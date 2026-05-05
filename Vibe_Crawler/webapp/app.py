from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, HttpUrl

from vibe_crawler.agentic import AgenticRunner
from vibe_crawler.config import CrawlConfig
from vibe_crawler.orchestrator import CrawlOrchestrator
from vibe_crawler.reporting import human_summary, save_agentic_outputs, save_json_report, save_ticket_exports

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
JOBS_DIR = BASE_DIR / "jobs"
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_REPORT_DIR = ARTIFACTS_DIR / "reports"
ARTIFACTS_REPORT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_SCREENSHOT_DIR = ARTIFACTS_DIR / "screenshots"
ARTIFACTS_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)


class CrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: int = Field(default=8, ge=1, le=40)
    max_depth: int = Field(default=2, ge=0, le=5)
    timeout_ms: int = Field(default=20_000, ge=1000, le=120_000)
    include_mobile_checks: bool = True
    include_form_checks: bool = True
    mode: str = Field(default="deterministic", pattern="^(deterministic|agentic)$")
    view_mode: str = Field(default="founder", pattern="^(founder|detailed)$")


class CrawlResponse(BaseModel):
    job_id: str
    status: str


class TicketPushPreviewRequest(BaseModel):
    provider: str = Field(pattern="^(github|linear)$")
    github_repo: str | None = None
    linear_team_id: str | None = None
    linear_label_ids: list[str] = Field(default_factory=list)
    max_tickets: int = Field(default=20, ge=1, le=100)


class TicketPushConfirmRequest(BaseModel):
    preview_token: str = Field(min_length=8)


class PlainEnglishRequest(BaseModel):
    audience: str = Field(default="non-technical", pattern="^(non-technical|engineer|llm)$")
    max_items: int = Field(default=5, ge=1, le=20)


@dataclass(slots=True)
class JobState:
    job_id: str
    url: str
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    report_path: str | None = None
    ticket_export_markdown_path: str | None = None
    ticket_export_csv_path: str | None = None
    agentic_json_path: str | None = None
    agentic_markdown_path: str | None = None
    summary: str | None = None
    pages_crawled: int = 0
    bugs_found: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "url": self.url,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "report_path": self.report_path,
            "ticket_export_markdown_path": self.ticket_export_markdown_path,
            "ticket_export_csv_path": self.ticket_export_csv_path,
            "agentic_json_path": self.agentic_json_path,
            "agentic_markdown_path": self.agentic_markdown_path,
            "summary": self.summary,
            "pages_crawled": self.pages_crawled,
            "bugs_found": self.bugs_found,
        }


@dataclass(slots=True)
class TicketPushPreviewState:
    preview_token: str
    job_id: str
    provider: str
    target: str
    tickets: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


app = FastAPI(title="Vibe Crawler UI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")

_jobs: dict[str, JobState] = {}
_tasks: dict[str, asyncio.Task] = {}
_job_lock = asyncio.Lock()
_ticket_push_previews: dict[tuple[str, str], TicketPushPreviewState] = {}


def _job_paths(job_id: str) -> tuple[Path, Path]:
    screenshot_dir = ARTIFACTS_SCREENSHOT_DIR / job_id
    report_path = ARTIFACTS_REPORT_DIR / f"{job_id}.json"
    return screenshot_dir, report_path


def _write_job_metadata(job: JobState) -> None:
    metadata_path = JOBS_DIR / f"{job.job_id}.json"
    metadata_path.write_text(json.dumps(job.to_dict(), indent=2))


