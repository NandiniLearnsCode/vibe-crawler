# 🐛 Vibe Crawler

An agent that crawls vibe-coded websites to automatically find bugs — broken links, JS errors, layout overflow, accessibility issues, missing meta tags, dead clicks, mobile responsiveness problems, and more.

## Quick Start

```bash
pip install -r requirements.txt
playwright install chromium

# Crawl a site
python crawler.py https://my-vibe-site.vercel.app

# With options
python crawler.py https://my-vibe-site.vercel.app --max-pages 30 --output bugs.json --format both
```

This produces a terminal summary, a `report.json` file, and a `report.html` with filtering and sorting.

## What It Detects

| Detector | What it finds | Severity |
|---|---|---|
| **ConsoleErrorDetector** | JS `console.error` calls and unhandled exceptions | HIGH / MEDIUM |
| **BrokenLinkDetector** | Links returning 4xx/5xx status codes | MEDIUM / HIGH |
| **OverflowDetector** | Elements with horizontal overflow | MEDIUM |
| **AccessibilityDetector** | Missing alt text, unlabeled inputs, no lang attr | MEDIUM / LOW |
| **MetaAndSEODetector** | Missing title, viewport, description, favicon, h1 issues | MEDIUM / LOW |
| **DeadClickDetector** | Elements that look clickable but aren't interactive | LOW |
| **MobileResponsivenessDetector** | Viewport overflow, small tap targets, tiny text | MEDIUM / LOW |

## CLI Options

```
python crawler.py URL [OPTIONS]

Arguments:
  URL                   Starting URL to crawl

Options:
  --max-pages INT       Max pages to visit (default: 20)
  --output PATH         Output report path (default: report.json)
  --format FORMAT       json, html, or both (default: both)
  --headed              Run browser visibly instead of headless
```

## Using as a Library

```python
import asyncio
from crawler import VibeCrawler
from reporter import print_report, generate_json_report, generate_html_report

async def scan():
    crawler = VibeCrawler(
        start_url="https://my-site.com",
        max_pages=10,
    )
    result = await crawler.run()
    print_report(result)
    generate_json_report(result, "report.json")
    generate_html_report(result, "report.html")

asyncio.run(scan())
```

## Writing Custom Detectors

Create a new file in `detectors/` and subclass `BugDetector`:

```python
# detectors/slow_pages.py
from detectors.base import BugDetector, Bug, Severity

class SlowPageDetector(BugDetector):
    name = "slow_pages"

    async def detect(self, page, url):
        timing = await page.evaluate(
            "() => performance.timing.loadEventEnd - performance.timing.navigationStart"
        )
        if timing > 3000:
            return [Bug(
                url=url,
                category="performance",
                severity=Severity.MEDIUM,
                title=f"Slow page load ({timing}ms)",
                description=f"Page took {timing}ms to fully load.",
            )]
        return []
```

Then register it in `detectors/__init__.py` and add it to `DEFAULT_DETECTORS` in `crawler.py`.

## GitHub Actions

The included workflow (`.github/workflows/crawl.yml`) lets you:

- **Run manually** from the Actions tab with a URL input
- **Run on a schedule** (weekly by default) against a `DEFAULT_TARGET_URL` repo variable

Reports are uploaded as artifacts you can download from the Actions run.

### Setup

1. Go to **Settings → Variables → Actions** in your repo
2. Add a variable called `DEFAULT_TARGET_URL` with your target site URL

## Project Structure

```
vibe-crawler/
├── .github/workflows/crawl.yml   # CI/CD automation
├── detectors/
│   ├── __init__.py                # Exports all detectors
│   ├── base.py                    # Bug, Severity, BugDetector base class
│   ├── console_errors.py          # JS error detection
│   ├── broken_links.py            # Dead link checking
│   ├── overflow.py                # Layout overflow detection
│   ├── accessibility.py           # A11y issue detection
│   ├── meta_seo.py                # Meta tag / SEO checks
│   ├── dead_clicks.py             # Fake button detection
│   └── mobile.py                  # Mobile responsiveness checks
├── crawler.py                     # Main crawler engine + CLI
├── reporter.py                    # Terminal, JSON, HTML reporters
├── requirements.txt
└── README.md
```

## Future Ideas

- **LLM visual bug detection** — screenshot pages and send to a vision model
- **Form fuzzer** — auto-fill forms with edge-case inputs
- **Lighthouse integration** — pull Core Web Vitals scores
- **Diff mode** — compare two crawls to find regressions
- **GitHub Issues integration** — auto-create issues for high-severity bugs
