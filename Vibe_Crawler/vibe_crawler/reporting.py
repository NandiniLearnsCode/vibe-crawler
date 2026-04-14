from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from vibe_crawler.models import BugReport, CrawlReport

CONVERSION_PATH_HINTS = ("pricing", "signup", "register", "trial", "demo", "contact", "book")
SUPPORT_PATH_HINTS = ("docs", "help", "support", "faq")
TRUST_PATH_HINTS = ("about", "company", "customers", "testimonials", "security")


def assign_bug_ids(run_id: str, bugs: list[BugReport]) -> list[BugReport]:
    for idx, bug in enumerate(bugs, start=1):
        if bug.id:
            continue
        bug.id = f"{run_id}-BUG-{idx:04d}"
    return bugs


def deduplicate_bugs(bugs: list[BugReport]) -> list[BugReport]:
    seen: set[str] = set()
    output: list[BugReport] = []
    for bug in bugs:
        fingerprint = "::".join(
            [
                bug.type,
                bug.page_url,
                bug.element_selector or "",
                bug.short_title.lower(),
            ]
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        output.append(bug)
    return output


def annotate_bug_impacts(bugs: list[BugReport]) -> None:
    for bug in bugs:
        if bug.impact_area and bug.affected_journey and bug.impact_reason:
            continue
        impact_area, journey, reason = _classify_bug_impact(bug)
        bug.impact_area = bug.impact_area or impact_area
        bug.affected_journey = bug.affected_journey or journey
        bug.impact_reason = bug.impact_reason or reason


def _classify_bug_impact(bug: BugReport) -> tuple[str, str, str]:
    path = urlparse(bug.page_url).path.lower()
    text = " ".join([bug.short_title, bug.description, bug.element_selector or ""]).lower()
    conversion_related = _contains_any(path, CONVERSION_PATH_HINTS) or _contains_any(text, CONVERSION_PATH_HINTS)
    journey = _journey_from_path(path)

    if bug.type == "form_failure":
        return (
            "conversion",
            "signup / lead capture",
            "Form breakdown can block visitors from submitting demo, trial, or contact intent.",
        )
    if bug.type == "broken_link":
        if conversion_related:
            return (
                "conversion",
                "signup / lead capture",
                "Broken navigation blocks visitors from reaching a key conversion step.",
            )
        return (
            "usability",
            journey,
            "Broken page flow increases friction and can cause users to abandon the journey.",
        )
    if bug.type == "dead_button":
        if conversion_related:
            return (
                "conversion",
                "signup / lead capture",
                "A non-working CTA can directly prevent lead or signup actions.",
            )
        return (
            "usability",
            journey,
            "A non-responsive control reduces task completion and creates confusion.",
        )
    if bug.type == "critical_frontend_error":
        return (
            "trust" if bug.severity == "high" else "usability",
            journey,
            "Visible runtime errors can make the product appear unreliable and break core interactions.",
        )
    if bug.type == "mobile_layout":
        if conversion_related:
            return (
                "conversion",
                "mobile conversion path",
                "Mobile layout breakage can prevent visitors from completing key actions on phones.",
            )
        if bug.severity == "low":
            return (
                "cosmetic",
                "mobile browsing",
                "Visual mobile defects degrade polish but may not block completion.",
            )
        return (
            "usability",
            "mobile browsing",
            "Mobile interaction friction can reduce engagement and completion rates.",
        )
    if bug.type == "missing_media":
        if _contains_any(text, ("logo", "hero", "brand", "testimonial")):
            return (
                "trust",
                journey,
                "Missing key visuals can reduce perceived legitimacy and quality.",
            )
        if bug.severity == "low":
            return (
                "cosmetic",
                journey,
                "Missing non-critical media hurts visual quality but has limited functional impact.",
            )
        return (
            "usability",
            journey,
            "Missing media can hide context users need to understand page content.",
        )
    return (
        "usability",
        journey,
        "This issue introduces user friction and can reduce successful task completion.",
    )


def _journey_from_path(path: str) -> str:
    if _contains_any(path, CONVERSION_PATH_HINTS):
        return "signup / lead capture"
    if _contains_any(path, SUPPORT_PATH_HINTS):
        return "self-serve support"
    if _contains_any(path, TRUST_PATH_HINTS):
        return "trust evaluation"
    if path in {"", "/"}:
        return "first impression / homepage"
    return "general navigation"


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(hint in text for hint in hints)


def save_json_report(report: CrawlReport, output_path: Path) -> None:
    annotate_bug_impacts(report.bugs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2))


def save_agentic_outputs(report: CrawlReport, output_path: Path) -> tuple[Path, Path] | None:
    """
    Persist a richer agentic-triage output bundle:
    - machine-friendly triage JSON
    - human-friendly markdown summary
    """
    if not report.mode.startswith("agentic"):
        return None

    annotate_bug_impacts(report.bugs)
    triage_json_path = output_path.with_name(f"{output_path.stem}-agentic-output.json")
    triage_md_path = output_path.with_name(f"{output_path.stem}-agentic-output.md")

    triage_json = _build_agentic_output(report)
    triage_json_path.write_text(json.dumps(triage_json, indent=2))
    triage_md_path.write_text(_build_agentic_markdown(triage_json))

    return triage_json_path, triage_md_path


