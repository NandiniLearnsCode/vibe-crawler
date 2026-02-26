"""
crawler.py — Playwright-based web crawler for vibe-coded site bug detection.

Usage:
    python crawler.py --url https://example.com
    python crawler.py --url https://example.com --username admin --password secret
    python crawler.py --url https://example.com --max-pages 50 --max-depth 3
"""

import asyncio
import argparse
import json
import logging
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, BrowserContext, ConsoleMessage, Request, Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PageFinding:
    """A single issue found on a page."""
    kind: str          # "console_error" | "failed_request" | "missing_resource" | "info"
    message: str
    detail: str = ""


@dataclass
class CrawledPage:
    """Everything collected about a single crawled page."""
    url: str
    status: int | None
    depth: int
    findings: list[PageFinding] = field(default_factory=list)
    links_found: list[str] = field(default_factory=list)
    screenshot_path: str | None = None
    crawled_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [asdict(f) for f in self.findings]
        return d


@dataclass
class CrawlResult:
    """Aggregate result of a full crawl."""
    root_url: str
    pages: list[CrawledPage] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: str | None = None

    def summary(self) -> dict:
        total_findings = sum(len(p.findings) for p in self.pages)
        by_kind: dict[str, int] = {}
        for page in self.pages:
            for f in page.findings:
                by_kind[f.kind] = by_kind.get(f.kind, 0) + 1
        return {
            "root_url": self.root_url,
            "pages_crawled": len(self.pages),
            "total_findings": total_findings,
            "findings_by_kind": by_kind,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    def to_dict(self) -> dict:
        return {
            "summary": self.summary(),
            "pages": [p.to_dict() for p in self.pages],
        }


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------

class VibeCrawler:
    def __init__(
        self,
        root_url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        max_pages: int = 100,
        max_depth: int = 5,
        screenshot_dir: str | Path | None = None,
        headless: bool = True,
        same_origin_only: bool = True,
    ):
        self.root_url = root_url.rstrip("/")
        self.root_origin = urlparse(root_url).netloc
        self.username = username
        self.password = password
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else None
        self.headless = headless
        self.same_origin_only = same_origin_only

        if self.screenshot_dir:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def crawl(self) -> CrawlResult:
        result = CrawlResult(root_url=self.root_url)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await self._make_context(browser)

            try:
                await self._run(context, result)
            finally:
                await context.close()
                await browser.close()

        result.finished_at = datetime.utcnow().isoformat()
        return result

    # ------------------------------------------------------------------
    # Browser / auth setup
    # ------------------------------------------------------------------

    async def _make_context(self, browser) -> BrowserContext:
        kwargs: dict = {
            "viewport": {"width": 1280, "height": 800},
            "ignore_https_errors": True,  # vibe-coded sites often have cert issues
        }
        if self.username and self.password:
            kwargs["http_credentials"] = {
                "username": self.username,
                "password": self.password,
            }
        context = await browser.new_context(**kwargs)
        return context

    # ------------------------------------------------------------------
    # Core BFS crawl loop
    # ------------------------------------------------------------------

    async def _run(self, context: BrowserContext, result: CrawlResult) -> None:
        visited: set[str] = set()
        # Queue items: (url, depth)
        queue: deque[tuple[str, int]] = deque([(self.root_url, 0)])

        while queue and len(result.pages) < self.max_pages:
            url, depth = queue.popleft()
            normalized = self._normalize(url)

            if normalized in visited:
                continue
            visited.add(normalized)

            log.info(f"[depth={depth}] Crawling: {url}")
            crawled = await self._crawl_page(context, url, depth)
            result.pages.append(crawled)

            if depth < self.max_depth:
                for link in crawled.links_found:
                    norm_link = self._normalize(link)
                    if norm_link not in visited and self._should_follow(link):
                        queue.append((link, depth + 1))

    # ------------------------------------------------------------------
    # Single-page crawl
    # ------------------------------------------------------------------

    async def _crawl_page(self, context: BrowserContext, url: str, depth: int) -> CrawledPage:
        page = await context.new_page()
        findings: list[PageFinding] = []
        failed_requests: list[str] = []

        # --- Attach listeners ---
        page.on("console", lambda msg: self._on_console(msg, findings))
        page.on("requestfailed", lambda req: failed_requests.append(req.url))

        status: int | None = None
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=30_000)
            status = response.status if response else None

            if status and status >= 400:
                findings.append(PageFinding(
                    kind="http_error",
                    message=f"HTTP {status}",
                    detail=url,
                ))

            # Wait a moment for late JS errors
            await page.wait_for_timeout(500)

            # Collect links
            links = await self._collect_links(page, url)

            # Record failed network requests
            for req_url in failed_requests:
                findings.append(PageFinding(
                    kind="failed_request",
                    message="Network request failed",
                    detail=req_url,
                ))

            # Screenshot
            screenshot_path = await self._take_screenshot(page, url)

        except Exception as exc:
            log.warning(f"Error crawling {url}: {exc}")
            findings.append(PageFinding(
                kind="crawl_error",
                message=str(exc),
                detail=url,
            ))
            links = []
            screenshot_path = None
        finally:
            await page.close()

        return CrawledPage(
            url=url,
            status=status,
            depth=depth,
            findings=findings,
            links_found=links,
            screenshot_path=str(screenshot_path) if screenshot_path else None,
        )

    # ------------------------------------------------------------------
    # Console listener
    # ------------------------------------------------------------------

    def _on_console(self, msg: ConsoleMessage, findings: list[PageFinding]) -> None:
        if msg.type in ("error", "warning"):
            findings.append(PageFinding(
                kind="console_error" if msg.type == "error" else "console_warning",
                message=msg.text,
                detail=f"type={msg.type}",
            ))

    # ------------------------------------------------------------------
    # Link collection
    # ------------------------------------------------------------------

    async def _collect_links(self, page: Page, base_url: str) -> list[str]:
        hrefs: list[str] = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.href)",
        )
        links = []
        for href in hrefs:
            absolute = urljoin(base_url, href)
            # Strip fragments
            absolute = absolute.split("#")[0].rstrip("/")
            if absolute and absolute.startswith("http"):
                links.append(absolute)
        return list(dict.fromkeys(links))  # deduplicate, preserve order

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    async def _take_screenshot(self, page: Page, url: str) -> Path | None:
        if not self.screenshot_dir:
            return None
        safe_name = url.replace("https://", "").replace("http://", "")
        safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in safe_name)
        safe_name = safe_name[:100]  # cap length
        path = self.screenshot_dir / f"{safe_name}.png"
        try:
            await page.screenshot(path=str(path), full_page=True)
            return path
        except Exception as exc:
            log.warning(f"Screenshot failed for {url}: {exc}")
            return None

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def _normalize(self, url: str) -> str:
        return url.rstrip("/").lower().split("?")[0]

    def _should_follow(self, url: str) -> bool:
        if self.same_origin_only:
            return urlparse(url).netloc == self.root_origin
        return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl a site and surface bugs.")
    parser.add_argument("--url", required=True, help="Root URL to crawl")
    parser.add_argument("--username", help="HTTP Basic Auth username")
    parser.add_argument("--password", help="HTTP Basic Auth password")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--screenshots", help="Directory to save screenshots")
    parser.add_argument("--output", help="Save full results to this JSON file")
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    crawler = VibeCrawler(
        root_url=args.url,
        username=args.username,
        password=args.password,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        screenshot_dir=args.screenshots,
        headless=not args.no_headless,
    )

    log.info(f"Starting crawl of {args.url}")
    result = await crawler.crawl()

    # Always print summary
    summary = result.summary()
    print("\n" + "=" * 60)
    print("CRAWL SUMMARY")
    print("=" * 60)
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # Print findings per page
    print("\nFINDINGS BY PAGE")
    print("-" * 60)
    for page in result.pages:
        if page.findings:
            print(f"\n  {page.url}  [HTTP {page.status}]")
            for f in page.findings:
                print(f"    [{f.kind}] {f.message}")
                if f.detail and f.detail != f.message:
                    print(f"             → {f.detail}")

    # Optionally save full JSON
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result.to_dict(), indent=2))
        log.info(f"Full results saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
