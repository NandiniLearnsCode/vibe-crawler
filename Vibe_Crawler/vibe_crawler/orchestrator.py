from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence
from urllib.parse import urljoin

from playwright.async_api import BrowserContext, Page, async_playwright

from vibe_crawler.config import CrawlConfig
from vibe_crawler.detectors import (
    BrokenLinksDetector,
    ConsoleErrorsDetector,
    DeadButtonsDetector,
    FormsDetector,
    MediaDetector,
    MobileLayoutDetector,
)
from vibe_crawler.detectors.base import Detector, PageScanContext
from vibe_crawler.evidence import ensure_directory, screenshot_name_for_url, take_page_screenshot
from vibe_crawler.frontier import UrlFrontier
from vibe_crawler.models import BugReport, CrawlReport, NetworkErrorResponse, NetworkFailure, PageRecord
from vibe_crawler.reporting import assign_bug_ids, deduplicate_bugs
from vibe_crawler.url_utils import (
    is_http_url,
    is_same_domain,
    looks_dangerous,
    looks_like_html_page,
    normalize_url,
)

log = logging.getLogger(__name__)


class CrawlOrchestrator:
    def __init__(
        self,
        config: CrawlConfig,
        *,
        desktop_detectors: Sequence[Detector] | None = None,
        mobile_detectors: Sequence[Detector] | None = None,
        headless: bool = True,
    ) -> None:
        self.config = config
        self.headless = headless
        self.desktop_detectors = list(
            desktop_detectors
            or [
                BrokenLinksDetector(),
                DeadButtonsDetector(),
                FormsDetector(),
                MediaDetector(),
                ConsoleErrorsDetector(),
            ]
        )
        self.mobile_detectors = list(mobile_detectors or [MobileLayoutDetector()])

    async def run(self) -> CrawlReport:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        started_at = datetime.now(timezone.utc).isoformat()
        ensure_directory(self.config.screenshot_dir)

        pages: list[PageRecord] = []
        bugs: list[BugReport] = []
        frontier = UrlFrontier(important_path_keywords=self.config.important_path_keywords)
        frontier.push(normalize_url(self.config.start_url), 0)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.headless)
            desktop_context = await browser.new_context(
                viewport={"width": self.config.desktop_viewport[0], "height": self.config.desktop_viewport[1]},
                ignore_https_errors=True,
            )
            mobile_context = await browser.new_context(
                viewport={"width": self.config.mobile_viewport[0], "height": self.config.mobile_viewport[1]},
                is_mobile=True,
                has_touch=True,
                ignore_https_errors=True,
            )

            try:
                while len(frontier) and len(pages) < self.config.max_pages:
                    next_item = frontier.pop()
                    if next_item is None:
                        break
                    url, depth = next_item
                    if depth > self.config.max_depth:
                        continue
                    if not self._is_safe_to_crawl(url):
                        continue

                    page_record, page_bugs = await self._scan_single_page(
                        browser_context=desktop_context,
                        url=url,
                        depth=depth,
                        run_id=run_id,
                        mobile=False,
                    )
                    pages.append(page_record)
                    bugs.extend(page_bugs)

                    if depth < self.config.max_depth:
                        for link in page_record.discovered_links:
                            if not self._is_safe_to_crawl(link):
                                continue
                            frontier.push(link, depth + 1)

                    if self.config.include_mobile_checks:
                        _, mobile_bugs = await self._scan_single_page(
                            browser_context=mobile_context,
                            url=url,
                            depth=depth,
                            run_id=run_id,
                            mobile=True,
                        )
                        bugs.extend(mobile_bugs)
            finally:
                await desktop_context.close()
                await mobile_context.close()
                await browser.close()

        deduped_bugs = deduplicate_bugs(bugs)
        assign_bug_ids(run_id, deduped_bugs)

        report = CrawlReport(
            run_id=run_id,
            start_url=self.config.start_url,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            pages=pages,
            bugs=deduped_bugs,
            output_path=self.config.output_path,
        )
        return report

    async def _scan_single_page(
        self,
        *,
        browser_context: BrowserContext,
        url: str,
        depth: int,
        run_id: str,
        mobile: bool,
    ) -> tuple[PageRecord, list[BugReport]]:
        page = await browser_context.new_page()
        console_errors: list[str] = []
        page_errors: list[str] = []
        failed_requests: list[NetworkFailure] = []
        error_responses: list[NetworkErrorResponse] = []
        crawl_errors: list[str] = []
        status_code: int | None = None

        def on_console(msg) -> None:
            if msg.type == "error":
                console_errors.append(msg.text)

        def on_page_error(exc: Exception) -> None:
            page_errors.append(str(exc))

        def on_request_failed(request) -> None:
            failure = request.failure
            if callable(failure):
                failure = failure()
            if isinstance(failure, dict):
                reason = failure.get("errorText") or "request failed"
            elif isinstance(failure, str):
                reason = failure
            else:
                reason = "request failed"
            failed_requests.append(
                NetworkFailure(
                    url=request.url,
                    resource_type=request.resource_type,
                    reason=reason,
                )
            )

        def on_response(response) -> None:
            if response.status >= 400:
                error_responses.append(
                    NetworkErrorResponse(
                        url=response.url,
                        status=response.status,
                        resource_type=response.request.resource_type,
                    )
                )

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("requestfailed", on_request_failed)
        page.on("response", on_response)

        links: list[str] = []
        screenshot_path: str | None = None
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
            status_code = response.status if response else None
            await page.wait_for_timeout(700)
            links = await self._extract_links(page, current_url=url)

            screenshot_suffix = "_mobile" if mobile else ""
            screenshot_name = screenshot_name_for_url(url, suffix=screenshot_suffix)
            screenshot_path = await take_page_screenshot(page, self.config.screenshot_dir / screenshot_name)
        except Exception as exc:
            crawl_errors.append(str(exc))
            log.warning("crawl error on %s: %s", url, exc)
        page_record = PageRecord(
            url=url,
            depth=depth,
            status_code=status_code,
            discovered_links=links,
            screenshot_path=screenshot_path,
            console_errors=console_errors,
            page_errors=page_errors,
            crawl_errors=crawl_errors,
            failed_requests=failed_requests,
            error_responses=error_responses,
        )

        detectors = self.mobile_detectors if mobile else self.desktop_detectors
        detector_ctx = PageScanContext(
            page=page,
            page_record=page_record,
            config=self.config,
            request_context=browser_context.request,
            screenshot_dir=self.config.screenshot_dir,
            run_id=run_id,
            mobile=mobile,
        )
        bugs: list[BugReport] = []
        for detector in detectors:
            try:
                bugs.extend(await detector.detect(detector_ctx))
            except Exception as exc:
                log.exception("detector %s failed on %s: %s", detector.name, url, exc)

        await page.close()
        return page_record, bugs

    async def _extract_links(self, page: Page, current_url: str) -> list[str]:
        hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(el => el.getAttribute('href'))")
        links: list[str] = []
        for href in hrefs:
            if not href:
                continue
            if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            candidate = normalize_url(urljoin(current_url, href))
            if not is_http_url(candidate):
                continue
            if candidate not in links:
                links.append(candidate)
        return links

    def _is_safe_to_crawl(self, url: str) -> bool:
        if not is_http_url(url):
            return False
        if self.config.same_domain_only and not is_same_domain(url, self.config.root_domain):
            return False
        if looks_dangerous(url, self.config.dangerous_path_keywords):
            return False
        if not looks_like_html_page(url):
            return False
        return True