def _build_agentic_output(report: CrawlReport) -> dict[str, Any]:
    annotate_bug_impacts(report.bugs)
    actions = report.agent_trace or []
    actions_by_type: dict[str, int] = {}
    phase_counts: dict[str, int] = {}
    impact_breakdown: dict[str, int] = {}
    for action in actions:
        action_name = str(action.get("action", "unknown"))
        phase = str(action.get("phase", "unknown"))
        actions_by_type[action_name] = actions_by_type.get(action_name, 0) + 1
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
    for bug in report.bugs:
        impact_key = bug.impact_area or "unclassified"
        impact_breakdown[impact_key] = impact_breakdown.get(impact_key, 0) + 1

    prioritized_findings = sorted(
        [bug.to_dict() for bug in report.bugs],
        key=lambda b: (
            {"high": 0, "medium": 1, "low": 2}.get(str(b.get("severity", "low")), 3),
            -float(b.get("confidence", 0)),
        ),
    )

    summary = report.summary()
    return {
        "run_id": report.run_id,
        "start_url": report.start_url,
        "mode": report.mode,
        "triage_summary": {
            "pages_crawled": summary.get("pages_crawled", 0),
            "total_bugs": summary.get("total_bugs", 0),
            "actions_total": len(actions),
            "actions_by_type": actions_by_type,
            "phase_counts": phase_counts,
            "follow_up_actions": phase_counts.get("follow_up", 0),
            "impact_breakdown": impact_breakdown,
        },
        "agent_reasoning_trace": actions,
        "prioritized_findings": prioritized_findings,
    }


def _build_agentic_markdown(triage_output: dict[str, Any]) -> str:
    summary = triage_output.get("triage_summary", {})
    lines = [
        f"# Agentic Triage Report: {triage_output.get('run_id', 'unknown')}",
        f"- URL: {triage_output.get('start_url', 'n/a')}",
        f"- Mode: {triage_output.get('mode', 'n/a')}",
        f"- Pages crawled: {summary.get('pages_crawled', 0)}",
        f"- Total bugs: {summary.get('total_bugs', 0)}",
        f"- Actions taken: {summary.get('actions_total', 0)}",
        "",
        "## Agent Actions by Type",
    ]

    actions_by_type = summary.get("actions_by_type", {})
    if not actions_by_type:
        lines.append("- No agent actions recorded.")
    else:
        for action, count in actions_by_type.items():
            lines.append(f"- {action}: {count}")

    impact_breakdown = summary.get("impact_breakdown", {})
    lines.extend(["", "## Business Impact Breakdown"])
    if not impact_breakdown:
        lines.append("- No impact-tagged findings.")
    else:
        for impact_area, count in impact_breakdown.items():
            lines.append(f"- {impact_area}: {count}")

    lines.extend(["", "## Prioritized Findings"])
    findings = triage_output.get("prioritized_findings", [])
    if not findings:
        lines.append("- No high-confidence findings.")
    else:
        for idx, bug in enumerate(findings, start=1):
            confidence = int(float(bug.get("confidence", 0)) * 100)
            lines.extend(
                [
                    f"### {idx}. [{str(bug.get('severity', '')).upper()}] {bug.get('short_title', 'Untitled finding')}",
                    f"- Type: {bug.get('type', 'unknown')}",
                    f"- Confidence: {confidence}%",
                    f"- URL: {bug.get('page_url', 'n/a')}",
                    f"- Description: {bug.get('description', '')}",
                    f"- Impact area: {bug.get('impact_area', 'n/a')}",
                    f"- Affected journey: {bug.get('affected_journey', 'n/a')}",
                    f"- Why this matters: {bug.get('impact_reason', 'n/a')}",
                ]
            )
            steps = bug.get("reproduction_steps") or []
            if steps:
                lines.append("- Reproduction steps:")
                for step in steps:
                    lines.append(f"  - {step}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def human_summary(report: CrawlReport) -> str:
    if not report.bugs:
        return "No high-confidence bugs detected in configured crawl scope."

    grouped: dict[str, list[BugReport]] = defaultdict(list)
    for bug in report.bugs:
        grouped[bug.severity].append(bug)

    severity_order = ("high", "medium", "low")
    lines = [
        f"Crawl run {report.run_id}",
        f"Pages crawled: {len(report.pages)}",
        f"Bugs found: {len(report.bugs)}",
        "",
    ]
    for severity in severity_order:
        items = grouped.get(severity, [])
        if not items:
            continue
        lines.append(f"{severity.upper()} ({len(items)})")
        for bug in items:
            lines.append(f"- [{bug.type}] {bug.short_title} ({bug.page_url})")
        lines.append("")
    return "\n".join(lines).strip()
