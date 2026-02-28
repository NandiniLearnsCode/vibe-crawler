## Cursor Cloud specific instructions

### Overview

Vibe Crawler is a Python CLI tool with two entry points:

- `Vibe_Crawler/crawler.py` — standalone Playwright-based BFS web crawler (no API key needed)
- `Vibe_Crawler/agent.py` — Claude-powered AI agent that drives the crawler (requires `ANTHROPIC_API_KEY`)

See `README.md` for full usage and CLI flags.

### Running the application

Both scripts are run from the `Vibe_Crawler/` directory with `python3`:

```
cd Vibe_Crawler
python3 crawler.py --url https://example.com
python3 agent.py --url https://example.com   # requires ANTHROPIC_API_KEY
```

Use `python3` (not `python`) — this environment does not alias `python` to `python3`.

### Environment notes

- `~/.local/bin` must be on `PATH` for the `playwright` CLI (already added to `~/.bashrc`).
- Chromium is installed via `playwright install --with-deps chromium` during setup. If Playwright is upgraded, re-run this command.
- There are no automated tests, linter configs, or build steps in this repo. Validation is done by running the CLI tools directly.
- `agent.py` requires the `ANTHROPIC_API_KEY` secret to be set. Without it, only `crawler.py` can be tested.
