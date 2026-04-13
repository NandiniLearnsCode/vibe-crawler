from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from vibe_crawler.agentic import AgenticRunner
from vibe_crawler.config import CrawlConfig
from vibe_crawler.orchestrator import CrawlOrchestrator
from vibe_crawler.reporting import human_summary, save_agentic_outputs, save_json_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic MVP website QA crawler.")
    parser.add_argument("--url", help="Starting URL to crawl")
    parser.add_argument("--config", help="Optional path to JSON config file")
    parser.add_argument("--max-pages", type=int, default=12, help="Maximum pages to crawl")
    parser.add_argument("--max-depth", type=int, default=2, help="Maximum crawl depth")
    parser.add_argument("--timeout-ms", type=int, default=20_000, help="Per-page timeout in milliseconds")
    parser.add_argument("--output", default="artifacts/report.json", help="Output report path")
    parser.add_argument("--screenshots-dir", default="artifacts/screenshots", help="Screenshot directory")
    parser.add_argument("--no-mobile", action="store_true", help="Disable mobile layout checks")
    parser.add_argument("--no-form-checks", action="store_true", help="Disable form testing")
    parser.add_argument("--headed", action="store_true", help="Show browser UI")
    parser.add_argument(
        "--mode",
        choices=("deterministic", "agentic"),
        default="deterministic",
        help="Execution mode: deterministic crawl or agentic triage",
    )
    parser.add_argument(
        "--max-actions",
        type=int,
        default=80,
        help="Agentic mode only: max follow-up actions",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING...)")
    return parser.parse_args()


def _config_from_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text())
    return raw if isinstance(raw, dict) else {}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _to_tuple2(value: Any, fallback: tuple[int, int]) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return fallback
    return fallback


def _to_tuple_str(value: Any, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        items = [str(item).strip() for item in value if str(item).strip()]
        if items:
            return tuple(items)
    return fallback


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def build_config(args: argparse.Namespace) -> CrawlConfig:
    json_cfg: dict[str, Any] = {}
    if args.config:
        json_cfg = _config_from_json(Path(args.config))

    start_url = args.url or json_cfg.get("start_url")
    if not start_url:
        raise ValueError("A starting URL is required via --url or config.start_url")
    if not urlparse(start_url).scheme:
        start_url = f"https://{start_url}"

    include_mobile_checks = _to_bool(_coalesce(json_cfg.get("include_mobile_checks"), not args.no_mobile))
    include_form_checks = _to_bool(_coalesce(json_cfg.get("include_form_checks"), not args.no_form_checks))
    same_domain_only = _to_bool(_coalesce(json_cfg.get("same_domain_only"), True))

    return CrawlConfig(
        start_url=start_url,
        max_pages=int(_coalesce(json_cfg.get("max_pages"), args.max_pages)),
        max_depth=int(_coalesce(json_cfg.get("max_depth"), args.max_depth)),
        timeout_ms=int(_coalesce(json_cfg.get("timeout_ms"), args.timeout_ms)),
        same_domain_only=same_domain_only,
        desktop_viewport=_to_tuple2(_coalesce(json_cfg.get("desktop_viewport")), (1366, 900)),
        mobile_viewport=_to_tuple2(_coalesce(json_cfg.get("mobile_viewport")), (390, 844)),
        screenshot_dir=Path(_coalesce(json_cfg.get("screenshot_dir"), args.screenshots_dir)),
        output_path=Path(_coalesce(json_cfg.get("output_path"), args.output)),
        include_mobile_checks=include_mobile_checks,
        include_form_checks=include_form_checks,
        dangerous_path_keywords=_to_tuple_str(
            _coalesce(json_cfg.get("dangerous_path_keywords")),
            CrawlConfig(start_url=start_url).dangerous_path_keywords,
        ),
        important_path_keywords=_to_tuple_str(
            _coalesce(json_cfg.get("important_path_keywords")),
            CrawlConfig(start_url=start_url).important_path_keywords,
        ),
    )


async def async_main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    config = build_config(args)
    if args.mode == "agentic":
        runner = AgenticRunner(config=config, max_actions=args.max_actions, headless=not args.headed)
        report = await runner.run()
    else:
        orchestrator = CrawlOrchestrator(config=config, headless=not args.headed)
        report = await orchestrator.run()

    save_json_report(report, config.output_path)
    triage_outputs = save_agentic_outputs(report, config.output_path)
    print(human_summary(report))
    print(f"\nJSON report saved to: {config.output_path}")
    if triage_outputs:
        print(f"Agentic triage JSON saved to: {triage_outputs[0]}")
        print(f"Agentic triage markdown saved to: {triage_outputs[1]}")
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
