from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from playwright.async_api import APIRequestContext, Page

from vibe_crawler.config import CrawlConfig
from vibe_crawler.models import BugReport, PageRecord


@dataclass(slots=True)
class PageScanContext:
    page: Page
    page_record: PageRecord
    config: CrawlConfig
    request_context: APIRequestContext
    screenshot_dir: Path
    run_id: str
    mobile: bool = False


class Detector(Protocol):
    name: str

    async def detect(self, ctx: PageScanContext) -> list[BugReport]:
        ...
