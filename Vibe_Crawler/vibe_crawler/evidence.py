from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Page


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_slug(value: str, *, max_len: int = 120) -> str:
    safe = "".join(char if char.isalnum() or char in "-_." else "_" for char in value)
    return safe[:max_len]


def screenshot_name_for_url(url: str, *, suffix: str = "") -> str:
    parsed = urlparse(url)
    base = f"{parsed.netloc}{parsed.path}".strip("/") or "homepage"
    base = sanitize_slug(base.replace("/", "_"))
    return f"{base}{suffix}.png"


async def take_page_screenshot(page: Page, destination: Path) -> str | None:
    try:
        await page.screenshot(path=str(destination), full_page=True)
        return str(destination)
    except Exception:
        return None
