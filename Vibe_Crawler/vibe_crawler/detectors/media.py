from __future__ import annotations

from urllib.parse import urlparse

from vibe_crawler.models import BugReport

from .base import PageScanContext


class MediaDetector:
    name = "media"

    async def detect(self, ctx: PageScanContext) -> list[BugReport]:
        bugs: list[BugReport] = []

        broken_images = await ctx.page.evaluate(
            """
            () => {
              const imgs = Array.from(document.querySelectorAll("img"));
              const output = [];
              for (const img of imgs) {
                const src = img.getAttribute("src") || "";
                if (!src) {
                  output.push({ src: "(missing src)", selector: "img", likelyHero: false });
                  continue;
                }
                const rect = img.getBoundingClientRect();
                const likelyHero = rect.top < window.innerHeight && rect.width > 320 && rect.height > 120;
                if ((img.complete && img.naturalWidth === 0) || img.dataset?.nimg === "error") {
                  output.push({
                    src,
                    selector: img.id ? `img#${img.id}` : "img",
                    likelyHero,
                  });
                }
              }
              return output.slice(0, 10);
            }
            """
        )

        for item in broken_images:
            severity = "high" if item.get("likelyHero") else "medium"
            bugs.append(
                BugReport(
                    id="",
                    type="missing_media",
                    severity=severity,
                    confidence=0.95,
                    page_url=ctx.page_record.url,
                    element_selector=item.get("selector"),
                    short_title="Image failed to load",
                    description=f"Image asset did not render correctly: {item.get('src')}",
                    reproduction_steps=[
                        f"Open {ctx.page_record.url}",
                        "Inspect visible image area",
                        "Observe missing/broken image asset",
                    ],
                    screenshot_path=ctx.page_record.screenshot_path,
                    network_evidence=[item.get("src", "")],
                    detector=self.name,
                )
            )

        for response in ctx.page_record.error_responses:
            if response.resource_type not in {"image", "media"}:
                continue
            if urlparse(response.url).netloc and urlparse(response.url).netloc != ctx.config.root_domain:
                continue
            bugs.append(
                BugReport(
                    id="",
                    type="missing_media",
                    severity="medium",
                    confidence=0.96,
                    page_url=ctx.page_record.url,
                    element_selector=None,
                    short_title="Media request returned error response",
                    description=f"Media asset request failed with HTTP {response.status}: {response.url}",
                    reproduction_steps=[
                        f"Open {ctx.page_record.url}",
                        "Observe broken media asset",
                        f"Check network entry for {response.url}",
                    ],
                    screenshot_path=ctx.page_record.screenshot_path,
                    network_evidence=[f"{response.url} -> HTTP {response.status}"],
                    detector=self.name,
                )
            )

        return bugs
