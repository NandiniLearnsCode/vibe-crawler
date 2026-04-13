from __future__ import annotations

from vibe_crawler.models import BugReport

from .base import PageScanContext
from vibe_crawler.url_utils import hosts_match

IGNORE_ERROR_SNIPPETS = (
    "favicon.ico",
    "chrome-extension://",
)

CRITICAL_ERROR_HINTS = (
    "uncaught",
    "typeerror",
    "referenceerror",
    "cannot read properties",
    "is not defined",
)


class ConsoleErrorsDetector:
    name = "console_errors"

    async def detect(self, ctx: PageScanContext) -> list[BugReport]:
        bugs: list[BugReport] = []

        combined_errors = [*ctx.page_record.page_errors, *ctx.page_record.console_errors]
        for error_text in combined_errors[:10]:
            lowered = error_text.lower()
            if any(ignore in lowered for ignore in IGNORE_ERROR_SNIPPETS):
                continue
            if not any(hint in lowered for hint in CRITICAL_ERROR_HINTS):
                continue

            bugs.append(
                BugReport(
                    id="",
                    type="critical_frontend_error",
                    severity="high",
                    confidence=0.93,
                    page_url=ctx.page_record.url,
                    element_selector=None,
                    short_title="Critical JavaScript runtime error",
                    description=f"Page emitted a critical runtime error: {error_text[:220]}",
                    reproduction_steps=[
                        f"Open {ctx.page_record.url}",
                        "Open browser developer console",
                        "Observe uncaught JavaScript error",
                    ],
                    screenshot_path=ctx.page_record.screenshot_path,
                    console_errors=[error_text],
                    detector=self.name,
                )
            )

        for response in ctx.page_record.error_responses:
            if response.resource_type not in {"script", "stylesheet"}:
                continue
            if not hosts_match(response.url, ctx.config.root_domain):
                continue

            bugs.append(
                BugReport(
                    id="",
                    type="critical_frontend_error",
                    severity="high",
                    confidence=0.9,
                    page_url=ctx.page_record.url,
                    element_selector=None,
                    short_title="Critical frontend asset failed to load",
                    description=f"{response.resource_type} failed with HTTP {response.status}: {response.url}",
                    reproduction_steps=[
                        f"Open {ctx.page_record.url}",
                        "Inspect network panel",
                        f"Observe {response.resource_type} request failing: {response.url}",
                    ],
                    screenshot_path=ctx.page_record.screenshot_path,
                    network_evidence=[f"{response.url} -> HTTP {response.status}"],
                    detector=self.name,
                )
            )

        return bugs
