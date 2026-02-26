# 🕷️ Vibe Crawler

An AI-powered agent that crawls websites and automatically surfaces bugs. Built with [Playwright](https://playwright.dev/python/) for browser automation and [Claude](https://anthropic.com) as the reasoning engine.

---

## What It Does

Vibe Crawler sends an AI agent to browse your website the way a QA engineer would. It navigates pages, clicks interactive elements, reads content, and uses judgment to decide what's worth investigating — then writes up everything it finds in plain English.

Unlike a simple linter or static checker, the agent *reasons* about what it sees. It can tell the difference between a button that looks broken and one that actually is, notice when placeholder text was never replaced, and follow leads across pages.

**What it detects:**

| Bug Type | Example |
|---|---|
| `js_error` | Uncaught TypeError thrown on page load |
| `broken_link` | Link returns 404 |
| `broken_form` | Form submits but nothing happens |
| `placeholder_text` | "Lorem ipsum" or "TODO" visible to users |
| `missing_resource` | Image or API call fails to load |
| `http_error` | Page returns 500 Internal Server Error |
| `dead_interaction` | Button has no click handler attached |
| `layout_issue` | Element overflows or renders incorrectly |

Each bug is reported with a **severity** (high / medium / low), the **URL** where it was found, and a plain English **description**.

---

## Architecture

The project has two layers:

### 1. `crawler.py` — The Browser Layer
A Playwright-based page walker. Given a URL, it:
- Navigates the page in a real Chromium browser
- Captures console errors and warnings
- Records failed network requests
- Collects all links for further crawling
- Optionally takes full-page screenshots
- Supports HTTP Basic Auth

This layer is deterministic — it always visits pages in BFS order and runs the same checks every time.

### 2. `agent.py` — The AI Layer
A Claude-powered agent that *drives* the crawler. Instead of visiting every page mechanically, Claude decides:
- Which pages are worth visiting
- Which elements are worth clicking
- When something looks suspicious enough to dig into
- When it has found everything there is to find

The agent runs a **ReAct loop** (Reasoning + Acting):
```
User: "Audit this website"
  ↓
Claude: thinks → calls navigate(url)
  ↓
Result: {status, console_errors, links}
  ↓
Claude: thinks → calls click_element(url, selector)
  ↓
Result: {errors triggered by click}
  ↓
Claude: thinks → calls report_bug(...)
  ↓
... continues until Claude calls done()
```

Claude has access to five tools:

| Tool | What it does |
|---|---|
| `navigate(url)` | Visit a page, get status + errors + links |
| `click_element(url, selector)` | Click something, observe what breaks |
| `get_page_text(url)` | Read page content, look for placeholder text |
| `report_bug(...)` | Log a confirmed bug |
| `done(summary)` | End the investigation, write the final report |

The agent stops when Claude determines there are no more leads to investigate and calls `done()`. A configurable `--max-steps` cap (default: 50 tool calls) acts as a safety limit.

---

## Setup

**Requirements:**
- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com)

**Install dependencies:**
```bash
pip install -r requirements.txt
playwright install chromium
```

**Set your API key:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

To make this permanent, add the line above to your `~/.zshrc` or `~/.bashrc`.

---

## Usage

**Basic audit:**
```bash
python agent.py --url https://your-site.com
```

**Watch Claude reason in real time:**
```bash
python agent.py --url https://your-site.com --verbose
```

**With HTTP Basic Auth:**
```bash
python agent.py --url https://your-site.com --username admin --password secret
```

**Save results to a JSON file:**
```bash
python agent.py --url https://your-site.com --output report.json
```

**Run the browser visibly (non-headless):**
```bash
python agent.py --url https://your-site.com --no-headless
```

**Limit the number of agent steps:**
```bash
python agent.py --url https://your-site.com --max-steps 20
```

**All options:**
```
--url           Root URL to audit (required)
--username      HTTP Basic Auth username
--password      HTTP Basic Auth password
--max-steps     Maximum tool calls before forced stop (default: 50)
--no-headless   Show the browser window while crawling
--verbose       Print Claude's reasoning between each tool call
--output        Save full bug report to a JSON file
```

---

## Example Output

```
🕷️  Starting vibe bug audit of https://example.com

============================================================
AUDIT COMPLETE
============================================================

The site has three issues worth fixing. The contact form on /contact
submits successfully but no confirmation message appears and no email
is sent — the form action points to a non-existent endpoint. The
/team page still contains Lorem Ipsum placeholder text in two staff
bios. The dashboard at /dashboard returns a 401 for logged-out users
but shows a blank white page instead of redirecting to login.

------------------------------------------------------------
BUGS FOUND: 3
------------------------------------------------------------

1. 🔴 [HIGH] broken_form
   URL: https://example.com/contact
   Form submits to /api/contact which returns 404. No user feedback shown.

2. 🟡 [MEDIUM] placeholder_text
   URL: https://example.com/team
   Two staff bios contain "Lorem ipsum dolor sit amet" placeholder text.

3. 🟡 [MEDIUM] http_error
   URL: https://example.com/dashboard
   Returns 401 with blank white page instead of redirecting to /login.
```

---

## Rate Limits

The agent uses `claude-haiku-4-5-20251001` by default, which has generous rate limits. If you want to use a more powerful model, change the `model` field in `agent.py`:

```python
model="claude-opus-4-6"  # More thorough reasoning, lower rate limits
```

Free-tier Anthropic accounts have a limit of 10,000 tokens per minute. For larger sites, consider upgrading at [console.anthropic.com](https://console.anthropic.com).

---

## Project Structure

```
vibe-crawler/
├── agent.py          # AI agent loop — Claude drives the investigation
├── crawler.py        # Playwright browser layer — executes tool calls
├── requirements.txt  # Python dependencies
└── README.md
```

---

## Roadmap

- [ ] Form interaction testing (fill and submit forms, not just click)
- [ ] Mobile layout checks (resize viewport, detect overflow)
- [ ] Visual regression via screenshot comparison
- [ ] HTML report output with annotated screenshots
- [ ] OAuth / cookie-based authentication support
- [ ] Parallel crawling for large sites
- [ ] CI/CD integration (run on every deploy)

---

## Built With

- [Playwright](https://playwright.dev/python/) — Browser automation
- [Anthropic Claude](https://anthropic.com) — AI reasoning engine
- Python 3.11+
