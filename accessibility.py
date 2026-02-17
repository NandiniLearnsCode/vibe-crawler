from __future__ import annotations

from playwright.async_api import Page

from detectors.base import BugDetector, Bug, Severity


class AccessibilityDetector(BugDetector):
    """
    Checks for common accessibility issues.

    Covers: missing alt text, unlabeled interactive elements, missing lang
    attribute, form inputs without associated labels.
    """

    name = "accessibility"

    async def detect(self, page: Page, url: str) -> list[Bug]:
        issues = await page.evaluate("""() => {
            const problems = [];

            // Images without alt text
            document.querySelectorAll('img:not([alt])').forEach(img => {
                problems.push({
                    type: 'img_no_alt',
                    detail: img.src?.slice(0, 120) || '(no src)',
                });
            });

            // Interactive elements with no accessible name
            document.querySelectorAll('button, a[href]').forEach(el => {
                const text = (el.innerText || '').trim();
                const ariaLabel = el.getAttribute('aria-label') || '';
                const title = el.getAttribute('title') || '';
                if (!text && !ariaLabel && !title) {
                    problems.push({
                        type: 'empty_interactive',
                        detail: el.outerHTML.slice(0, 150),
                    });
                }
            });

            // Missing lang attribute on <html>
            if (!document.documentElement.getAttribute('lang')) {
                problems.push({
                    type: 'no_lang',
                    detail: '<html> missing lang attribute',
                });
            }

            // Form inputs without labels
            document.querySelectorAll(
                'input:not([type=hidden]), textarea, select'
            ).forEach(el => {
                const id = el.id;
                const ariaLabel = el.getAttribute('aria-label');
                const ariaLabelledBy = el.getAttribute('aria-labelledby');
                const hasLabel = id && document.querySelector(
                    'label[for="' + id + '"]'
                );
                if (!hasLabel && !ariaLabel && !ariaLabelledBy) {
                    problems.push({
                        type: 'input_no_label',
                        detail: el.outerHTML.slice(0, 150),
                    });
                }
            });

            return problems.slice(0, 30);
        }""")

        title_map = {
            "img_no_alt": "Image missing alt text",
            "empty_interactive": "Interactive element has no accessible name",
            "no_lang": "Missing lang attribute on <html>",
            "input_no_label": "Form input missing associated label",
        }

        severity_map = {
            "img_no_alt": Severity.MEDIUM,
            "empty_interactive": Severity.MEDIUM,
            "no_lang": Severity.LOW,
            "input_no_label": Severity.MEDIUM,
        }

        return [
            Bug(
                url=url,
                category="accessibility",
                severity=severity_map.get(issue["type"], Severity.LOW),
                title=title_map.get(issue["type"], issue["type"]),
                description=issue["detail"],
            )
            for issue in issues
        ]
