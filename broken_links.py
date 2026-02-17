from __future__ import annotations

from playwright.async_api import Page

from detectors.base import BugDetector, Bug, Severity


class BrokenLinkDetector(BugDetector):
    """Finds links that return 4xx/5xx status codes."""

    name = "broken_links"

    MAX_LINKS_PER_PAGE = 50

    async def detect(self, page: Page, url: str) -> list[Bug]:
        bugs = []
        links = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.href, text: e.innerText.trim().slice(0, 80)}))",
        )

        for link in links[: self.MAX_LINKS_PER_PAGE]:
            href = link["href"]
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "data:")):
                continue
            try:
                resp = await page.request.head(href, timeout=8000)
                if resp.status >= 400:
                    bugs.append(Bug(
                        url=url,
                        category="broken_link",
                        severity=Severity.HIGH if resp.status >= 500 else Severity.MEDIUM,
                        title=f"Broken link ({resp.status})",
                        description=(
                            f'Link "{link["text"]}" → {href} returned {resp.status}'
                        ),
                        extra={"status": resp.status, "target": href},
                    ))
            except Exception:
                pass  # timeouts on external sites are too noisy to report

        return bugs
