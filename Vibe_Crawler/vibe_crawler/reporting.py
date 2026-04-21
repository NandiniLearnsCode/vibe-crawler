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


def build_digest(report: CrawlReport) -> dict[str, Any]:
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

    return {
        "headline": headline,
        "highlights": highlights,
        "fix_first": fix_first,
        "next_actions": next_actions[:3],
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


def save_json_report(report: CrawlReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    payload["digest"] = build_digest(report)
    output_path.write_text(json.dumps(payload, indent=2))


def save_agentic_outputs(report: CrawlReport, output_path: Path) -> tuple[Path, Path] | None:
    """
    Persist a richer agentic-triage output bundle:
    - machine-friendly triage JSON
    - human-friendly markdown summary
    """
    if not report.mode.startswith("agentic"):
        return None

    triage_json_path = output_path.with_name(f"{output_path.stem}-agentic-output.json")
    triage_md_path = output_path.with_name(f"{output_path.stem}-agentic-output.md")

    triage_json = _build_agentic_output(report)
    triage_json_path.write_text(json.dumps(triage_json, indent=2))
    triage_md_path.write_text(_build_agentic_markdown(triage_json))

    return triage_json_path, triage_md_path


def _build_agentic_output(report: CrawlReport) -> dict[str, Any]:
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
        "digest": build_digest(report),
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

    lines.extend(
        [
            "",
            "## Fix First",
        ]
    )
    fix_first = digest.get("fix_first") or []
    if not fix_first:
        lines.append("- No prioritized fixes identified.")
    else:
        for item in fix_first:
            lines.extend(
                [
                    f"- [{str(item.get('severity', '')).upper()}] {item.get('title', 'Untitled finding')} ({item.get('page_url', 'n/a')})",
                    f"  - Why now: {item.get('why_now', 'n/a')}",
                    f"  - Quick fix: {item.get('quick_fix_hint', 'n/a')}",
                ]
            )

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