async def _run_crawl_job(job: JobState, request: CrawlRequest) -> None:
    screenshot_dir, report_path = _job_paths(job.job_id)
    job.status = "running"
    job.started_at = datetime.now(timezone.utc).isoformat()
    _write_job_metadata(job)
    try:
        config = CrawlConfig(
            start_url=str(request.url),
            max_pages=request.max_pages,
            max_depth=request.max_depth,
            timeout_ms=request.timeout_ms,
            include_mobile_checks=request.include_mobile_checks,
            include_form_checks=request.include_form_checks,
            presentation_mode=request.view_mode,
            screenshot_dir=screenshot_dir,
            output_path=report_path,
        )
        if request.mode == "agentic":
            runner = AgenticRunner(config=config, headless=True, max_actions=max(20, request.max_pages * 6))
            report = await runner.run()
        else:
            orchestrator = CrawlOrchestrator(config=config, headless=True)
            report = await orchestrator.run()
        save_json_report(report, report_path, presentation_mode=config.presentation_mode)
        ticket_exports = save_ticket_exports(report, report_path, presentation_mode=config.presentation_mode)
        triage_outputs = save_agentic_outputs(report, report_path, presentation_mode=config.presentation_mode)

        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc).isoformat()
        job.report_path = str(report_path)
        if ticket_exports:
            job.ticket_export_markdown_path = str(ticket_exports[0])
            job.ticket_export_csv_path = str(ticket_exports[1])
        if triage_outputs:
            job.agentic_json_path = str(triage_outputs[0])
            job.agentic_markdown_path = str(triage_outputs[1])
        job.summary = human_summary(report)
        job.pages_crawled = len(report.pages)
        job.bugs_found = len(report.bugs)
        _write_job_metadata(job)
    except Exception as exc:
        log.exception("job %s failed", job.job_id)
        job.status = "failed"
        job.finished_at = datetime.now(timezone.utc).isoformat()
        job.error = str(exc)
        _write_job_metadata(job)


async def _create_job(request: CrawlRequest) -> JobState:
    async with _job_lock:
        job_id = uuid.uuid4().hex[:12]
        job = JobState(job_id=job_id, url=str(request.url))
        _jobs[job_id] = job
        _write_job_metadata(job)
        task = asyncio.create_task(_run_crawl_job(job, request))
        _tasks[job_id] = task
    return job


def _load_report_payload(report_path: str) -> dict[str, Any]:
    return json.loads(Path(report_path).read_text())


def _build_issue_payload_preview(job_id: str, report: dict[str, Any], max_items: int = 20) -> dict[str, Any]:
    founder = (report.get("digest") or {}).get("founder_mode") or {}
    blockers = founder.get("top_blockers") or []
    issues: list[dict[str, Any]] = []
    for blocker in blockers[:max_items]:
        severity = str(blocker.get("severity", "medium")).upper()
        title = str(blocker.get("title", "Untitled issue"))
        labels = [str(blocker.get("type", "crawler")), str(blocker.get("severity", "medium"))]
        pages = blocker.get("affected_pages") or []
        page_scope = ", ".join(pages[:5]) if pages else str(blocker.get("page_url", "n/a"))
        body = "\n".join(
            [
                f"Run: {job_id}",
                f"Cluster: {blocker.get('cluster_id', 'n/a')}",
                f"Severity: {severity}",
                f"Occurrences: {blocker.get('occurrences', 1)}",
                f"Affected pages: {page_scope}",
                f"Why now: {blocker.get('why_now', 'n/a')}",
                f"Recommended fix: {blocker.get('quick_fix_hint', 'Investigate and patch.')}",
            ]
        )
        issues.append(
            {
                "title": f"[{severity}] {title}",
                "body": body,
                "labels": labels,
            }
        )
    return {
        "summary": {
            "issues_count": len(issues),
        },
        "issues": issues,
    }


