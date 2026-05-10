from __future__ import annotations

import csv
import io
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from vibe_crawler.models import BugReport, CrawlReport

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
WORD_RE = re.compile(r"[a-z0-9]+")
URL_RE = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)
PATH_RE = re.compile(r"/[A-Za-z0-9._~:/?#\\[\\]@!$&'()*+,;=%-]+")
HREF_RE = re.compile(r"href\\s*=\\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "page",
    "link",
    "button",
    "form",
    "error",
    "failed",
    "missing",
}


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


def build_issue_clusters(bugs: list[BugReport]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[BugReport]] = defaultdict(list)
    for bug in bugs:
        grouped[(bug.type, _root_cause_signature(bug))].append(bug)

    clusters: list[dict[str, Any]] = []
    for (bug_type, root_cause), items in grouped.items():
        affected_pages = sorted({item.page_url for item in items})
        highest = min((item.severity for item in items), key=lambda sev: SEVERITY_ORDER.get(sev, 99))
        sample_ids = [item.id for item in items[:3]]
        sample_titles = [item.short_title for item in items[:3]]
        clusters.append(
            {
                "type": bug_type,
                "root_cause_hint": root_cause,
                "severity_highest": highest,
                "occurrences": len(items),
                "affected_pages": affected_pages,
                "sample_bug_ids": sample_ids,
                "sample_titles": sample_titles,
                "recommended_fix": _cluster_fix_hint(bug_type, root_cause),
            }
        )

    clusters.sort(
        key=lambda cluster: (
            SEVERITY_ORDER.get(str(cluster.get("severity_highest", "low")), 99),
            -int(cluster.get("occurrences", 0)),
            str(cluster.get("type", "")),
        )
    )
    for idx, cluster in enumerate(clusters, start=1):
        cluster["cluster_id"] = f"CL-{idx:03d}"
    return clusters


