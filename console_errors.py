from __future__ import annotations

from playwright.async_api import Page

from detectors.base import BugDetector, Bug, Severity


class ConsoleErrorDetector(BugDetector):
    """Captures JavaScript console errors and unhandled exceptions."""

    name = "console_errors"

    def __init__(self):
        self._errors: list[dict] = []

    def attach(self, page: Page):
        page.on("console", self._on_console)
        page.on("pageerror", self._on_pageerror)

    def _on_console(self, msg):
        if msg.type == "error":
            self._errors.append({"type": "console.error", "text": msg.text})

    def _on_pageerror(self, error):
        self._errors.append({"type": "unhandled_exception", "text": str(error)})

    async def detect(self, page: Page, url: str) -> list[Bug]:
        bugs = []
        for err in self._errors:
            bugs.append(Bug(
                url=url,
                category="javascript",
                severity=(
                    Severity.HIGH
                    if err["type"] == "unhandled_exception"
                    else Severity.MEDIUM
                ),
                title=f"JS {err['type']}",
                description=err["text"][:500],
            ))
        self._errors.clear()
        return bugs