def _build_github_issue_markdown(issues: list[dict[str, Any]]) -> str:
    lines = ["# GitHub Issues Export", ""]
    if not issues:
        return "# GitHub Issues Export\n\nNo issues generated.\n"
    for idx, issue in enumerate(issues, start=1):
        lines.extend(
            [
                f"## {idx}. {issue.get('title', 'Untitled issue')}",
                f"Labels: {', '.join(issue.get('labels') or [])}",
                "",
                issue.get("body", ""),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _build_linear_issue_markdown(issues: list[dict[str, Any]]) -> str:
    lines = ["# Linear Issues Export", ""]
    if not issues:
        return "# Linear Issues Export\n\nNo issues generated.\n"
    for idx, issue in enumerate(issues, start=1):
        lines.extend(
            [
                f"## {idx}. {issue.get('title', 'Untitled issue')}",
                f"Priority labels: {', '.join(issue.get('labels') or [])}",
                "",
                issue.get("body", ""),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _build_plain_english_pack(report: dict[str, Any], audience: str = "non-technical", max_items: int = 5) -> dict[str, Any]:
    digest = report.get("digest") or {}
    founder = digest.get("founder_mode") or {}
    blockers = list(founder.get("top_blockers") or [])[:max_items]
    summary_lines = founder.get("three_line_summary") or []
    header = summary_lines[0] if summary_lines else str(digest.get("headline", "Run completed."))

    items: list[dict[str, Any]] = []
    for idx, blocker in enumerate(blockers, start=1):
        severity = str(blocker.get("severity", "medium")).upper()
        title = str(blocker.get("title", "Issue"))
        pages = blocker.get("affected_pages") or []
        where = ", ".join(pages[:3]) if pages else str(blocker.get("page_url", "n/a"))
        what_happened = f"{title} is happening on {where}."
        why_it_matters = str(blocker.get("why_now", "This makes the website harder to use."))
        fix_hint = str(blocker.get("quick_fix_hint", "Investigate and patch this issue."))
        say_to_engineer = (
            f"[{severity}] {title}. Scope: {where}. "
            f"Observed repeated behavior ({blocker.get('occurrences', 1)} occurrence(s)). "
            f"Please implement: {fix_hint}"
        )
        llm_prompt = (
            "You are helping debug a website issue.\n"
            f"Issue: {title}\n"
            f"Severity: {severity}\n"
            f"Where it appears: {where}\n"
            f"Why it matters: {why_it_matters}\n"
            f"Recommended fix direction: {fix_hint}\n"
            "Please provide: (1) likely root causes, (2) a step-by-step debugging checklist, "
            "(3) a concrete implementation patch strategy, and (4) regression tests."
        )
        items.append(
            {
                "rank": idx,
                "severity": severity,
                "issue": title,
                "what_happened": what_happened,
                "why_it_matters": why_it_matters,
                "recommended_fix_direction": fix_hint,
                "say_to_engineer": say_to_engineer,
                "prompt_for_llm": llm_prompt,
            }
        )

    if not items:
        items.append(
            {
                "rank": 1,
                "severity": "LOW",
                "issue": "No urgent issues",
                "what_happened": "No high-confidence blocker was found in this crawl scope.",
                "why_it_matters": "You can proceed, or run a wider crawl for more confidence.",
                "recommended_fix_direction": "Increase max pages/depth and rerun.",
                "say_to_engineer": "No urgent fix needed from this run.",
                "prompt_for_llm": "Suggest expanded test coverage for this website crawl.",
            }
        )

    intro = {
        "non-technical": "Plain-English summary for a website owner.",
        "engineer": "Plain-English handoff to engineering.",
        "llm": "Plain-English context prepared for an LLM assistant.",
    }.get(audience, "Plain-English summary.")

    return {
        "audience": audience,
        "intro": intro,
        "header": header,
        "items": items,
    }


def _plain_english_to_markdown(pack: dict[str, Any], report: dict[str, Any]) -> str:
    lines = [
        f"# Plain-English Fix Guide: {report.get('run_id', 'unknown')}",
        f"- URL: {report.get('start_url', 'n/a')}",
        f"- Audience: {pack.get('audience', 'non-technical')}",
        "",
        f"## Summary",
        f"- {pack.get('intro', '')}",
        f"- {pack.get('header', '')}",
        "",
        "## Priority Issues (Plain English)",
    ]
    for item in pack.get("items", []):
        lines.extend(
            [
                f"### {item.get('rank', '')}. [{item.get('severity', '')}] {item.get('issue', 'Issue')}",
                f"- What happened: {item.get('what_happened', '')}",
                f"- Why it matters: {item.get('why_it_matters', '')}",
                f"- Recommended fix direction: {item.get('recommended_fix_direction', '')}",
                f"- What to tell an engineer:",
                f"  - {item.get('say_to_engineer', '')}",
                f"- Prompt to paste into an LLM:",
                "```text",
                str(item.get("prompt_for_llm", "")),
                "```",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    in_list = False
    for raw in lines:
        line = raw.strip()
        if not line:
            if in_list:
                output.append("</ul>")
                in_list = False
            continue
        if line.startswith("### "):
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<h3>{html.escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<h2>{html.escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<h1>{html.escape(line[2:])}</h1>")
            continue
        if line.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if in_list:
            output.append("</ul>")
            in_list = False
        output.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        output.append("</ul>")
    return "\n".join(output)


@app.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    html_path = TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(), status_code=200)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs", response_model=CrawlResponse)
async def submit_job(request: CrawlRequest) -> CrawlResponse:
    job = await _create_job(request)
    return CrawlResponse(job_id=job.job_id, status=job.status)


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.get("/api/jobs/{job_id}/report")
async def get_report(job_id: str) -> dict[str, Any]:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.report_path:
        raise HTTPException(status_code=409, detail="Report not ready")
    return _load_report_payload(job.report_path)


@app.post("/api/jobs/{job_id}/plain-english")
async def plain_english_report(job_id: str, request: PlainEnglishRequest) -> dict[str, Any]:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.report_path:
        raise HTTPException(status_code=409, detail="Report not ready")
    report = _load_report_payload(job.report_path)
    return _build_plain_english_pack(report, audience=request.audience, max_items=request.max_items)


@app.get("/api/jobs/{job_id}/download/plain-english")
async def download_plain_english_markdown(job_id: str) -> FileResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.report_path:
        raise HTTPException(status_code=409, detail="Report not ready")
    report = _load_report_payload(job.report_path)
    pack = _build_plain_english_pack(report, audience="non-technical", max_items=5)
    out_path = Path(job.report_path).with_name(f"{job_id}-plain-english.md")
    out_path.write_text(_plain_english_to_markdown(pack, report))
    return FileResponse(path=out_path, filename=f"{job_id}-plain-english.md")


@app.get("/api/jobs")
async def list_jobs() -> list[dict[str, Any]]:
    jobs = sorted(_jobs.values(), key=lambda item: item.created_at, reverse=True)
    return [job.to_dict() for job in jobs]


@app.get("/api/jobs/{job_id}/download")
async def download_report(job_id: str) -> FileResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.report_path:
        raise HTTPException(status_code=404, detail="Report unavailable")
    report_path = Path(job.report_path)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file missing")
    return FileResponse(path=report_path, filename=f"{job_id}-report.json")


@app.get("/api/jobs/{job_id}/download/agentic-json")
async def download_agentic_json(job_id: str) -> FileResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.agentic_json_path:
        raise HTTPException(status_code=404, detail="Agentic JSON unavailable for this run")
    triage_path = Path(job.agentic_json_path)
    if not triage_path.exists():
        raise HTTPException(status_code=404, detail="Agentic JSON file missing")
    return FileResponse(path=triage_path, filename=f"{job_id}-agentic-output.json")


@app.get("/api/jobs/{job_id}/download/agentic-markdown")
async def download_agentic_markdown(job_id: str) -> FileResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.agentic_markdown_path:
        raise HTTPException(status_code=404, detail="Agentic markdown unavailable for this run")
    triage_path = Path(job.agentic_markdown_path)
    if not triage_path.exists():
        raise HTTPException(status_code=404, detail="Agentic markdown file missing")
    return FileResponse(path=triage_path, filename=f"{job_id}-agentic-output.md")


@app.get("/api/jobs/{job_id}/download/tickets/md")
async def download_ticket_markdown(job_id: str) -> FileResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.ticket_export_markdown_path:
        raise HTTPException(status_code=404, detail="Ticket markdown unavailable for this run")
    ticket_path = Path(job.ticket_export_markdown_path)
    if not ticket_path.exists():
        raise HTTPException(status_code=404, detail="Ticket markdown file missing")
    return FileResponse(path=ticket_path, filename=f"{job_id}-tickets.md")


@app.get("/api/jobs/{job_id}/download/tickets/csv")
async def download_ticket_csv(job_id: str) -> FileResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.ticket_export_csv_path:
        raise HTTPException(status_code=404, detail="Ticket CSV unavailable for this run")
    ticket_path = Path(job.ticket_export_csv_path)
    if not ticket_path.exists():
        raise HTTPException(status_code=404, detail="Ticket CSV file missing")
    return FileResponse(path=ticket_path, filename=f"{job_id}-tickets.csv")


@app.get("/api/jobs/{job_id}/download/tickets/github")
async def download_ticket_github_markdown(job_id: str) -> HTMLResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.report_path:
        raise HTTPException(status_code=404, detail="Report unavailable")
    payload = _load_report_payload(job.report_path)
    preview = _build_issue_payload_preview(job_id, payload)
    content = _build_github_issue_markdown(preview["issues"])
    return HTMLResponse(content=content, media_type="text/markdown")


@app.get("/api/jobs/{job_id}/download/tickets/linear")
async def download_ticket_linear_markdown(job_id: str) -> HTMLResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.report_path:
        raise HTTPException(status_code=404, detail="Report unavailable")
    payload = _load_report_payload(job.report_path)
    preview = _build_issue_payload_preview(job_id, payload)
    content = _build_linear_issue_markdown(preview["issues"])
    return HTMLResponse(content=content, media_type="text/markdown")


@app.get("/api/jobs/{job_id}/push-preview/{provider}")
async def ticket_push_preview(job_id: str, provider: str) -> dict[str, Any]:
    provider_name = provider.strip().lower()
    if provider_name not in {"github", "linear"}:
        raise HTTPException(status_code=400, detail="Provider must be github or linear")
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.report_path:
        raise HTTPException(status_code=404, detail="Report unavailable")
    payload = _load_report_payload(job.report_path)
    preview = _build_issue_payload_preview(job_id, payload)
    issues = preview["issues"]
    preview_text = (
        _build_github_issue_markdown(issues)
        if provider_name == "github"
        else _build_linear_issue_markdown(issues)
    )
    token = uuid.uuid4().hex[:12]
    _ticket_push_previews[(job_id, provider_name)] = TicketPushPreviewState(
        preview_token=token,
        job_id=job_id,
        provider=provider_name,
        target=provider_name,
        tickets=issues,
        metadata={"issues_count": len(issues)},
    )
    return {
        "preview_token": token,
        "provider": provider_name,
        "issues_count": len(issues),
        "preview": preview_text,
    }


@app.post("/api/jobs/{job_id}/push-confirm/{provider}")
async def ticket_push_confirm(job_id: str, provider: str) -> dict[str, Any]:
    provider_name = provider.strip().lower()
    if provider_name not in {"github", "linear"}:
        raise HTTPException(status_code=400, detail="Provider must be github or linear")
    preview = _ticket_push_previews.get((job_id, provider_name))
    if not preview:
        raise HTTPException(status_code=409, detail="No preview found; generate preview first")
    items_created = len(preview.tickets)
    return {
        "status": "ok",
        "provider": provider_name,
        "items_created": items_created,
        "simulated": True,
    }


@app.get("/share/{job_id}", response_class=HTMLResponse)
async def share_agentic_report(job_id: str) -> HTMLResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Job has not completed")
    if not job.agentic_markdown_path:
        raise HTTPException(status_code=404, detail="Agentic share report unavailable for this run")
    md_path = Path(job.agentic_markdown_path)
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="Agentic markdown file missing")
    markdown = md_path.read_text()
    rendered = _markdown_to_html(markdown)
    body = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Agentic Triage Report {html.escape(job_id)}</title>
    <style>
      body {{
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        background: #0b1220;
        color: #e5e7eb;
      }}
      .container {{
        max-width: 900px;
        margin: 0 auto;
        padding: 24px;
      }}
      .card {{
        background: #111827;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
      }}
      h1, h2, h3 {{ color: #f8fafc; }}
      p, li {{ line-height: 1.6; }}
      a {{ color: #93c5fd; }}
      .meta {{ color: #94a3b8; margin-bottom: 18px; }}
    </style>
  </head>
  <body>
    <main class="container">
      <section class="card">
        <div class="meta">
          Run: {html.escape(job_id)} | URL: {html.escape(job.url)} | Finished: {html.escape(job.finished_at or "n/a")}
        </div>
        {rendered}
        <hr />
        <p>
          <a href="/api/jobs/{html.escape(job_id)}/download">Download full report JSON</a> |
          <a href="/api/jobs/{html.escape(job_id)}/download/agentic-json">Download triage JSON</a> |
          <a href="/api/jobs/{html.escape(job_id)}/download/agentic-markdown">Download triage Markdown</a>
        </p>
      </section>
    </main>
  </body>
</html>"""
    return HTMLResponse(content=body, status_code=200)
