from vibe_crawler.detectors.broken_links import BrokenLinksDetector
from vibe_crawler.detectors.console_errors import ConsoleErrorsDetector
from vibe_crawler.detectors.dead_buttons import DeadButtonsDetector
from vibe_crawler.detectors.forms import FormsDetector
from vibe_crawler.detectors.media import MediaDetector
from vibe_crawler.detectors.mobile_layout import MobileLayoutDetector

__all__ = [
    "BrokenLinksDetector",
    "ConsoleErrorsDetector",
    "DeadButtonsDetector",
    "FormsDetector",
    "MediaDetector",
    "MobileLayoutDetector",
]
