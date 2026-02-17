"""
Vibe Crawler
============
An agent that crawls vibe-coded websites to automatically find bugs.

Usage:
    python crawler.py https://my-vibe-site.vercel.app
    python crawler.py https://my-vibe-site.vercel.app --max-pages 30 --output bugs.json
"""

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse
from typing import Optional

from playwright.async_api import async_playwright, Page

from detectors import (
    BugDetector,
    ConsoleErrorDetector,
    BrokenLinkDetector,
    OverflowDetector,
    AccessibilityDetector,
    MetaAndSEODetector,
    DeadClickDetector,
    MobileResponsivenessDetector,
)


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Bug:
    url: str
    category: str
    severity: Severity
    title: str
    description: str
    selector: Optional[str] = None
    screenshot_path: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class CrawlResult:
    start_url: str
    pages_visited: int = 0
    bugs: list[Bug] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""


DEFAULT_DETECTORS: list[type[BugDetector]] = [
    ConsoleErrorDetector,
    BrokenLinkDetector,
    OverflowDetector,
    AccessibilityDetector,
    MetaAndSEODetector,
    DeadClickDetector,
    MobileResponsivenessDetector,
]


class VibeCrawler:
    """
    Main crawler agent. Visits pages starting from a URL using BFS,
    runs all registered detectors on each page, and produces a report.
    """

    def __init__(
        self,
        start_url: str,
        max_pages: int = 20,
        detectors: list[type[BugDetector]] | None = None,
        headless: bool = True,
        viewport: dict | None = None,
    ):
        self.start_url = start_url
        self.max_pages = max_pages
        self.detector_classes = detectors or DEFAULT_DETECTORS
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 800}
        self._visited: set[str] = set()
        self._queue: list[str] = []
        self.result = CrawlResult(start_url=start_url)

    def _same_origin(self, url: str) -> bool:
        return urlparse(url).netloc == urlparse(self.start_url).netloc

    async def _discover_links(self, page: Page) -> list[str]:
        hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = []
        for href in hrefs:
            clean = href.split("#")[0].rstrip("/")
            if clean and self._same_origin(clean) and clean not in self._visited:
                links.append(clean)
        return list(set(links))

    async def _crawl_page(self, page: Page, url: str, detectors: list[BugDetector]):
        print(f"  → Visiting: {url}")
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(1500)  # let JS hydrate/settle
        except Exception as e:
            self.result.errors.append(f"Failed to load {url}: {e}")
            return

        if resp and resp.status >= 400:
            self.result.bugs.append(Bug(
                url=url,
                category="http",
                severity=Severity.HIGH,
                title=f"HTTP {resp.status}",
                description=f"Page returned status {resp.status}",
            ))

        for det in detectors:
            try:
                bugs = await det.detect(page, url)
                self.result.bugs.extend(bugs)
            except Exception as e:
                self.result.errors.append(f"Detector {det.name} failed on {url}: {e}")

        try:
            new_links = await self._discover_links(page)
            for link in new_links:
                if link not in self._visited and link not in self._queue:
                    self._queue.append(link)
        except Exception:
            pass

    async def run(self) -> CrawlResult:
        self.result.started_at = datetime.utcnow().isoformat()
        print(f"🔍 Vibe Crawler starting: {self.start_url} (max {self.max_pages} pages)")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(viewport=self.viewport)
            page = await context.new_page()

            detectors: list[BugDetector] = []
            for cls in self.detector_classes:
                det = cls()
                if hasattr(det, "attach"):
                    det.attach(page)
                detectors.append(det)

            self._queue.append(self.start_url.rstrip("/"))

            while self._queue and len(self._visited) < self.max_pages:
                url = self._queue.pop(0)
                if url in self._visited:
                    continue
                self._visited.add(url)
                await self._crawl_page(page, url, detectors)

            await browser.close()

        self.result.pages_visited = len(self._visited)
        self.result.finished_at = datetime.utcnow().isoformat()
        print(f"✅ Done. Visited {self.result.pages_visited} pages, found {len(self.result.bugs)} bugs.")
        return self.result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Vibe Crawler — find bugs in vibe-coded websites"
    )
    parser.add_argument("url", help="Starting URL to crawl")
    parser.add_argument("--max-pages", type=int, default=20, help="Max pages to visit (default: 20)")
    parser.add_argument("--output", default="report.json", help="Output JSON report path")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    parser.add_argument(
        "--format",
        choices=["json", "html", "both"],
        default="both",
        help="Report format (default: both)",
    )
    args = parser.parse_args()

    from reporter import print_report, generate_json_report, generate_html_report

    crawler = VibeCrawler(
        start_url=args.url,
        max_pages=args.max_pages,
        headless=not args.headed,
    )
    result = await crawler.run()
    print_report(result)

    if args.format in ("json", "both"):
        generate_json_report(result, args.output)
    if args.format in ("html", "both"):
        html_path = args.output.replace(".json", ".html")
        generate_html_report(result, html_path)


if __name__ == "__main__":
    asyncio.run(main())
