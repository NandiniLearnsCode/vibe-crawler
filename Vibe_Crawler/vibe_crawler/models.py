from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    agent_trace: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "start_url": self.start_url,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "mode": self.mode,
            "summary": self.summary(),
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


@dataclass(slots=True)
class DetectorContext:
    run_id: str
    output_dir: Path
    depth: int
    is_mobile: bool = False
