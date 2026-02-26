"""
agent.py — Claude-powered agent that drives the vibe bug crawler.

The agent decides which pages to investigate, what to look at next,
and when it's satisfied there's nothing more to find. It stops when
it determines there are no more leads worth pursuing.

Usage:
    python agent.py --url https://example.com
    python agent.py --url https://example.com --username admin --password secret
    python agent.py --url https://example.com --max-steps 30 --verbose
"""

import asyncio
import argparse
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import anthropic
from playwright.async_api import async_playwright, BrowserContext

from crawler import VibeCrawler, CrawledPage, PageFinding

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions — what Claude is allowed to do
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "navigate",
        "description": (
            "Navigate to a URL and return the page's HTTP status, console errors, "
            "failed network requests, and all links found on the page. "
            "Use this to visit a new page or re-visit one to dig deeper."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL to navigate to."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "click_element",
        "description": (
            "Click a CSS selector on the current page and return any console errors "
            "or network failures that result. Use this to test buttons, form submits, "
            "nav items, or anything interactive that might be broken."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The page URL to load first."},
                "selector": {"type": "string", "description": "CSS selector to click."},
            },
            "required": ["url", "selector"],
        },
    },
    {
        "name": "get_page_text",
        "description": (
            "Return the visible text content of a page. Use this to detect "
            "placeholder text (Lorem ipsum, TODO, FIXME, 'Coming soon', etc.), "
            "hardcoded dummy data, or missing content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The page URL to inspect."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "report_bug",
        "description": (
            "Record a confirmed bug. Call this whenever you've found something "
            "genuinely broken or suspicious. Be specific: include the URL, what "
            "you observed, and why it's a problem."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The page where the bug was found."},
                "kind": {
                    "type": "string",
                    "description": "Category of bug.",
                    "enum": [
                        "js_error",
                        "broken_link",
                        "broken_form",
                        "placeholder_text",
                        "missing_resource",
                        "http_error",
                        "dead_interaction",
                        "layout_issue",
                        "other",
                    ],
                },
                "description": {"type": "string", "description": "Clear description of the bug."},
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "How bad is this bug for users?",
                },
            },
            "required": ["url", "kind", "description", "severity"],
        },
    },
    {
        "name": "done",
        "description": (
            "Signal that you have finished the investigation. Call this when you've "
            "explored all promising leads and have nothing left to investigate. "
            "Provide a natural language summary of everything you found."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A clear, human-readable summary of all bugs found and the overall site health.",
                },
            },
            "required": ["summary"],
        },
    },
]


# ---------------------------------------------------------------------------
# Bug record
# ---------------------------------------------------------------------------

@dataclass
class Bug:
    url: str
    kind: str
    description: str
    severity: str
    found_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# Tool implementations — the actual Python functions Claude calls
# ---------------------------------------------------------------------------

