# MVP Website QA Crawler - Implementation Plan

## 1) MVP scope

Build a bounded crawler for public websites that:

- starts from one URL,
- crawls internal pages with page/depth limits,
- runs deterministic high-confidence bug detectors,
- captures screenshots,
- emits structured JSON bug reports plus a human summary.

In-scope bug classes for this MVP:

1. broken internal links,
2. dead buttons,
3. basic form failures,
4. missing/broken media,
5. mobile layout issues,
6. critical frontend runtime/asset errors.

Out of scope for now:

- authenticated flows,
- destructive actions (payments/deletes),
- advanced AI reasoning and speculative bug finding,
- external link checking as a primary signal.

## 2) Architecture

System is split into small modules:

- **Crawl Orchestrator**: controls run lifecycle, browser contexts, crawl loop.
- **URL Frontier Manager**: deduplicated prioritized queue with depth tracking.
- **Browser Runner**: page navigation, event listeners, screenshots, link extraction.
- **Detector Engine**: pluggable detector modules with a shared context interface.
- **Evidence Collector**: screenshot naming and artifact persistence.
- **Report Generator**: de-duplication, confidence/severity output, JSON + summary.

## 3) Core components

- `vibe_crawler/config.py`: crawl settings and safety knobs.
- `vibe_crawler/frontier.py`: deterministic URL queue.
- `vibe_crawler/orchestrator.py`: crawler control plane.
- `vibe_crawler/detectors/*`: modular bug detectors.
- `vibe_crawler/models.py`: typed bug/page/report data models.
- `vibe_crawler/reporting.py`: output formatting.
- `vibe_crawler/cli.py`: job runner CLI.

## 4) Recommended tech stack

- **Python 3.11+**: fast to implement, easy ops, strong Playwright support.
- **Playwright (Chromium)**: deterministic browser automation + screenshots.
- **JSON artifacts**: easy to consume now, can feed a UI later.
- **Simple job execution via CLI**: easiest first version; API/queue is deferred.

## 5) Bug report data model

Each bug includes:

- `id`
- `type`
- `severity`
- `confidence`
- `page_url`
- `element_selector` (optional)
- `short_title`
- `description`
- `reproduction_steps`
- `screenshot_path` (optional)
- `console_errors` (optional)
- `network_evidence` (optional)
- `detector` (source detector name)

## 6) Crawl strategy

- Normalize URLs (remove query/fragment).
- Stay in-domain by default.
- Prioritize important pages with path hints: pricing/signup/login/contact/docs/about.
- Ignore dangerous or irrelevant paths and non-HTML assets.
- Enforce max pages, depth, and per-page timeout.
- Use separate desktop + mobile contexts.

## 7) Detection strategy by bug type

1. **Broken links**
   - request internal links from crawled pages,
   - flag 4xx/5xx responses with high confidence,
   - flag obvious error-page body signatures with medium confidence.
2. **Dead buttons**
   - test visible action-like buttons/anchors,
   - require no URL change, no request activity, no modal/state mutation.
3. **Basic form failures**
   - only test simple non-auth/non-payment forms,
   - flag missing/disabled submit, no validation feedback, silent submit failures.
4. **Missing media**
   - detect broken `<img>` state and failing image/media requests.
5. **Mobile layout issues**
   - detect horizontal overflow, off-screen controls, and clipped text at mobile viewport.
6. **Critical frontend errors**
   - detect uncaught runtime console/page errors and failed internal JS/CSS loads.

## 8) Mocked or deferred items

- No queue broker yet (single-process job runner).
- No DB persistence yet (file artifacts only).
- No LLM reasoner layer yet.
- No auth/session replay yet.
- No dashboard UI yet.

## 9) Biggest engineering risks

- False positives from ambiguous UI interactions.
- Flaky behavior from highly dynamic SPAs.
- Form safety in the wild (must keep strict skip rules).
- Crawl performance vs. detector depth tradeoffs.

Risk mitigation:

- conservative detector thresholds,
- bounded crawl limits,
- strict safety filters for actions,
- confidence scoring and de-duplication.

## 10) Phased delivery plan

### Phase 1
- homepage + prioritized internal crawling,
- broken link detection,
- dead button detection,
- screenshots,
- JSON reports.

### Phase 2
- form checks,
- console critical error detection,
- mobile layout checks.

### Phase 3
- stronger prioritization and dedupe,
- queue/API worker split,
- lightweight dashboard/report viewer.
