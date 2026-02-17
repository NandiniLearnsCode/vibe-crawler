from __future__ import annotations

from playwright.async_api import Page

from detectors.base import BugDetector, Bug, Severity


class MobileResponsivenessDetector(BugDetector):
    """
    Checks for mobile responsiveness issues by evaluating the page
    at its current viewport and looking for common breakage patterns.

    For a full mobile-viewport crawl, run VibeCrawler with
    viewport={"width": 375, "height": 812}.
    """

    name = "mobile_responsiveness"

    async def detect(self, page: Page, url: str) -> list[Bug]:
        issues = await page.evaluate("""() => {
            const problems = [];
            const vw = window.innerWidth;

            // Elements wider than the viewport
            for (const el of document.querySelectorAll('*')) {
                const rect = el.getBoundingClientRect();
                if (rect.width > vw + 5 && rect.width > 0) {
                    const tag = el.tagName.toLowerCase();
                    if (['html', 'body'].includes(tag)) continue;
                    const id = el.id ? '#' + el.id : '';
                    const cls = el.className && typeof el.className === 'string'
                        ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.')
                        : '';
                    problems.push({
                        type: 'wider_than_viewport',
                        selector: tag + id + cls,
                        elementWidth: Math.round(rect.width),
                        viewportWidth: vw,
                    });
                    if (problems.length >= 15) break;
                }
            }

            // Fixed-width elements that don't adapt
            document.querySelectorAll('[style*="width"]').forEach(el => {
                const style = el.getAttribute('style') || '';
                const match = style.match(/width:\\s*(\\d+)px/);
                if (match && parseInt(match[1]) > vw) {
                    problems.push({
                        type: 'fixed_width_overflow',
                        selector: el.tagName.toLowerCase(),
                        detail: style.slice(0, 100),
                    });
                }
            });

            // Tiny tap targets (interactive elements smaller than 44x44)
            document.querySelectorAll('a, button, input, select, textarea').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (
                    rect.width > 0 && rect.height > 0 &&
                    (rect.width < 44 || rect.height < 44) &&
                    rect.width < 200  // skip full-width elements
                ) {
                    const text = (el.innerText || el.getAttribute('aria-label') || '')
                        .trim().slice(0, 40);
                    problems.push({
                        type: 'small_tap_target',
                        selector: el.tagName.toLowerCase(),
                        detail: text,
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                    });
                }
            });

            // Text too small to read on mobile
            const textEls = document.querySelectorAll('p, span, li, td, th, label');
            for (const el of textEls) {
                const fontSize = parseFloat(getComputedStyle(el).fontSize);
                if (fontSize > 0 && fontSize < 12 && el.innerText?.trim().length > 5) {
                    problems.push({
                        type: 'small_text',
                        detail: el.innerText.trim().slice(0, 60),
                        fontSize: fontSize,
                    });
                    break;  // one is enough to flag
                }
            }

            return problems.slice(0, 25);
        }""")

        bugs = []
        for issue in issues:
            if issue["type"] == "wider_than_viewport":
                bugs.append(Bug(
                    url=url,
                    category="mobile",
                    severity=Severity.MEDIUM,
                    title="Element wider than viewport",
                    description=(
                        f"Element `{issue['selector']}` is {issue['elementWidth']}px wide "
                        f"but viewport is {issue['viewportWidth']}px."
                    ),
                    selector=issue.get("selector"),
                ))
            elif issue["type"] == "fixed_width_overflow":
                bugs.append(Bug(
                    url=url,
                    category="mobile",
                    severity=Severity.MEDIUM,
                    title="Fixed-width element overflows viewport",
                    description=f"Inline style sets a fixed pixel width: {issue['detail']}",
                ))
            elif issue["type"] == "small_tap_target":
                bugs.append(Bug(
                    url=url,
                    category="mobile",
                    severity=Severity.LOW,
                    title="Tap target too small",
                    description=(
                        f"`{issue['selector']}` \"{issue['detail']}\" is only "
                        f"{issue['width']}×{issue['height']}px "
                        f"(minimum recommended: 44×44px)."
                    ),
                ))
            elif issue["type"] == "small_text":
                bugs.append(Bug(
                    url=url,
                    category="mobile",
                    severity=Severity.LOW,
                    title="Text may be too small on mobile",
                    description=(
                        f"Text \"{issue['detail']}\" is {issue['fontSize']}px "
                        f"(minimum recommended: 12px)."
                    ),
                ))

        return bugs
