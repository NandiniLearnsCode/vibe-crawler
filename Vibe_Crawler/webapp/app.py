from __future__ import annotations

import asyncio
import html
import json
import logging
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
from vibe_crawler.reporting import human_summary, save_agentic_outputs, save_json_report

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
            "agentic_json_path": self.agentic_json_path,
            "agentic_markdown_path": self.agentic_markdown_path,
            "summary": self.summary,
            "pages_crawled": self.pages_crawled,
            "bugs_found": self.bugs_found,
        }


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
        triage_outputs = save_agentic_outputs(report, report_path, presentation_mode=config.presentation_mode)

        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc).isoformat()
        job.report_path = str(report_path)
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
