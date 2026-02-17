from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from playwright.async_api import Page


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


class BugDetector:
    """
    Base class for all bug detectors.

    Subclass this and override `detect()` to create your own detector.
    Optionally override `attach()` if you need to hook into page events
    before navigation (e.g. listening to console messages).
    """

    name: str = "base"

    async def detect(self, page: Page, url: str) -> list[Bug]:
        raise NotImplementedError

    def attach(self, page: Page) -> None:
        """Override to subscribe to page events before navigation."""
        pass
