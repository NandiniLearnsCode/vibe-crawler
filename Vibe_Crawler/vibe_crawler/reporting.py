from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from vibe_crawler.models import BugReport, CrawlReport


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


def save_json_report(report: CrawlReport, output_path: Path) -> None:
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
