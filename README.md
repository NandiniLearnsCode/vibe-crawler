# MVP Website QA Crawler (Deterministic)

Practical crawler agent for public websites that finds **high-confidence, obvious bugs** with screenshots and structured JSON output.

This version intentionally prioritizes:

- reliability over sophistication,
- deterministic checks over AI reasoning,
- bounded and safe crawling,
- fast implementation with modular detector architecture.

## What this MVP does

Given a starting URL, the crawler:

1. Crawls key internal pages with page/depth limits.
2. Runs deterministic bug detectors.
3. Captures screenshots.
4. Produces structured bug reports:
   - `id`
   - `type`
   - `severity`
   - `confidence`
   - `page_url`
   - `element_selector` (optional)
   - `short_title`
   - `description`
   - `reproduction_steps`
   - `screenshot_path`
   - `console_errors` (optional)
   - `network_evidence` (optional)

## Supported bug types (V1)

1. Broken internal links (`broken_link`)
2. Dead buttons/interactions (`dead_button`)
3. Basic form failures (`form_failure`)
4. Missing images/media (`missing_media`)
5. Mobile layout issues (`mobile_layout`)
6. Critical frontend runtime/asset errors (`critical_frontend_error`)

## Safety and crawl bounds

- Same-domain crawling by default.
- Configurable max pages and max depth.
- Per-page timeout.
- Dangerous/destructive paths skipped (`logout`, `payment`, `delete`, etc.).
- No login flows in this first version.

## Architecture

Detailed plan: [`Vibe_Crawler/docs/IMPLEMENTATION_PLAN.md`](Vibe_Crawler/docs/IMPLEMENTATION_PLAN.md)

Key runtime components:

- **Crawl Orchestrator**: overall job runner
- **URL Frontier**: prioritized deduplicated link queue
- **Browser Runner**: Playwright navigation + event collection
- **Detector Engine**: pluggable detector modules
- **Evidence Collector**: screenshot handling
- **Report Generator**: JSON + human summary output

## File structure

```text
Vibe_Crawler/
├── crawler.py                           # CLI entrypoint
├── agent.py                             # Backward-compatible entrypoint
├── requirements.txt
├── webapp/
│   ├── app.py                           # FastAPI backend + job runner
│   ├── static/
│   │   ├── app.css
│   │   └── app.js
│   └── templates/
│       └── index.html
├── docs/
│   └── IMPLEMENTATION_PLAN.md
├── examples/
│   ├── sample_config.json
│   └── example_report.json
└── vibe_crawler/
    ├── __init__.py
    ├── cli.py
    ├── config.py
    ├── evidence.py
    ├── frontier.py
    ├── models.py
    ├── orchestrator.py
    ├── reporting.py
    ├── url_utils.py
    └── detectors/
        ├── __init__.py
        ├── base.py
        ├── broken_links.py
        ├── console_errors.py
        ├── dead_buttons.py
        ├── forms.py
        ├── media.py
        └── mobile_layout.py
```

## Local setup

From repository root:

```bash
cd Vibe_Crawler
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

## Run a crawl

Basic run:

```bash
cd Vibe_Crawler
python crawler.py --url https://example.com
```

Use config file:

```bash
python crawler.py --config examples/sample_config.json
```

## Run web UI (URL submit + report viewer)

```bash
cd Vibe_Crawler
uvicorn webapp.app:app --reload
```

Then open `http://127.0.0.1:8000` in your browser.

What the UI does:
- submit crawl jobs with URL + limits
- poll job status
- render grouped bug findings by severity
- show screenshot path and evidence fields

## Deploy for sharing (recommended: Render)

Fastest way to get a public URL for advisors/professors is Render.

### One-click-ish setup with `render.yaml`

This repo now includes a Render blueprint at the repository root:
- `render.yaml`

It creates:
- a **Web Service** (FastAPI app),
- a persistent disk mounted at `/workspace/Vibe_Crawler/artifacts` (stores reports + screenshots).

### Deploy steps

1. Push your branch to GitHub.
2. In Render, choose **New +** -> **Blueprint**.
3. Connect this GitHub repo and select branch `cursor/mvp-deterministic-crawler-a9f6`.
4. Deploy.
5. Open the generated `onrender.com` URL and submit a crawl job.

### If you prefer manual Web Service setup

Use:
- Root Directory: `Vibe_Crawler`
- Build Command:  
  `pip install -r requirements.txt && python -m playwright install chromium`
- Start Command:  
  `./start.sh`
- Runtime: Python 3.12+

Add persistent disk:
- Mount Path: `/workspace/Vibe_Crawler/artifacts`
- Name: `vibe-artifacts`

### Notes for demos

- First crawl can be slower (cold start + browser startup).
- Keep crawl limits small for live demos (`max_pages=6`, `max_depth=2`).
- Reports are available in UI and via `/api/jobs/{job_id}/download`.

Useful flags:

```text
--url <url>
--config <path>
--max-pages <int>
--max-depth <int>
--timeout-ms <int>
--output <report-path>
--screenshots-dir <dir>
--no-mobile
--no-form-checks
--headed
--log-level DEBUG|INFO|WARNING|ERROR
```

## Sample crawl job

`examples/sample_config.json`:

```json
{
  "start_url": "https://example.com",
  "max_pages": 8,
  "max_depth": 2,
  "timeout_ms": 12000,
  "same_domain_only": true,
  "include_mobile_checks": true,
  "desktop_viewport": [1366, 900],
  "mobile_viewport": [390, 844],
  "screenshot_dir": "artifacts/screenshots",
  "output_path": "artifacts/reports/example-report.json",
  "dangerous_path_keywords": [
    "logout",
    "delete",
    "remove",
    "payment",
    "checkout",
    "billing",
    "admin/delete"
  ],
  "important_path_keywords": [
    "pricing",
    "signup",
    "login",
    "contact",
    "product",
    "docs",
    "about"
  ]
}
```

## Example output bug report

See [`Vibe_Crawler/examples/example_report.json`](Vibe_Crawler/examples/example_report.json).

## Small test plan

1. **Smoke run**
   - Run against `https://example.com`.
   - Verify report JSON is generated and no crashes occur.
2. **Broken-link fixture**
   - Run against a test site with known 404 internal links.
   - Verify `broken_link` findings and confidence scores.
3. **Dead button fixture**
   - Run against a page with a no-op CTA (`href="#"` and no handlers).
   - Verify `dead_button` detection.
4. **Mobile fixture**
   - Run against an intentionally overflowing mobile layout page.
   - Verify `mobile_layout` issues are flagged.
5. **Form fixture**
   - Run against a simple contact form with disabled submit / no feedback.
   - Verify `form_failure` detection.

## Next improvements (post-MVP)

1. Queue + worker execution model (Redis/SQS + worker process).
2. API layer for submitting jobs and fetching reports.
3. Stronger deduplication and bug clustering.
4. Lightweight web report viewer/dashboard.
5. Optional LLM summarization layer on top of deterministic evidence.
