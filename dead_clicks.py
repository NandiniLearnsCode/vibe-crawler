from __future__ import annotations

from playwright.async_api import Page

from detectors.base import BugDetector, Bug, Severity


class DeadClickDetector(BugDetector):
    """
    Finds elements that look clickable but aren't actually interactive.

    Looks for elements with button-like class names (btn, button, cta, click)
    that are not real buttons/links and don't have click handlers or
    pointer cursors.
    """

    name = "dead_clicks"

    async def detect(self, page: Page, url: str) -> list[Bug]:
        suspects = await page.evaluate("""() => {
            const results = [];
            const els = document.querySelectorAll(
                '[class*="btn"], [class*="button"], [class*="cta"], [class*="click"]'
            );
            for (const el of els) {
                const tag = el.tagName.toLowerCase();
                // Skip actually interactive elements
                if (['button', 'a', 'input', 'select', 'textarea'].includes(tag))
                    continue;
                const style = getComputedStyle(el);
                if (
                    style.cursor === 'pointer' ||
                    el.getAttribute('role') === 'button' ||
                    el.getAttribute('tabindex')
                )
                    continue;
                if (!el.onclick) {
                    results.push({
                        tag,
                        text: el.innerText?.trim().slice(0, 60) || '',
                        html: el.outerHTML.slice(0, 150),
                    });
                }
                if (results.length >= 10) break;
            }
            return results;
        }""")

        return [
            Bug(
                url=url,
                category="ux",
                severity=Severity.LOW,
                title="Possibly non-interactive button-like element",
                description=(
                    f'`{s["tag"]}` with text "{s["text"]}" has a button-like '
                    f"class name but may not be clickable."
                ),
                extra={"html": s["html"]},
            )
            for s in suspects
        ]
