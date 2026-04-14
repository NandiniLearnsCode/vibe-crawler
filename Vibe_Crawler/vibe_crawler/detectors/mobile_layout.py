from __future__ import annotations

from vibe_crawler.models import BugReport

from .base import PageScanContext


class MobileLayoutDetector:
    name = "mobile_layout"

    async def detect(self, ctx: PageScanContext) -> list[BugReport]:
        if not ctx.mobile:
            return []

        metrics = await ctx.page.evaluate(
            """
            () => {
              const viewportWidth = window.innerWidth;
              const overflowPx = document.documentElement.scrollWidth - viewportWidth;

              const controls = Array.from(document.querySelectorAll("a, button, input, textarea, select"));
              const offscreenControls = controls.filter((el) => {
                const rect = el.getBoundingClientRect();
                if (rect.width < 20 || rect.height < 12) return false;
                return rect.right > viewportWidth + 2 || rect.left < -2;
              });

              const truncatedTextNodes = Array.from(document.querySelectorAll("p, h1, h2, h3, span, a, button"))
                .filter((el) => {
                  const text = (el.textContent || "").trim();
                  if (text.length < 25) return false;
                  const style = window.getComputedStyle(el);
                  return (
                    (style.overflow === "hidden" || style.textOverflow === "ellipsis") &&
                    el.scrollWidth > el.clientWidth + 4
                  );
                })
                .slice(0, 10)
                .length;

              return {
                overflowPx,
                offscreenCount: offscreenControls.length,
                truncatedTextNodes,
              };
            }
            """
        )

        bugs: list[BugReport] = []
        if metrics["overflowPx"] > 20:
            bugs.append(
                BugReport(
                    id="",
                    type="mobile_layout",
                    severity="high",
                    confidence=0.94,
                    page_url=ctx.page_record.url,
                    element_selector=None,
                    short_title="Mobile page has horizontal overflow",
                    description=(
                        "Page width exceeds viewport on mobile, creating horizontal scrolling "
                        f"({metrics['overflowPx']}px overflow)."
                    ),
                    reproduction_steps=[
                        f"Open {ctx.page_record.url} at 390px viewport width",
                        "Swipe horizontally",
                        "Observe horizontal overflow",
                    ],
                    screenshot_path=ctx.page_record.screenshot_path,
                    detector=self.name,
                )
            )

        if metrics["offscreenCount"] >= 2:
            bugs.append(
                BugReport(
                    id="",
                    type="mobile_layout",
                    severity="medium",
                    confidence=0.88,
                    page_url=ctx.page_record.url,
                    element_selector=None,
                    short_title="Interactive elements are off-screen on mobile",
                    description=(
                        f"Detected {metrics['offscreenCount']} interactive elements outside "
                        "the mobile viewport bounds."
                    ),
                    reproduction_steps=[
                        f"Open {ctx.page_record.url} at 390px viewport width",
                        "Inspect interactive controls",
                        "Observe controls extending off-screen",
                    ],
                    screenshot_path=ctx.page_record.screenshot_path,
                    detector=self.name,
                )
            )

        if metrics["truncatedTextNodes"] >= 2:
            bugs.append(
                BugReport(
                    id="",
                    type="mobile_layout",
                    severity="medium",
                    confidence=0.84,
                    page_url=ctx.page_record.url,
                    element_selector=None,
                    short_title="Text appears truncated on mobile",
                    description=(
                        f"Detected {metrics['truncatedTextNodes']} text elements that appear clipped "
                        "with overflow styling."
                    ),
                    reproduction_steps=[
                        f"Open {ctx.page_record.url} at 390px viewport width",
                        "Review body text and headings",
                        "Observe clipped/truncated text",
                    ],
                    screenshot_path=ctx.page_record.screenshot_path,
                    detector=self.name,
                )
            )

        return bugs
