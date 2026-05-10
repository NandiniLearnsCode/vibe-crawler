from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from vibe_crawler.url_utils import canonical_domain


DEFAULT_DANGEROUS_PATH_KEYWORDS = (
    "logout",
    "delete",
    "remove",
    "payment",
    "checkout",
    "billing",
    "unsubscribe",
    "cancel",
    "admin/reset",
)

DEFAULT_IMPORTANT_PATH_KEYWORDS = (
    "pricing",
    "signup",
    "sign-up",
    "login",
    "contact",
    "product",
    "docs",
    "about",
)


@dataclass(slots=True)
class CrawlConfig:
    start_url: str
    max_pages: int = 12
    max_depth: int = 2
    timeout_ms: int = 20_000
    same_domain_only: bool = True
    desktop_viewport: tuple[int, int] = (1366, 900)
    mobile_viewport: tuple[int, int] = (390, 844)
    max_links_per_page: int = 30
    max_buttons_per_page: int = 6
    max_forms_per_page: int = 2
    screenshot_dir: Path = Path("artifacts/screenshots")
    output_path: Path = Path("artifacts/report.json")
    include_mobile_checks: bool = True
    include_form_checks: bool = True
    presentation_mode: str = "founder"
    dangerous_path_keywords: tuple[str, ...] = field(default_factory=lambda: DEFAULT_DANGEROUS_PATH_KEYWORDS)
    important_path_keywords: tuple[str, ...] = field(default_factory=lambda: DEFAULT_IMPORTANT_PATH_KEYWORDS)

    @property
    def root_domain(self) -> str:
        return canonical_domain(urlparse(self.start_url).netloc)

    @property
    def allowed_domains(self) -> tuple[str, ...]:
        root = self.root_domain
        if not root:
            return tuple()
        return (root,)
