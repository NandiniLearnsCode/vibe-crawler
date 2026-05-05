from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from vibe_crawler.config import CrawlConfig
from vibe_crawler.detectors import (
    BrokenLinksDetector,
    ConsoleErrorsDetector,
    DeadButtonsDetector,
    FormsDetector,
    MobileLayoutDetector,
)
from vibe_crawler.models import BugReport, PageRecord
from vibe_crawler.orchestrator import CrawlOrchestrator

ActionType = Literal["forms", "mobile", "dead_buttons", "broken_links", "console"]


@dataclass(slots=True)
class AgentAction:
    action_type: ActionType
    reason: str


@dataclass(slots=True)
class AgentContext:
    visited_urls: set[str] = field(default_factory=set)
    actions_taken: int = 0
    pages: list[PageRecord] = field(default_factory=list)
    bugs: list[BugReport] = field(default_factory=list)
    followup_counts: dict[str, int] = field(default_factory=dict)
    mobile_rechecks_done: dict[str, bool] = field(default_factory=dict)
    dead_button_rechecks_done: dict[str, bool] = field(default_factory=dict)
    form_rechecks_done: dict[str, bool] = field(default_factory=dict)

    def record_observation(self, observation: "ToolObservation") -> None:
        if observation.phase == "base_scan":
            self.visited_urls.add(observation.page.url)
            self.pages.append(observation.page)
        self.bugs.extend(observation.bugs)
        if observation.phase == "follow_up":
            page_url = observation.page.url
            self.actions_taken += 1
            self.followup_counts[page_url] = self.followup_counts.get(page_url, 0) + 1
            if observation.action.action_type == "mobile":
                self.mobile_rechecks_done[page_url] = True
            elif observation.action.action_type == "dead_buttons":
                self.dead_button_rechecks_done[page_url] = True
            elif observation.action.action_type == "forms":
                self.form_rechecks_done[page_url] = True


@dataclass(slots=True)
class ToolObservation:
    page: PageRecord
    bugs: list[BugReport]
    action: AgentAction
    phase: Literal["base_scan", "follow_up"]


class AgentTools:
    def __init__(self, *, config: CrawlConfig, run_id: str, headless: bool) -> None:
        self.orchestrator = CrawlOrchestrator(config=config, headless=headless)
        self.run_id = run_id

    async def __aenter__(self) -> "AgentTools":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def base_scan(self, *, url: str, depth: int) -> ToolObservation:
        page, bugs = await self.orchestrator.run_single_page(
            url=url,
            depth=depth,
            mobile=False,
        )
        return ToolObservation(
            page=page,
            bugs=bugs,
            action=AgentAction(action_type="broken_links", reason="baseline deterministic scan"),
            phase="base_scan",
        )

    async def follow_up_scan(
        self,
        *,
        url: str,
        depth: int,
        action: AgentAction,
    ) -> ToolObservation:
        if action.action_type == "forms":
            page, bugs = await self.orchestrator.run_single_page(
                url=url,
                depth=depth,
                mobile=False,
                detectors=[FormsDetector()],
            )
        elif action.action_type == "dead_buttons":
            page, bugs = await self.orchestrator.run_single_page(
                url=url,
                depth=depth,
                mobile=False,
                detectors=[DeadButtonsDetector()],
            )
        elif action.action_type == "console":
            page, bugs = await self.orchestrator.run_single_page(
                url=url,
                depth=depth,
                mobile=False,
                detectors=[ConsoleErrorsDetector()],
            )
        elif action.action_type == "mobile":
            page, bugs = await self.orchestrator.run_single_page(
                url=url,
                depth=depth,
                mobile=True,
                detectors=[MobileLayoutDetector()],
            )
        elif action.action_type == "broken_links":
            page, bugs = await self.orchestrator.run_single_page(
                url=url,
                depth=depth,
                mobile=False,
                detectors=[BrokenLinksDetector()],
            )
        else:
            page, bugs = await self.orchestrator.run_single_page(url=url, depth=depth, mobile=False)

        return ToolObservation(page=page, bugs=bugs, action=action, phase="follow_up")

    def suspicion_score(self, page_url: str, page_bugs: list[BugReport]) -> int:
        score = 0
        lowered = page_url.lower()
        if any(token in lowered for token in ("signup", "sign-up", "contact", "pricing", "product", "trial", "demo")):
            score += 1
        if any(bug.severity == "high" for bug in page_bugs):
            score += 2
        if any(bug.type in {"critical_frontend_error", "form_failure", "dead_button"} for bug in page_bugs):
            score += 1
        return score

