from __future__ import annotations

import logging

from vibe_crawler.models import BugReport

from .base import PageScanContext

log = logging.getLogger(__name__)


class DeadButtonsDetector:
    name = "dead_buttons"

    async def detect(self, ctx: PageScanContext) -> list[BugReport]:
        if ctx.mobile:
            return []

        request_count = 0

        def on_request(_) -> None:
            nonlocal request_count
            request_count += 1

        ctx.page.on("request", on_request)
        await ctx.page.evaluate(
            """
            () => {
              if (!window.__qaMutationProbe) {
                window.__qaMutationProbe = { count: 0 };
                const observer = new MutationObserver((mutations) => {
                  window.__qaMutationProbe.count += mutations.length;
                });
                observer.observe(document.body, { childList: true, subtree: true, attributes: true });
              }
            }
            """
        )

        candidates = await ctx.page.evaluate(
            """
            () => {
              const actionWords = /(sign up|get started|submit|contact|send|continue|next|join|book|try|start)/i;
              const nodeList = Array.from(document.querySelectorAll("button, a, [role='button'], input[type='button']"));

              function cssPath(el) {
                if (!(el instanceof Element)) return "";
                const parts = [];
                while (el && el.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
                  let selector = el.nodeName.toLowerCase();
                  if (el.id) {
                    selector += "#" + el.id;
                    parts.unshift(selector);
                    break;
                  }
                  const cls = Array.from(el.classList).slice(0, 2).join(".");
                  if (cls) selector += "." + cls;
                  const siblings = el.parentNode ? Array.from(el.parentNode.children).filter(n => n.nodeName === el.nodeName) : [];
                  if (siblings.length > 1) {
                    selector += `:nth-of-type(${siblings.indexOf(el) + 1})`;
                  }
                  parts.unshift(selector);
                  el = el.parentElement;
                }
                return parts.join(" > ");
              }

              const output = [];
              for (const el of nodeList) {
                if (output.length >= 12) break;
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                if (rect.width < 24 || rect.height < 14) continue;
                if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") continue;
                if (el.disabled) continue;

                const text = (el.innerText || el.getAttribute("aria-label") || "").trim();
                const href = (el.getAttribute("href") || "").trim().toLowerCase();
                const role = (el.getAttribute("role") || "").trim().toLowerCase();
                const suspiciousHref = href === "#" || href.startsWith("javascript:");
                if (!actionWords.test(text) && !suspiciousHref && role !== "button") continue;

                output.push({
                  selector: cssPath(el),
                  text,
                  href,
                });
              }
              return output;
            }
            """
        )

        bugs: list[BugReport] = []
        for candidate in candidates[: ctx.config.max_buttons_per_page]:
            selector = candidate.get("selector")
            if not selector:
                continue

            baseline = await ctx.page.evaluate(
                """
                () => ({
                  url: window.location.href,
                  mutationCount: window.__qaMutationProbe ? window.__qaMutationProbe.count : 0,
                  modalCount: document.querySelectorAll("[role='dialog'], [aria-modal='true'], .modal").length,
                })
                """
            )
            request_baseline = request_count

            try:
                await ctx.page.locator(selector).first.click(timeout=2500)
                await ctx.page.wait_for_timeout(900)
            except Exception:
                continue

            after = await ctx.page.evaluate(
                """
                () => ({
                  url: window.location.href,
                  mutationCount: window.__qaMutationProbe ? window.__qaMutationProbe.count : 0,
                  modalCount: document.querySelectorAll("[role='dialog'], [aria-modal='true'], .modal").length,
                })
                """
            )

            if (
                baseline["url"] == after["url"]
                and (request_count - request_baseline) == 0
                and (after["mutationCount"] - baseline["mutationCount"]) <= 1
                and after["modalCount"] <= baseline["modalCount"]
            ):
                text = candidate.get("text") or "Unnamed button"
                bugs.append(
                    BugReport(
                        id="",
                        type="dead_button",
                        severity="medium",
                        confidence=0.9,
                        page_url=ctx.page_record.url,
                        element_selector=selector,
                        short_title="Interactive element appears non-functional",
                        description=(
                            f"Clicking '{text[:60]}' did not trigger navigation, requests, modal "
                            "open, or visible state changes."
                        ),
                        reproduction_steps=[
                            f"Open {ctx.page_record.url}",
                            f"Click element: {selector}",
                            "Observe no visible result after click",
                        ],
                        screenshot_path=ctx.page_record.screenshot_path,
                        detector=self.name,
                    )
                )

        return bugs