class ToolExecutor:
    """Runs the tools Claude requests. Owns the Playwright browser context."""

    def __init__(self, context: BrowserContext, screenshot_dir: Path | None = None):
        self.context = context
        self.screenshot_dir = screenshot_dir
        self._current_url: str | None = None

    async def navigate(self, url: str) -> dict:
        page = await self.context.new_page()
        findings: list[dict] = []
        failed: list[str] = []

        page.on("console", lambda m: findings.append({
            "kind": "console_error" if m.type == "error" else "console_warning",
            "message": m.text,
        }) if m.type in ("error", "warning") else None)
        page.on("requestfailed", lambda r: failed.append(r.url))

        try:
            resp = await page.goto(url, wait_until="networkidle", timeout=30_000)
            await page.wait_for_timeout(500)
            status = resp.status if resp else None

            # Collect links
            hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = list(dict.fromkeys(
                h.split("#")[0].rstrip("/") for h in hrefs
                if h.startswith("http")
            ))

            for f in failed:
                findings.append({"kind": "failed_request", "message": f"Failed: {f}"})

            self._current_url = url
            return {
                "url": url,
                "status": status,
                "findings": findings,
                "links": links[:40],  # cap to avoid flooding context
            }
        except Exception as exc:
            return {"url": url, "status": None, "findings": [{"kind": "error", "message": str(exc)}], "links": []}
        finally:
            await page.close()

    async def click_element(self, url: str, selector: str) -> dict:
        page = await self.context.new_page()
        errors: list[str] = []
        failed: list[str] = []

        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("requestfailed", lambda r: failed.append(r.url))

        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            await page.wait_for_timeout(300)

            element = await page.query_selector(selector)
            if not element:
                return {"clicked": False, "reason": f"Selector not found: {selector}"}

            await element.click(timeout=5_000)
            await page.wait_for_timeout(1_000)

            return {
                "clicked": True,
                "selector": selector,
                "console_errors": errors,
                "failed_requests": failed,
            }
        except Exception as exc:
            return {"clicked": False, "reason": str(exc), "console_errors": errors}
        finally:
            await page.close()

    async def get_page_text(self, url: str) -> dict:
        page = await self.context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            text = await page.inner_text("body")
            # Truncate to avoid huge context payloads
            truncated = text[:4000] if len(text) > 4000 else text
            return {"url": url, "text": truncated, "truncated": len(text) > 4000}
        except Exception as exc:
            return {"url": url, "text": "", "error": str(exc)}
        finally:
            await page.close()


# ---------------------------------------------------------------------------
# The Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior QA engineer auditing a website for bugs.
Your job is to methodically investigate the site and find real problems that would affect users.

You have four investigation tools:
- navigate(url): visit a page, see its status, console errors, and links
- click_element(url, selector): interact with buttons/forms to see if they work
- get_page_text(url): read page content to spot placeholder text, TODOs, dummy data
- report_bug(...): record a confirmed bug with its URL, kind, severity, and description

Your workflow:
1. Start by navigating the root URL
2. Look at what came back — errors, links, suspicious patterns
3. Follow leads: if a page has JS errors, dig in; if there are forms, test them;
   if something looks like a dashboard or admin area, check it
4. Report bugs as you find them — don't wait until the end
5. Keep exploring until you've followed all reasonable leads
6. When there's genuinely nothing left to investigate, call done() with a summary

Be thorough but efficient. Don't re-visit pages you've already checked unless you
have a specific new thing to test. Focus on bugs that real users would hit.

