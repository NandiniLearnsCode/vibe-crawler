from __future__ import annotations

from playwright.async_api import Page

from detectors.base import BugDetector, Bug, Severity


class OverflowDetector(BugDetector):
    """
    Detects elements with horizontal overflow.

    This is extremely common in vibe-coded sites where LLM-generated layouts
    don't account for content width properly.
    """

    name = "overflow"

    async def detect(self, page: Page, url: str) -> list[Bug]:
        overflows = await page.evaluate("""() => {
            const results = [];
            for (const el of document.querySelectorAll('*')) {
                if (el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0) {
                    const tag = el.tagName.toLowerCase();
                    if (['html', 'body'].includes(tag)) continue;
                    const id = el.id ? '#' + el.id : '';
                    const cls = el.className && typeof el.className === 'string'
                        ? '.' + el.className.trim().split(/\\s+/).join('.') : '';
                    results.push({
                        selector: tag + id + cls,
                        scrollWidth: el.scrollWidth,
                        clientWidth: el.clientWidth,
                    });
                }
                if (results.length >= 20) break;
            }
            return results;
        }""")

        return [
            Bug(
                url=url,
                category="layout",
                severity=Severity.MEDIUM,
                title="Horizontal overflow detected",
                description=(
                    f"Element `{item['selector']}` overflows: "
                    f"scrollWidth={item['scrollWidth']}px vs "
                    f"clientWidth={item['clientWidth']}px"
                ),
                selector=item["selector"],
            )
            for item in overflows
        ]
