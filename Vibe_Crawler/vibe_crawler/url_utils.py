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
    host = canonical_domain(parsed.netloc)
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{host}{port}" if host else parsed.netloc.lower()
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=netloc,
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


def canonical_domain(host_or_netloc: str) -> str:
    host = (host_or_netloc or "").strip().lower()
    if "@" in host:
        host = host.split("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def normalized_host(url_or_host: str) -> str:
    parsed = urlparse(url_or_host)
    if parsed.scheme and parsed.netloc:
        return canonical_domain(parsed.netloc)
    return canonical_domain(url_or_host)


def hosts_match(url_or_host: str, root_domain: str) -> bool:
    return normalized_host(url_or_host) == canonical_domain(root_domain)


def is_same_domain(url: str, root_domain: str) -> bool:
    return hosts_match(url, root_domain)


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