def build_digest(
    report: CrawlReport, *, presentation_mode: str = "founder", issue_clusters: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    clusters = issue_clusters if issue_clusters is not None else build_issue_clusters(report.bugs)
    summary = report.summary()
    total_bugs = summary.get("total_bugs", 0)
    by_severity = summary.get("bugs_by_severity", {})
    high_count = int(by_severity.get("high", 0))
    medium_count = int(by_severity.get("medium", 0))

    top_findings = sorted(
        report.bugs,
        key=lambda bug: (SEVERITY_ORDER.get(bug.severity, 9), -bug.confidence),
    )[:3]
    cluster_count = len(clusters)
    collapsed = max(total_bugs - cluster_count, 0)

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
    if total_bugs > 0:
        highlights.append(f"Clustering collapsed {total_bugs} findings into {cluster_count} root-cause cluster(s).")
        if collapsed > 0:
            highlights.append(f"{collapsed} repeated findings were grouped into shared root causes.")

    fix_first = [_digest_finding_item(bug) for bug in top_findings]
    next_actions = [item["quick_fix_hint"] for item in fix_first if item.get("quick_fix_hint")]

    founder_mode = _build_founder_mode(report, fix_first, clusters)
    return {
        "presentation_mode": presentation_mode,
        "default_view": "founder",
        "headline": headline,
        "highlights": highlights,
        "fix_first": fix_first,
        "next_actions": next_actions[:3],
        "issue_clustering": {
            "total_clusters": cluster_count,
            "findings_collapsed": collapsed,
        },
        "clustered_top_issues": clusters[:3],
        "founder_mode": founder_mode,
    }


def build_plain_english_output(
    report: CrawlReport, *, issue_clusters: list[dict[str, Any]] | None = None, max_items: int = 5
) -> dict[str, Any]:
    clusters = issue_clusters if issue_clusters is not None else build_issue_clusters(report.bugs)
    summary = report.summary()
    total_bugs = int(summary.get("total_bugs", 0))
    pages_crawled = int(summary.get("pages_crawled", 0))
    severity = summary.get("bugs_by_severity", {})
    high = int(severity.get("high", 0))
    medium = int(severity.get("medium", 0))
    low = int(severity.get("low", 0))

    if total_bugs == 0:
        overview = (
            f"We checked {pages_crawled} page(s) and did not find any high-confidence user-facing issues in this run."
        )
    else:
        overview = (
            f"We checked {pages_crawled} page(s) and found {total_bugs} likely issues "
            f"({high} high, {medium} medium, {low} low). "
            f"These are grouped into {len(clusters)} root-cause group(s) to avoid duplicates."
        )

    plain_items: list[dict[str, Any]] = []
    for cluster in clusters[:max_items]:
        issue_type = str(cluster.get("type", "unknown"))
        pages = list(cluster.get("affected_pages") or [])
        title = _cluster_title(cluster)
        quick_fix = str(cluster.get("recommended_fix", "Investigate and patch this root cause."))
        explanation = _plain_english_issue_explanation(issue_type)
        engineer_prompt = (
            f"We have a {issue_type.replace('_', ' ')} issue cluster ({cluster.get('cluster_id', 'n/a')}) "
            f"affecting {len(pages)} page(s): {', '.join(pages[:5]) or 'n/a'}. "
            f"Observed root cause hint: {cluster.get('root_cause_hint', 'n/a')}. "
            f"Please identify the exact failing component and apply a durable fix. "
            f"Suggested starting point: {quick_fix}"
        )
        llm_prompt = (
            "You are helping debug a website bug cluster.\n"
            f"Issue type: {issue_type}\n"
            f"Cluster title: {title}\n"
            f"Affected pages: {', '.join(pages[:5]) or 'n/a'}\n"
            f"Observed hint: {cluster.get('root_cause_hint', 'n/a')}\n"
            f"Desired outcome: propose a concrete fix plan, likely root cause in code, and regression test checklist.\n"
            f"Current suggested fix: {quick_fix}"
        )
        plain_items.append(
            {
                "cluster_id": cluster.get("cluster_id", ""),
                "issue_title": title,
                "issue_type": issue_type,
                "severity": str(cluster.get("severity_highest", "medium")),
                "affected_pages": pages,
                "what_this_means": explanation,
                "why_users_feel_it": _cluster_why_now(cluster),
                "what_to_tell_engineer": engineer_prompt,
                "prompt_for_llm": llm_prompt,
                "suggested_fix_start": quick_fix,
            }
        )

    overall_engineer_handoff = (
        "Please prioritize high-severity clusters first, fix one root cause at a time, "
        "and confirm each fix with a quick manual regression on affected pages."
    )
    overall_llm_handoff = (
        "I have a QA crawl report with clustered issues. For each cluster, give me: "
        "(1) likely technical root cause, (2) exact code areas to inspect, "
        "(3) minimal patch plan, (4) tests to prevent regressions."
    )
    return {
        "overview": overview,
        "how_to_use": (
            "Share 'what_to_tell_engineer' with your engineer, or paste 'prompt_for_llm' into an LLM "
            "to brainstorm implementation details."
        ),
        "overall_engineer_handoff": overall_engineer_handoff,
        "overall_llm_handoff": overall_llm_handoff,
        "issues": plain_items,
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


def _build_founder_mode(
    report: CrawlReport, fix_first: list[dict[str, Any]], issue_clusters: list[dict[str, Any]]
) -> dict[str, Any]:
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

    blockers: list[dict[str, Any]] = []
    for cluster in issue_clusters[:3]:
        affected_pages = list(cluster.get("affected_pages") or [])
        blockers.append(
            {
                "id": cluster.get("cluster_id", ""),
                "cluster_id": cluster.get("cluster_id", ""),
                "severity": cluster.get("severity_highest", "medium"),
                "type": cluster.get("type", "unknown"),
                "title": _cluster_title(cluster),
                "page_url": affected_pages[0] if affected_pages else "",
                "occurrences": int(cluster.get("occurrences", 0)),
                "affected_pages": affected_pages,
                "why_now": _cluster_why_now(cluster),
                "quick_fix_hint": cluster.get("recommended_fix", "Investigate root cause and patch."),
            }
        )
    if not blockers:
        blockers = [
            {
                "id": item.get("id", ""),
                "severity": item.get("severity", "medium"),
                "type": item.get("type", "unknown"),
                "title": item.get("title", "Untitled finding"),
                "page_url": item.get("page_url", ""),
                "occurrences": 1,
                "affected_pages": [item.get("page_url", "")] if item.get("page_url") else [],
                "why_now": item.get("why_now", ""),
                "quick_fix_hint": item.get("quick_fix_hint", ""),
            }
            for item in fix_first[:3]
        ]

    ticket_lines: list[str] = []
    for idx, blocker in enumerate(blockers, start=1):
        affected = blocker.get("affected_pages") or []
        affected_summary = f"{len(affected)} page(s)" if affected else blocker.get("page_url", "n/a")
        ticket_lines.append(
            f"{idx}. [{str(blocker.get('severity', 'medium')).upper()}] {blocker.get('title', 'Untitled finding')} "
            f"| Cluster: {blocker.get('cluster_id', 'n/a')} "
            f"| Scope: {affected_summary} "
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


def _cluster_title(cluster: dict[str, Any]) -> str:
    bug_type = str(cluster.get("type", "issue")).replace("_", " ")
    root = str(cluster.get("root_cause_hint", "general root cause")).replace("_", " ")
    return f"{bug_type}: {root}"


def _cluster_why_now(cluster: dict[str, Any]) -> str:
    occurrences = int(cluster.get("occurrences", 1))
    severity = str(cluster.get("severity_highest", "medium"))
    pages = len(cluster.get("affected_pages") or [])
    if severity == "high":
        return f"High-severity root cause repeated {occurrences} time(s) across {pages} page(s)."
    return f"Shared issue appears {occurrences} time(s), so one fix can resolve multiple findings."


def _cluster_fix_hint(bug_type: str, root_cause: str) -> str:
    if bug_type == "broken_link":
        return "Patch broken href targets/routes and add automated internal link checks."
    if bug_type == "dead_button":
        return "Connect button handlers/navigation and assert visible state change after click."
    if bug_type == "form_failure":
        return "Fix submit/validation handling and return clear success or error feedback."
    if bug_type == "missing_media":
        return "Correct missing asset paths/CDN references and add fallback placeholders."
    if bug_type == "mobile_layout":
        return "Resolve responsive CSS overflow/overlap and retest at narrow breakpoints."
    if bug_type == "critical_frontend_error":
        return "Fix runtime JS/asset load error causing repeated frontend failures."
    return f"Address shared root cause: {root_cause.replace('_', ' ')}."


def _plain_english_issue_explanation(issue_type: str) -> str:
    if issue_type == "broken_link":
        return "Some links send users to the wrong place or an error page."
    if issue_type == "dead_button":
        return "A button looks clickable but nothing useful happens."
    if issue_type == "form_failure":
        return "Users may not be able to submit important forms."
    if issue_type == "missing_media":
        return "Important images or media are not loading correctly."
    if issue_type == "mobile_layout":
        return "The page layout breaks on smaller screens."
    if issue_type == "critical_frontend_error":
        return "Frontend code errors are likely breaking key interactions."
    return "Users are likely experiencing a repeatable issue that needs a code fix."


def _root_cause_signature(bug: BugReport) -> str:
    text_blob = " ".join(
        [
            bug.short_title or "",
            bug.description or "",
            bug.element_selector or "",
            " ".join(bug.console_errors[:2]),
            " ".join(bug.network_evidence[:2]),
        ]
    ).lower()
    if bug.type == "broken_link":
        target = _extract_url_or_path(text_blob)
        return f"broken_target:{target or _normalized_phrase(text_blob)}"
    if bug.type == "missing_media":
        target = _extract_url_or_path(text_blob)
        return f"asset:{target or _normalized_phrase(text_blob)}"
    if bug.type == "form_failure":
        if "required" in text_blob or "validation" in text_blob:
            return "form_validation_missing"
        if "disabled" in text_blob:
            return "form_submit_disabled"
        if "silent" in text_blob or "no response" in text_blob or "timeout" in text_blob:
            return "form_silent_submit_failure"
        return "form_submission_failure"
    if bug.type == "dead_button":
        return f"dead_click:{_selector_or_phrase(bug)}"
    if bug.type == "mobile_layout":
        if "overflow" in text_blob or "horizontal" in text_blob:
            return "mobile_overflow"
        if "off-screen" in text_blob or "offscreen" in text_blob:
            return "mobile_offscreen_controls"
        if "overlap" in text_blob:
            return "mobile_overlap"
        return "mobile_layout_breakage"
    if bug.type == "critical_frontend_error":
        if bug.console_errors:
            return f"console:{_normalized_phrase(bug.console_errors[0])}"
        return f"critical_frontend:{_normalized_phrase(text_blob)}"
    return _normalized_phrase(text_blob)


def _selector_or_phrase(bug: BugReport) -> str:
    selector = (bug.element_selector or "").strip()
    if selector:
        href_match = HREF_RE.search(selector)
        if href_match:
            return href_match.group(1)
        return _normalized_phrase(selector)
    return _normalized_phrase(f"{bug.short_title} {bug.description}")


def _extract_url_or_path(text: str) -> str | None:
    url_match = URL_RE.search(text)
    if url_match:
        return _strip_trailing_punctuation(url_match.group(0))
    path_match = PATH_RE.search(text)
    if path_match:
        path = _strip_trailing_punctuation(path_match.group(0))
        if path and path != "/":
            return path
    return None


def _strip_trailing_punctuation(value: str) -> str:
    return value.rstrip(".,);:!?\"'")


def _normalized_phrase(text: str) -> str:
    tokens = [token for token in WORD_RE.findall(text.lower()) if token not in STOPWORDS and len(token) >= 3]
    return "_".join(tokens[:6]) if tokens else "general_root_cause"


def save_json_report(report: CrawlReport, output_path: Path, *, presentation_mode: str = "founder") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clusters = build_issue_clusters(report.bugs)
    payload = report.to_dict()
    payload["digest"] = build_digest(report, presentation_mode=presentation_mode, issue_clusters=clusters)
    payload["issue_clusters"] = clusters
    payload["plain_english"] = build_plain_english_output(report, issue_clusters=clusters)
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


def save_ticket_exports(
    report: CrawlReport, output_path: Path, *, presentation_mode: str = "founder"
) -> tuple[Path, Path]:
    clusters = build_issue_clusters(report.bugs)
    digest = build_digest(report, presentation_mode=presentation_mode, issue_clusters=clusters)
    founder_mode = digest.get("founder_mode") or {}
    ticket_markdown_path = output_path.with_name(f"{output_path.stem}-tickets.md")
    ticket_csv_path = output_path.with_name(f"{output_path.stem}-tickets.csv")
    ticket_markdown_path.write_text(_build_ticket_markdown(report, digest, founder_mode))
    ticket_csv_path.write_text(_build_ticket_csv(founder_mode))
    return ticket_markdown_path, ticket_csv_path


def save_plain_english_outputs(report: CrawlReport, output_path: Path) -> tuple[Path, Path]:
    clusters = build_issue_clusters(report.bugs)
    plain = build_plain_english_output(report, issue_clusters=clusters)
    plain_json_path = output_path.with_name(f"{output_path.stem}-plain-english.json")
    plain_md_path = output_path.with_name(f"{output_path.stem}-plain-english.md")
    plain_json_path.write_text(json.dumps(plain, indent=2))
    plain_md_path.write_text(_build_plain_english_markdown(report, plain))
    return plain_json_path, plain_md_path


def _build_agentic_output(report: CrawlReport, *, presentation_mode: str = "founder") -> dict[str, Any]:
    clusters = build_issue_clusters(report.bugs)
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
        "digest": build_digest(report, presentation_mode=presentation_mode, issue_clusters=clusters),
        "plain_english": build_plain_english_output(report, issue_clusters=clusters),
        "issue_clusters": clusters,
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
            confidence_text = ""
            if item.get("confidence") is not None:
                confidence_text = f" | confidence {int(float(item.get('confidence', 0)) * 100)}%"
            lines.extend(
                [
                    f"- [{str(item.get('severity', '')).upper()}] {item.get('title', 'Untitled finding')} ({item.get('page_url', 'n/a')}){confidence_text}",
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

    plain = triage_output.get("plain_english") or {}
    lines.extend(["", "## Plain-English Handoff"])
    lines.append(f"- {plain.get('overview', 'Plain-English summary unavailable.')}")
    lines.append(f"- Engineer handoff: {plain.get('overall_engineer_handoff', 'n/a')}")
    lines.append(f"- LLM handoff: {plain.get('overall_llm_handoff', 'n/a')}")
    plain_issues = plain.get("issues") or []
    if plain_issues:
        lines.extend(["", "### Issue-by-issue plain language"])
        for item in plain_issues[:5]:
            lines.extend(
                [
                    f"- {item.get('cluster_id', 'n/a')} [{str(item.get('severity', 'medium')).upper()}] {item.get('issue_title', 'Untitled')}",
                    f"  - What this means: {item.get('what_this_means', 'n/a')}",
                    f"  - Suggested fix start: {item.get('suggested_fix_start', 'n/a')}",
                ]
            )

    issue_clusters = triage_output.get("issue_clusters") or []
    lines.extend(["", "## Root Cause Clusters"])
    if not issue_clusters:
        lines.append("- No root-cause clusters created.")
    else:
        for cluster in issue_clusters[:8]:
            lines.append(
                f"- {cluster.get('cluster_id', 'n/a')} [{str(cluster.get('severity_highest', 'low')).upper()}] "
                f"{cluster.get('type', 'unknown')} | {cluster.get('occurrences', 0)} finding(s)"
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


def _build_ticket_markdown(report: CrawlReport, digest: dict[str, Any], founder_mode: dict[str, Any]) -> str:
    lines = [
        f"# Engineering Ticket Export: {report.run_id}",
        f"- URL: {report.start_url}",
        f"- Mode: {report.mode}",
        f"- Presentation mode: {digest.get('presentation_mode', 'founder')}",
        "",
        "## 3-line summary",
    ]
    for entry in founder_mode.get("three_line_summary") or ["No summary available."]:
        lines.append(f"- {entry}")
    lines.extend(["", "## Copy/Paste Ticket List", "```text"])
    for entry in founder_mode.get("engineering_ticket_list") or ["1. No urgent engineering tickets from this run."]:
        lines.append(str(entry))
    lines.extend(["```", "", "## Detailed Cluster Tickets"])
    for idx, blocker in enumerate(founder_mode.get("top_blockers") or [], start=1):
        pages = blocker.get("affected_pages") or []
        lines.extend(
            [
                f"### Ticket {idx}: {blocker.get('title', 'Untitled finding')}",
                f"- Severity: {str(blocker.get('severity', 'medium')).upper()}",
                f"- Cluster: {blocker.get('cluster_id', 'n/a')}",
                f"- Type: {blocker.get('type', 'unknown')}",
                f"- Occurrences: {blocker.get('occurrences', 1)}",
                f"- Affected pages: {', '.join(pages) if pages else blocker.get('page_url', 'n/a')}",
                f"- Why now: {blocker.get('why_now', 'n/a')}",
                f"- Recommended fix: {blocker.get('quick_fix_hint', 'Investigate and patch.')}",
                "",
            ]
        )
    if not founder_mode.get("top_blockers"):
        lines.append("- No blocker tickets generated.")
    return "\n".join(lines).strip() + "\n"


def _build_ticket_csv(founder_mode: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ticket_id",
            "cluster_id",
            "severity",
            "type",
            "title",
            "occurrences",
            "affected_pages",
            "why_now",
            "recommended_fix",
        ]
    )
    blockers = founder_mode.get("top_blockers") or []
    for idx, blocker in enumerate(blockers, start=1):
        writer.writerow(
            [
                idx,
                blocker.get("cluster_id", ""),
                blocker.get("severity", ""),
                blocker.get("type", ""),
                blocker.get("title", ""),
                blocker.get("occurrences", 1),
                " | ".join(blocker.get("affected_pages") or []),
                blocker.get("why_now", ""),
                blocker.get("quick_fix_hint", ""),
            ]
        )
    if not blockers:
        writer.writerow([1, "", "low", "none", "No urgent engineering tickets from this run.", 0, "", "", ""])
    return output.getvalue()


def _build_plain_english_markdown(report: CrawlReport, plain: dict[str, Any]) -> str:
    lines = [
        f"# Plain-English QA Report: {report.run_id}",
        f"- URL: {report.start_url}",
        f"- Mode: {report.mode}",
        "",
        "## Simple summary",
        plain.get("overview", "No summary available."),
        "",
        "## How to use this",
        plain.get("how_to_use", ""),
        "",
        "## What to tell an engineer",
        plain.get("overall_engineer_handoff", ""),
        "",
        "## What to paste into an LLM",
        plain.get("overall_llm_handoff", ""),
        "",
        "## Issue-by-issue guide",
    ]
    issues = plain.get("issues") or []
    if not issues:
        lines.append("- No major issues detected in this run.")
    else:
        for idx, item in enumerate(issues, start=1):
            lines.extend(
                [
                    f"### {idx}. {item.get('issue_title', 'Untitled issue')} ({item.get('cluster_id', 'n/a')})",
                    f"- Severity: {str(item.get('severity', 'medium')).upper()}",
                    f"- What this means: {item.get('what_this_means', 'n/a')}",
                    f"- Why users feel it: {item.get('why_users_feel_it', 'n/a')}",
                    f"- Suggested fix start: {item.get('suggested_fix_start', 'n/a')}",
                    f"- Engineer handoff: {item.get('what_to_tell_engineer', 'n/a')}",
                    "- LLM prompt:",
                    "```text",
                    str(item.get("prompt_for_llm", "n/a")),
                    "```",
                    "",
                ]
            )
    return "\n".join(lines).strip() + "\n"