Severity guide:
- high: site is broken for core functionality (can't sign in, pages 404, JS crashes on load)
- medium: feature is broken or confusing (form submits but nothing happens, broken images)
- low: cosmetic or minor (placeholder text visible, small layout glitch)
"""


class VibeAgent:
    def __init__(
        self,
        root_url: str,
        *,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        max_steps: int = 50,
        screenshot_dir: str | Path | None = None,
        headless: bool = True,
        verbose: bool = False,
    ):
        self.root_url = root_url
        self.username = username
        self.password = password
        self.max_steps = max_steps
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else None
        self.headless = headless
        self.verbose = verbose

        self.client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.bugs: list[Bug] = []
        self.steps: int = 0

    async def run(self) -> tuple[list[Bug], str]:
        """
        Run the agent. Returns (bugs_found, summary_text).
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            kwargs: dict = {
                "viewport": {"width": 1280, "height": 800},
                "ignore_https_errors": True,
            }
            if self.username and self.password:
                kwargs["http_credentials"] = {
                    "username": self.username,
                    "password": self.password,
                }
            context = await browser.new_context(**kwargs)
            executor = ToolExecutor(context, self.screenshot_dir)

            try:
                summary = await self._loop(executor)
            finally:
                await context.close()
                await browser.close()

        return self.bugs, summary

    async def _loop(self, executor: ToolExecutor) -> str:
        """Core ReAct loop: think → act → observe → repeat."""
        history: list[dict] = [
            {"role": "user", "content": f"Please audit this website for bugs: {self.root_url}"}
        ]

        while self.steps < self.max_steps:
            self.steps += 1
            log.info(f"[step {self.steps}/{self.max_steps}] Calling Claude...")

            response = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=history,
            )

            # Append Claude's response to history
            history.append({"role": "assistant", "content": response.content})

            if self.verbose:
                for block in response.content:
                    if hasattr(block, "text"):
                        log.info(f"Claude: {block.text}")

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Claude finished without calling done() — extract any text
                texts = [b.text for b in response.content if hasattr(b, "text")]
                return "\n".join(texts) or "Agent finished without producing a summary."

            if response.stop_reason != "tool_use":
                return f"Unexpected stop reason: {response.stop_reason}"

            # Dispatch all tool calls in this response
            tool_results = []
            finished = False
            final_summary = ""

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                log.info(f"  → tool: {tool_name}({json.dumps(tool_input, ensure_ascii=False)[:120]})")

                # Execute the tool
                result, done_signal, summary_text = await self._dispatch(
                    executor, tool_name, tool_input
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

                if done_signal:
                    finished = True
                    final_summary = summary_text

            # Feed all results back in one user turn
            history.append({"role": "user", "content": tool_results})

            if finished:
                return final_summary

        return f"Reached step limit ({self.max_steps}). Bugs found so far: {len(self.bugs)}"

    async def _dispatch(
        self, executor: ToolExecutor, name: str, inputs: dict
    ) -> tuple[dict, bool, str]:
        """
        Execute a tool call. Returns (result_dict, is_done, summary_if_done).
        """
        if name == "navigate":
            result = await executor.navigate(inputs["url"])
            return result, False, ""

        elif name == "click_element":
            result = await executor.click_element(inputs["url"], inputs["selector"])
            return result, False, ""

        elif name == "get_page_text":
            result = await executor.get_page_text(inputs["url"])
            return result, False, ""

        elif name == "report_bug":
            bug = Bug(
                url=inputs["url"],
                kind=inputs["kind"],
                description=inputs["description"],
                severity=inputs["severity"],
            )
            self.bugs.append(bug)
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(bug.severity, "⚪")
            log.info(f"  {severity_icon} BUG [{bug.severity}] {bug.kind}: {bug.description[:80]}")
            return {"recorded": True, "total_bugs": len(self.bugs)}, False, ""

        elif name == "done":
            return {"acknowledged": True}, True, inputs["summary"]

        else:
            return {"error": f"Unknown tool: {name}"}, False, ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="AI agent that finds bugs in vibe-coded websites.")
    parser.add_argument("--url", required=True, help="Root URL to audit")
    parser.add_argument("--username", help="HTTP Basic Auth username")
    parser.add_argument("--password", help="HTTP Basic Auth password")
    parser.add_argument("--max-steps", type=int, default=50, help="Max agent steps (safety cap)")
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="Print Claude's reasoning")
    parser.add_argument("--output", help="Save bug report to JSON file")
    args = parser.parse_args()

    agent = VibeAgent(
        root_url=args.url,
        username=args.username,
        password=args.password,
        max_steps=args.max_steps,
        headless=not args.no_headless,
        verbose=args.verbose,
    )

    print(f"\n🕷️  Starting vibe bug audit of {args.url}\n")
    bugs, summary = await agent.run()

    # Print summary
    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)
    print(f"\n{summary}\n")

    if bugs:
        print(f"{'─' * 60}")
        print(f"BUGS FOUND: {len(bugs)}")
        print(f"{'─' * 60}")
        for i, bug in enumerate(bugs, 1):
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(bug.severity, "⚪")
            print(f"\n{i}. {icon} [{bug.severity.upper()}] {bug.kind}")
            print(f"   URL: {bug.url}")
            print(f"   {bug.description}")
    else:
        print("✅ No bugs found.")

    # Optionally save JSON
    if args.output:
        report = {
            "url": args.url,
            "audited_at": datetime.utcnow().isoformat(),
            "summary": summary,
            "bugs": [
                {
                    "url": b.url,
                    "kind": b.kind,
                    "severity": b.severity,
                    "description": b.description,
                    "found_at": b.found_at,
                }
                for b in bugs
            ],
        }
        Path(args.output).write_text(json.dumps(report, indent=2))
        log.info(f"Report saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
