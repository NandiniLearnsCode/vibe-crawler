from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from vibe_crawler.models import BugReport, CrawlReport

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


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


def build_digest(report: CrawlReport, *, presentation_mode: str = "founder") -> dict[str, Any]:
    summary = report.summary()
    total_bugs = summary.get("total_bugs", 0)
    by_severity = summary.get("bugs_by_severity", {})
    high_count = int(by_severity.get("high", 0))
    medium_count = int(by_severity.get("medium", 0))

    top_findings = sorted(
        report.bugs,
        key=lambda bug: (SEVERITY_ORDER.get(bug.severity, 9), -bug.confidence),
    )[:3]

    if total_bugs == 0:
        headline = "No high-confidence issues were found in the scanned scope."
        highlights = ["Nothing critical detected in sampled pages."]
    elif high_count > 0:
        headline = f"{high_count} high-severity issue(s) need attention first."
        highlights = [
            f"{high_count} high, {medium_count} medium, {max(total_bugs - high_count - medium_count, 0)} low findings.",
            "Start with high-severity blockers before polishing lower-severity issues.",
        ]
    else:
        headline = "No high-severity issues found; medium issues are the next priority."
        highlights = [
            f"{medium_count} medium-severity issue(s) can still affect user outcomes.",
            "Address medium findings next, then optional low-severity polish.",
        ]

    fix_first = [_digest_finding_item(bug) for bug in top_findings]
    next_actions = [item["quick_fix_hint"] for item in fix_first if item.get("quick_fix_hint")]

    founder_mode = _build_founder_mode(report, fix_first)
    return {
        "presentation_mode": presentation_mode,
        "default_view": "founder",
        "headline": headline,
        "highlights": highlights,
        "fix_first": fix_first,
        "next_actions": next_actions[:3],
        "founder_mode": founder_mode,
    }


def _digest_finding_item(bug: BugReport) -> dict[str, Any]:
    return {
        "id": bug.id,
        "severity": bug.severity,
        "type": bug.type,
        "title": bug.short_title,
        "page_url": bug.page_url,
        "confidence": bug.confidence,
        "why_now": _why_now(bug),
        "quick_fix_hint": _quick_fix_hint(bug),
    }


def _why_now(bug: BugReport) -> str:
    if bug.severity == "high":
        return "This can directly break a key user flow."
    if bug.type in {"dead_button", "form_failure"}:
        return "Users may abandon the flow when the page does not respond as expected."
    if bug.type == "broken_link":
        return "Users hit dead ends and lose trust quickly."
    return "Fixing this reduces friction and improves the overall experience."


def _quick_fix_hint(bug: BugReport) -> str:
    if bug.type == "broken_link":
        return "Validate internal href targets and add a CI link-check step."
    if bug.type == "dead_button":
        return "Bind click handlers/navigation and verify visible state change on click."
    if bug.type == "form_failure":
        return "Ensure required validation and clear success/error feedback on submit."
    if bug.type == "missing_media":
        return "Check asset paths/CDN responses and add fallback placeholders."
    if bug.type == "mobile_layout":
        return "Fix overflow/stacking in mobile CSS and retest at narrow viewports."
    if bug.type == "critical_frontend_error":
        return "Resolve console runtime errors and missing critical asset loads."
    return "Reproduce locally, patch, and verify with one focused regression test."


def _build_founder_mode(report: CrawlReport, fix_first: list[dict[str, Any]]) -> dict[str, Any]:
    summary = report.summary()
    total_bugs = summary.get("total_bugs", 0)
    severity = summary.get("bugs_by_severity", {})
    high = int(severity.get("high", 0))
    medium = int(severity.get("medium", 0))
    low = int(severity.get("low", 0))

    line_1 = f"Scanned {summary.get('pages_crawled', 0)} page(s) and found {total_bugs} high-confidence issue(s)."
    if total_bugs == 0:
        line_2 = "No blockers were detected in this sampled crawl."
        line_3 = "Next step: widen scope (more pages/depth) to increase confidence."
    else:
        line_2 = f"Severity mix: {high} high, {medium} medium, {low} low."
        if high > 0:
            line_3 = "Focus on high-severity blockers first to protect core user flows."
        elif medium > 0:
            line_3 = "No critical blockers; resolve medium issues next to reduce drop-off."
        else:
            line_3 = "Only low-severity findings remain; this is mostly polish work."

    blockers = [
        {
            "id": item.get("id", ""),
            "severity": item.get("severity", "medium"),
            "title": item.get("title", "Untitled finding"),
            "page_url": item.get("page_url", ""),
            "why_now": item.get("why_now", ""),
            "quick_fix_hint": item.get("quick_fix_hint", ""),
        }
        for item in fix_first[:3]
    ]

    ticket_lines: list[str] = []
    for idx, blocker in enumerate(blockers, start=1):
        ticket_lines.append(
            f"{idx}. [{str(blocker.get('severity', 'medium')).upper()}] {blocker.get('title', 'Untitled finding')} "
            f"| URL: {blocker.get('page_url', 'n/a')} "
            f"| Fix: {blocker.get('quick_fix_hint', 'Investigate and patch with regression check.')}"
        )
    if not ticket_lines:
        ticket_lines.append("1. No urgent engineering tickets from this run.")

    return {
        "three_line_summary": [line_1, line_2, line_3],
        "top_blockers": blockers,
        "engineering_ticket_list": ticket_lines,
        "engineering_ticket_block": "\n".join(ticket_lines),
    }


