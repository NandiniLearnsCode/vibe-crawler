from __future__ import annotations

from playwright.async_api import Page

from detectors.base import BugDetector, Bug, Severity


class MetaAndSEODetector(BugDetector):
    """
    Checks for missing meta tags, title, and viewport.

    Vibe-coded sites frequently ship without a viewport meta tag,
    which makes them broken on mobile devices.
    """

    name = "meta_seo"

    async def detect(self, page: Page, url: str) -> list[Bug]:
        info = await page.evaluate("""() => ({
            title: document.title,
            metaDescription:
                document.querySelector('meta[name="description"]')?.content || '',
            viewport:
                document.querySelector('meta[name="viewport"]')?.content || '',
            h1Count: document.querySelectorAll('h1').length,
            favicon: !!document.querySelector('link[rel*="icon"]'),
        })""")

        bugs = []

        if not info["title"]:
            bugs.append(Bug(
                url=url,
                category="seo",
                severity=Severity.MEDIUM,
                title="Missing page <title>",
                description="The page has no <title> tag.",
            ))

        if not info["viewport"]:
            bugs.append(Bug(
                url=url,
                category="seo",
                severity=Severity.MEDIUM,
                title="Missing viewport meta tag",
                description=(
                    "No <meta name='viewport'> found — "
                    "this page is likely broken on mobile devices."
                ),
            ))

        if not info["metaDescription"]:
            bugs.append(Bug(
                url=url,
                category="seo",
                severity=Severity.LOW,
                title="Missing meta description",
                description="No <meta name='description'> tag found.",
            ))

        if not info["favicon"]:
            bugs.append(Bug(
                url=url,
                category="seo",
                severity=Severity.LOW,
                title="Missing favicon",
                description="No <link rel='icon'> found.",
            ))

        if info["h1Count"] == 0:
            bugs.append(Bug(
                url=url,
                category="seo",
                severity=Severity.LOW,
                title="No <h1> heading found",
                description="Page has no <h1> element.",
            ))
        elif info["h1Count"] > 1:
            bugs.append(Bug(
                url=url,
                category="seo",
                severity=Severity.LOW,
                title=f"Multiple <h1> tags ({info['h1Count']})",
                description="Best practice is a single <h1> per page.",
            ))

        return bugs
