from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from vibe_crawler.models import BugReport, PageRecord

ActionType = Literal["forms", "mobile", "dead_buttons", "broken_links", "console"]


@dataclass(slots=True)
class PlannedAction:
    action_type: ActionType
    reason: str


def next_actions(
    *,
    page: PageRecord,
    base_findings: list[BugReport],
    max_actions: int = 3,
) -> list[PlannedAction]:
    """
    Deterministic planner for agentic triage.

    It infers follow-up probes from concrete evidence on the page
    and returns a bounded list of actions.
    """
    actions: list[PlannedAction] = []
    if max_actions <= 0:
        return actions

    has_forms = _page_has_form_hints(page)
    has_runtime_hints = bool(page.console_errors or page.page_errors)
    has_request_failures = bool(page.failed_requests or page.error_responses)
    has_many_links = len(page.discovered_links) >= 8
    has_actionable_cta_hints = _page_has_cta_hints(page)

    finding_types = {bug.type for bug in base_findings}
    if "form_failure" in finding_types or has_forms:
        actions.append(PlannedAction("forms", "page appears to contain form interactions worth probing"))

    if "dead_button" in finding_types or has_actionable_cta_hints:
        actions.append(PlannedAction("dead_buttons", "page likely has CTA/button interactions to validate"))

    if "critical_frontend_error" in finding_types or has_runtime_hints:
        actions.append(PlannedAction("console", "runtime/console hints suggest deeper frontend stability checks"))

    if "missing_media" in finding_types or has_request_failures:
        actions.append(PlannedAction("mobile", "re-check under mobile viewport for compounded rendering issues"))

    if has_many_links:
        actions.append(PlannedAction("broken_links", "link-heavy page benefits from stronger internal link validation"))

    # Deduplicate by action type while preserving order.
    deduped: list[PlannedAction] = []
    seen: set[ActionType] = set()
    for action in actions:
        if action.action_type in seen:
            continue
        seen.add(action.action_type)
        deduped.append(action)
        if len(deduped) >= max_actions:
            break
    return deduped


def _page_has_form_hints(page: PageRecord) -> bool:
    lowered = page.url.lower()
    return any(token in lowered for token in ("contact", "signup", "sign-up", "register", "waitlist"))


def _page_has_cta_hints(page: PageRecord) -> bool:
    lowered = page.url.lower()
    return any(token in lowered for token in ("pricing", "product", "features", "start", "trial", "demo"))