def save_json_report(report: CrawlReport, output_path: Path, *, presentation_mode: str = "founder") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    payload["digest"] = build_digest(report, presentation_mode=presentation_mode)
    output_path.write_text(json.dumps(payload, indent=2))


def save_agentic_outputs(
    report: CrawlReport, output_path: Path, *, presentation_mode: str = "founder"
) -> tuple[Path, Path] | None:
    """
    Persist a richer agentic-triage output bundle:
    - machine-friendly triage JSON
    - human-friendly markdown summary
    """
    if not report.mode.startswith("agentic"):
        return None

    triage_json_path = output_path.with_name(f"{output_path.stem}-agentic-output.json")
    triage_md_path = output_path.with_name(f"{output_path.stem}-agentic-output.md")

    triage_json = _build_agentic_output(report, presentation_mode=presentation_mode)
    triage_json_path.write_text(json.dumps(triage_json, indent=2))
    triage_md_path.write_text(_build_agentic_markdown(triage_json))

    return triage_json_path, triage_md_path


def _build_agentic_output(report: CrawlReport, *, presentation_mode: str = "founder") -> dict[str, Any]:
    actions = report.agent_trace or []
    actions_by_type: dict[str, int] = {}
    phase_counts: dict[str, int] = {}
    for action in actions:
        action_name = str(action.get("action", "unknown"))
        phase = str(action.get("phase", "unknown"))
        actions_by_type[action_name] = actions_by_type.get(action_name, 0) + 1
        phase_counts[phase] = phase_counts.get(phase, 0) + 1

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
        "digest": build_digest(report, presentation_mode=presentation_mode),
        "triage_summary": {
            "pages_crawled": summary.get("pages_crawled", 0),
            "total_bugs": summary.get("total_bugs", 0),
            "actions_total": len(actions),
            "actions_by_type": actions_by_type,
            "phase_counts": phase_counts,
            "follow_up_actions": phase_counts.get("follow_up", 0),
        },
        "agent_reasoning_trace": actions,
        "prioritized_findings": prioritized_findings,
    }


def _build_agentic_markdown(triage_output: dict[str, Any]) -> str:
    summary = triage_output.get("triage_summary", {})
    digest = triage_output.get("digest", {})
    lines = [
        f"# Agentic Triage Report: {triage_output.get('run_id', 'unknown')}",
        f"- URL: {triage_output.get('start_url', 'n/a')}",
        f"- Mode: {triage_output.get('mode', 'n/a')}",
        f"- Pages crawled: {summary.get('pages_crawled', 0)}",
        f"- Total bugs: {summary.get('total_bugs', 0)}",
        f"- Actions taken: {summary.get('actions_total', 0)}",
        "",
        "## TL;DR",
        f"- {digest.get('headline', 'No digest available.')}",
    ]

    highlights = digest.get("highlights") or []
    for line in highlights:
        lines.append(f"- {line}")

    founder_mode = digest.get("founder_mode") or {}
    founder_lines = founder_mode.get("three_line_summary") or []
    lines.extend(["", "## Founder Mode (default)", "### 3-line summary"])
    if founder_lines:
        for entry in founder_lines:
            lines.append(f"- {entry}")
    else:
        lines.append("- Founder summary unavailable.")

    lines.extend(["", "### Top blockers"])
    top_blockers = founder_mode.get("top_blockers") or []
    if not top_blockers:
        lines.append("- No blockers identified.")
    else:
        for item in top_blockers:
            lines.extend(
                [
                    f"- [{str(item.get('severity', '')).upper()}] {item.get('title', 'Untitled finding')} ({item.get('page_url', 'n/a')})",
                    f"  - Why now: {item.get('why_now', 'n/a')}",
                ]
            )

    lines.extend(["", "### Copy/paste engineering tickets", "```text"])
    tickets = founder_mode.get("engineering_ticket_list") or []
    if tickets:
        lines.extend([str(ticket) for ticket in tickets])
    else:
        lines.append("1. No urgent engineering tickets from this run.")
    lines.append("```")

    lines.extend(
        [
            "",
        "## Agent Actions by Type",
        ]
    )

    actions_by_type = summary.get("actions_by_type", {})
    if not actions_by_type:
        lines.append("- No agent actions recorded.")
    else:
        for action, count in actions_by_type.items():
            lines.append(f"- {action}: {count}")

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
