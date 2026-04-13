from __future__ import annotations

import asyncio
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

from vibe_crawler.config import CrawlConfig
from vibe_crawler.orchestrator import CrawlOrchestrator
from vibe_crawler.reporting import human_summary, save_json_report

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
            screenshot_dir=screenshot_dir,
            output_path=report_path,
        )
        orchestrator = CrawlOrchestrator(config=config, headless=True)
        report = await orchestrator.run()
        save_json_report(report, report_path)

        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc).isoformat()
        job.report_path = str(report_path)
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
