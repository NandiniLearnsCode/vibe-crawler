from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SEVERITY_PRIORITY = {"high": 0, "medium": 1, "low": 2}


@dataclass(slots=True)
class NetworkFailure:
    url: str
    resource_type: str
    reason: str


@dataclass(slots=True)
class NetworkErrorResponse:
    url: str
    status: int
    resource_type: str


@dataclass(slots=True)
class BugReport:
    id: str
    type: str
    severity: str
    confidence: float
    page_url: str
    element_selector: str | None
    short_title: str
    description: str
    reproduction_steps: list[str]
    screenshot_path: str | None
    console_errors: list[str] = field(default_factory=list)
    network_evidence: list[str] = field(default_factory=list)
    detector: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PageRecord:
    url: str
    depth: int
    status_code: int | None
    discovered_links: list[str]
    screenshot_path: str | None
    console_errors: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    crawl_errors: list[str] = field(default_factory=list)
    failed_requests: list[NetworkFailure] = field(default_factory=list)
    error_responses: list[NetworkErrorResponse] = field(default_factory=list)
    crawled_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["failed_requests"] = [asdict(item) for item in self.failed_requests]
        payload["error_responses"] = [asdict(item) for item in self.error_responses]
        return payload


@dataclass(slots=True)
class CrawlReport:
    run_id: str
    start_url: str
    started_at: str
    finished_at: str | None
    pages: list[PageRecord]
    bugs: list[BugReport]
    output_path: Path | None = None
    mode: str = "deterministic"
    presentation_mode: str = "founder"
    agent_trace: list[dict[str, Any]] = field(default_factory=list)

    def executive_digest(self) -> dict[str, Any]:
        bugs_sorted = sorted(
            self.bugs,
            key=lambda bug: (
                SEVERITY_PRIORITY.get(bug.severity, 3),
                -bug.confidence,
            ),
        )
        top_issues = [
            {
                "id": bug.id,
                "title": bug.short_title,
                "type": bug.type,
                "severity": bug.severity,
                "confidence": bug.confidence,
                "page_url": bug.page_url,
            }
            for bug in bugs_sorted[:3]
        ]
        next_actions = [
            f"Fix [{bug.severity.upper()}] {bug.short_title} on {bug.page_url}"
            for bug in bugs_sorted[:3]
        ]
        return {
            "headline": self._digest_headline(),
            "top_issues": top_issues,
            "next_actions": next_actions,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "start_url": self.start_url,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "mode": self.mode,
            "presentation_mode": self.presentation_mode,
            "summary": self.summary(),
            "digest": self.executive_digest(),
            "pages": [page.to_dict() for page in self.pages],
            "bugs": [bug.to_dict() for bug in self.bugs],
            "agent_trace": self.agent_trace,
        }

    def summary(self) -> dict[str, Any]:
        by_severity = {"high": 0, "medium": 0, "low": 0}
        by_type: dict[str, int] = {}
        for bug in self.bugs:
            by_severity[bug.severity] = by_severity.get(bug.severity, 0) + 1
            by_type[bug.type] = by_type.get(bug.type, 0) + 1
        return {
            "pages_crawled": len(self.pages),
            "total_bugs": len(self.bugs),
            "bugs_by_severity": by_severity,
            "bugs_by_type": by_type,
        }

    def _digest_headline(self) -> str:
        if not self.bugs:
            return "No high-confidence issues detected in the scanned scope."
        counts = self.summary()["bugs_by_severity"]
        high = counts.get("high", 0)
        medium = counts.get("medium", 0)
        if high > 0:
            return (
                f"Immediate attention: {high} high-severity issue(s) can impact key user flows."
            )
        if medium > 0:
            return (
                f"Moderate risk: {medium} medium-severity issue(s) may reduce conversion or usability."
            )
        return "Mostly healthy: only low-severity issues were found."


@dataclass(slots=True)
class DetectorContext:
    run_id: str
    output_dir: Path
    depth: int
    is_mobile: bool = False
