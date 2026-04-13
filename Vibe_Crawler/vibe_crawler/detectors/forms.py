from __future__ import annotations

from vibe_crawler.models import BugReport

from .base import PageScanContext

UNSAFE_FORM_KEYWORDS = ("payment", "checkout", "billing", "card", "delete", "remove", "logout")


class FormsDetector:
    name = "forms"

    async def detect(self, ctx: PageScanContext) -> list[BugReport]:
        if not ctx.config.include_form_checks:
            return []
        if ctx.mobile:
            return []

        form_candidates = await ctx.page.evaluate(
            """
            () => {
              const forms = Array.from(document.querySelectorAll("form"));
              const output = [];
              let formProbeCounter = 0;
              let submitProbeCounter = 0;
              for (const form of forms) {
                if (output.length >= 6) break;
                const rect = form.getBoundingClientRect();
                const style = window.getComputedStyle(form);
                if (rect.width < 120 || rect.height < 40) continue;
                if (style.display === "none" || style.visibility === "hidden") continue;

                const controls = Array.from(form.querySelectorAll("input, textarea, select"));
                const inputTypes = controls
                  .filter(el => el.tagName.toLowerCase() === "input")
                  .map(el => (el.getAttribute("type") || "text").toLowerCase());
                const requiredCount = controls.filter(el => el.required).length;
                const hasPassword = inputTypes.includes("password");
                const hasSubmit = Boolean(form.querySelector("button[type='submit'], input[type='submit'], button:not([type])"));
                const submitEl = form.querySelector("button[type='submit'], input[type='submit'], button:not([type])");
                const textSignals = `${form.id} ${form.className} ${form.getAttribute("action") || ""}`.toLowerCase();
                const likelySimple = controls.length <= 12 && controls.length > 0;

                formProbeCounter += 1;
                const formProbeId = `qa-form-probe-${formProbeCounter}`;
                form.setAttribute("data-qa-form-probe", formProbeId);

                let submitSelector = null;
                if (submitEl) {
                  submitProbeCounter += 1;
                  const submitProbeId = `qa-submit-probe-${submitProbeCounter}`;
                  submitEl.setAttribute("data-qa-submit-probe", submitProbeId);
                  submitSelector = `[data-qa-submit-probe="${submitProbeId}"]`;
                }

                output.push({
                  selector: `[data-qa-form-probe="${formProbeId}"]`,
                  action: form.getAttribute("action") || "",
                  method: (form.getAttribute("method") || "get").toLowerCase(),
                  hasPassword,
                  hasSubmit,
                  requiredCount,
                  controlCount: controls.length,
                  inputTypes,
                  likelySimple,
                  textSignals,
                  submitSelector,
                });
              }
              return output;
            }
            """
        )

        request_count = 0

        def on_request(_) -> None:
            nonlocal request_count
            request_count += 1

        ctx.page.on("request", on_request)

        bugs: list[BugReport] = []
        for form in form_candidates[: ctx.config.max_forms_per_page]:
            selector = form["selector"]
            action_signature = f"{form['action']} {ctx.page_record.url} {form['textSignals']}".lower()
            if any(keyword in action_signature for keyword in UNSAFE_FORM_KEYWORDS):
                continue
            if form["hasPassword"] or not form["likelySimple"]:
                continue

            if not form["hasSubmit"] or not form["submitSelector"]:
                bugs.append(
                    BugReport(
                        id="",
                        type="form_failure",
                        severity="high",
                        confidence=0.97,
                        page_url=ctx.page_record.url,
                        element_selector=selector,
                        short_title="Form has no usable submit control",
                        description="Visible form does not expose a clear submit button/input.",
                        reproduction_steps=[
                            f"Open {ctx.page_record.url}",
                            f"Inspect form: {selector}",
                            "Observe missing submit control",
                        ],
                        screenshot_path=ctx.page_record.screenshot_path,
                        detector=self.name,
                    )
                )
                continue

            submit_selector = form["submitSelector"]
            try:
                disabled = await ctx.page.evaluate(
                    "(sel) => Boolean(document.querySelector(sel)?.disabled)", submit_selector
                )
            except Exception:
                continue
            if disabled:
                bugs.append(
                    BugReport(
                        id="",
                        type="form_failure",
                        severity="high",
                        confidence=0.95,
                        page_url=ctx.page_record.url,
                        element_selector=submit_selector,
                        short_title="Submit button is disabled",
                        description="Form submit button is disabled and cannot be used.",
                        reproduction_steps=[
                            f"Open {ctx.page_record.url}",
                            f"Locate submit button: {submit_selector}",
                            "Observe disabled state",
                        ],
                        screenshot_path=ctx.page_record.screenshot_path,
                        detector=self.name,
                    )
                )
                continue

            if form["requiredCount"] > 0:
                await ctx.page.evaluate(
                    """
                    (sel) => {
                      const form = document.querySelector(sel);
                      if (!form) return;
                      for (const el of form.querySelectorAll("input, textarea")) {
                        if (el.required && !el.disabled) el.value = "";
                      }
                    }
                    """,
                    selector,
                )
                try:
                    await ctx.page.locator(submit_selector).first.click(timeout=2500)
                    await ctx.page.wait_for_timeout(700)
                except Exception:
                    pass

                missing_feedback = await ctx.page.evaluate(
                    """
                    (sel) => {
                      const form = document.querySelector(sel);
                      if (!form) return false;
                      const invalidCount = form.querySelectorAll(":invalid").length;
                      const feedbackEls = form.querySelectorAll(
                        ".error, [role='alert'], [aria-invalid='true'], .invalid-feedback, .field-error"
                      );
                      const hasVisibleFeedback = Array.from(feedbackEls).some((el) => {
                        const text = (el.textContent || "").trim();
                        const rect = el.getBoundingClientRect();
                        return text.length > 0 && rect.height > 0 && rect.width > 0;
                      });
                      return invalidCount > 0 && !hasVisibleFeedback;
                    }
                    """,
                    selector,
                )
                if missing_feedback:
                    bugs.append(
                        BugReport(
                            id="",
                            type="form_failure",
                            severity="medium",
                            confidence=0.86,
                            page_url=ctx.page_record.url,
                            element_selector=selector,
                            short_title="Required fields missing with no visible validation",
                            description=(
                                "Submitting with required fields empty leaves invalid fields but no visible "
                                "validation feedback."
                            ),
                            reproduction_steps=[
                                f"Open {ctx.page_record.url}",
                                "Leave required fields blank",
                                "Submit the form",
                                "Observe no visible validation message",
                            ],
                            screenshot_path=ctx.page_record.screenshot_path,
                            detector=self.name,
                        )
                    )

            await ctx.page.evaluate(
                """
                (sel) => {
                  const form = document.querySelector(sel);
                  if (!form) return;
                  for (const el of form.querySelectorAll("input, textarea, select")) {
                    if (el.disabled || el.type === "hidden" || el.type === "file") continue;
                    const type = (el.getAttribute("type") || "").toLowerCase();
                    if (type === "checkbox" || type === "radio") {
                      el.checked = true;
                      continue;
                    }
                    if (type === "email") el.value = "qa-test@example.com";
                    else if (type === "tel") el.value = "5551234567";
                    else if (type === "url") el.value = "https://example.com";
                    else el.value = "QA Test";
                    el.dispatchEvent(new Event("input", { bubbles: true }));
                    el.dispatchEvent(new Event("change", { bubbles: true }));
                  }
                }
                """,
                selector,
            )

            baseline = await ctx.page.evaluate(
                "() => ({ url: window.location.href, success: document.querySelectorAll('.success, .alert-success, [data-success], [role=\"status\"]').length })"
            )
            request_baseline = request_count

            try:
                await ctx.page.locator(submit_selector).first.click(timeout=2500)
                await ctx.page.wait_for_timeout(1400)
            except Exception as exc:
                bugs.append(
                    BugReport(
                        id="",
                        type="form_failure",
                        severity="high",
                        confidence=0.95,
                        page_url=ctx.page_record.url,
                        element_selector=submit_selector,
                        short_title="Submit interaction fails",
                        description=f"Clicking submit raised an exception: {exc}",
                        reproduction_steps=[
                            f"Open {ctx.page_record.url}",
                            "Fill visible form fields with dummy values",
                            "Click submit",
                            "Observe submit interaction failure",
                        ],
                        screenshot_path=ctx.page_record.screenshot_path,
                        detector=self.name,
                    )
                )
                continue

            outcome = await ctx.page.evaluate(
                """
                () => {
                  const errors = Array.from(document.querySelectorAll(".error, .alert-danger, [role='alert']"));
                  const blankErrors = errors.filter((el) => (el.textContent || "").trim().length === 0).length;
                  const visibleErrors = errors.filter((el) => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                  }).length;
                  const success = document.querySelectorAll(".success, .alert-success, [data-success], [role='status']").length;
                  return {
                    url: window.location.href,
                    blankErrors,
                    visibleErrors,
                    success,
                  };
                }
                """
            )

            if outcome["blankErrors"] > 0:
                bugs.append(
                    BugReport(
                        id="",
                        type="form_failure",
                        severity="medium",
                        confidence=0.9,
                        page_url=ctx.page_record.url,
                        element_selector=selector,
                        short_title="Form shows blank error state",
                        description="Form displays an error container with no meaningful text.",
                        reproduction_steps=[
                            f"Open {ctx.page_record.url}",
                            "Fill visible form fields with dummy values",
                            "Submit form",
                            "Observe blank/empty error message",
                        ],
                        screenshot_path=ctx.page_record.screenshot_path,
                        detector=self.name,
                    )
                )

            if (
                outcome["url"] == baseline["url"]
                and (request_count - request_baseline) == 0
                and outcome["success"] == baseline["success"]
                and outcome["visibleErrors"] == 0
            ):
                bugs.append(
                    BugReport(
                        id="",
                        type="form_failure",
                        severity="high",
                        confidence=0.9,
                        page_url=ctx.page_record.url,
                        element_selector=selector,
                        short_title="Form submission appears to silently fail",
                        description=(
                            "Submitting a visible form caused no navigation, no network request, "
                            "and no visible success/error feedback."
                        ),
                        reproduction_steps=[
                            f"Open {ctx.page_record.url}",
                            "Fill visible form fields with dummy values",
                            "Submit form",
                            "Observe no success or error feedback",
                        ],
                        screenshot_path=ctx.page_record.screenshot_path,
                        detector=self.name,
                    )
                )

        return bugs
