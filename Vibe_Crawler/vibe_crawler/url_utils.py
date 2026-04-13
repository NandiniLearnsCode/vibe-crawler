from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse

PRIORITY_PATH_HINTS = (
    "pricing",
    "signup",
    "sign-up",
    "login",
    "contact",
    "product",
    "docs",
    "about",
)

UNSAFE_FILE_SUFFIXES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".mp4",
    ".mov",
    ".avi",
    ".css",
    ".js",
    ".xml",
)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        query="",
        fragment="",
        path=path.rstrip("/") or "/",
    )
    return urlunparse(normalized)


def to_absolute(base_url: str, candidate: str) -> str:
    return normalize_url(urljoin(base_url, candidate.strip()))


def is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_same_domain(url: str, root_domain: str) -> bool:
    return urlparse(url).netloc.lower() == root_domain.lower()


def looks_dangerous(url: str, blocked_keywords: tuple[str, ...]) -> bool:
    lowered = url.lower()
    return any(keyword in lowered for keyword in blocked_keywords)


def looks_like_html_page(url: str) -> bool:
    lowered = url.lower()
    return not lowered.endswith(UNSAFE_FILE_SUFFIXES)


def path_priority_score(url: str, hints: tuple[str, ...] = PRIORITY_PATH_HINTS) -> int:
    lowered = url.lower()
    for index, keyword in enumerate(hints):
        if keyword in lowered:
            return 100 - index * 10
    if lowered.endswith("/"):
        return 80
    return 50
