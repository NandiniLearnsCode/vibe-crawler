from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from vibe_crawler.agentic.planner import next_actions
from vibe_crawler.agentic.tools import AgentTools
from vibe_crawler.config import CrawlConfig
from vibe_crawler.models import BugReport, CrawlReport, PageRecord
from vibe_crawler.reporting import assign_bug_ids, deduplicate_bugs
from vibe_crawler.url_utils import is_http_url, is_same_domain, looks_dangerous, looks_like_html_page, normalize_url


@dataclass(slots=True)
class AgenticRunner:
    config: CrawlConfig
    headless: bool = True
    max_actions: int = 60

    async def run(self) -> CrawlReport:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        started_at = datetime.now(timezone.utc).isoformat()
        queue: deque[tuple[str, int]] = deque([(normalize_url(self.config.start_url), 0)])
        pages: list[PageRecord] = []
        findings: list[BugReport] = []
        trace: list[dict] = []

        visited_urls: set[str] = set()
        followups_done: set[tuple[str, str]] = set()
        actions_taken = 0

        async with AgentTools(config=self.config, run_id=run_id, headless=self.headless) as tools:
            while queue and len(pages) < self.config.max_pages:
                url, depth = queue.popleft()
                if url in visited_urls:
                    continue
                if not self._is_safe(url):
                    continue

                base_observation = await tools.base_scan(url=url, depth=depth)
                pages.append(base_observation.page)
                findings.extend(base_observation.bugs)
                trace.append(
                    {
                        "phase": base_observation.phase,
                        "url": base_observation.page.url,
                        "action": base_observation.action.action_type,
                        "reason": base_observation.action.reason,
                        "findings_count": len(base_observation.bugs),
                    }
                )

                if depth < self.config.max_depth:
                    for link in base_observation.page.discovered_links:
                        if self._is_safe(link):
                            queue.append((link, depth + 1))

                visited_urls.add(url)
                planned = next_actions(page=base_observation.page, base_findings=base_observation.bugs, max_actions=3)
                for action in planned:
                    if actions_taken >= self.max_actions:
                        break
                    if (url, action.action_type) in followups_done:
                        continue
                    followups_done.add((url, action.action_type))
                    actions_taken += 1
                    follow_up = await tools.follow_up_scan(
                        url=base_observation.page.url,
                        depth=depth,
                        action=action,
                    )
                    findings.extend(follow_up.bugs)
                    trace.append(
                        {
                            "phase": follow_up.phase,
                            "url": follow_up.page.url,
                            "action": follow_up.action.action_type,
                            "reason": follow_up.action.reason,
                            "findings_count": len(follow_up.bugs),
                        }
                    )

        deduped = deduplicate_bugs(findings)
        assign_bug_ids(run_id, deduped)

        report = CrawlReport(
            run_id=run_id,
            start_url=self.config.start_url,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            pages=pages,
            bugs=deduped,
            output_path=self.config.output_path,
            mode="agentic-triage",
            presentation_mode=self.config.presentation_mode,
            agent_trace=trace,
        )
        return report

    def _is_safe(self, url: str) -> bool:
        if not is_http_url(url):
            return False
        if self.config.same_domain_only and not is_same_domain(url, self.config.root_domain):
            return False
        if looks_dangerous(url, self.config.dangerous_path_keywords):
            return False
        if not looks_like_html_page(url):
            return False
        return True
