"""Backward-compatible entrypoint for crawler CLI."""

from vibe_crawler.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
