from __future__ import annotations

from vibe_crawler.models import BugReport
from vibe_crawler.url_utils import canonical_domain

from .base import PageScanContext

ERROR_PAGE_PATTERNS = (
    "404",
    "page not found",
    "not found",
    "something went wrong",
    "internal server error",
)


class BrokenLinksDetector:
    name = "broken_links"

    async def detect(self, ctx: PageScanContext) -> list[BugReport]:
        bugs: list[BugReport] = []
        checked = 0

        for link in ctx.page_record.discovered_links:
            if checked >= ctx.config.max_links_per_page:
                break
            if canonical_domain(link) not in ctx.config.allowed_domains:
                continue
            checked += 1

            try:
                response = await ctx.request_context.get(link, timeout=ctx.config.timeout_ms)
                status = response.status
                if status >= 400:
                    bugs.append(
                        BugReport(
                            id="",
                            type="broken_link",
                            severity="high" if status >= 500 else "medium",
                            confidence=0.99,
                            page_url=ctx.page_record.url,
                            element_selector=None,
                            short_title=f"Internal link returns HTTP {status}",
                            description=f"Internal link {link} returned HTTP {status}.",
                            reproduction_steps=[
                                f"Open {ctx.page_record.url}",
                                f"Navigate to link: {link}",
                                f"Observe HTTP {status} response",
                            ],
                            screenshot_path=ctx.page_record.screenshot_path,
                            network_evidence=[f"{link} -> HTTP {status}"],
                            detector=self.name,
                        )
                    )
                    continue

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type.lower():
                    continue

                body = (await response.text())[:4000].lower()
                if any(pattern in body for pattern in ERROR_PAGE_PATTERNS):
                    bugs.append(
                        BugReport(
                            id="",
                            type="broken_link",
                            severity="medium",
                            confidence=0.87,
                            page_url=ctx.page_record.url,
                            element_selector=None,
                            short_title="Internal link appears to lead to error page",
                            description=(
                                f"Internal link {link} returned HTTP {status} but its content "
                                "matches common error-page signatures."
                            ),
                            reproduction_steps=[
                                f"Open {ctx.page_record.url}",
                                f"Navigate to link: {link}",
                                "Observe page contains error messaging (e.g. 404 or not found)",
                            ],
                            screenshot_path=ctx.page_record.screenshot_path,
                            network_evidence=[f"{link} -> HTTP {status} with error-like body"],
                            detector=self.name,
                        )
                    )
            except Exception as exc:
                bugs.append(
                    BugReport(
                        id="",
                        type="broken_link",
                        severity="medium",
                        confidence=0.92,
                        page_url=ctx.page_record.url,
                        element_selector=None,
                        short_title="Internal link request failed",
                        description=f"Request to internal link {link} failed: {exc}",
                        reproduction_steps=[
                            f"Open {ctx.page_record.url}",
                            f"Navigate to link: {link}",
                            "Observe request failure in browser/network logs",
                        ],
                        screenshot_path=ctx.page_record.screenshot_path,
                        network_evidence=[f"{link} -> request failed: {exc}"],
                        detector=self.name,
                    )
                )

        return bugs
