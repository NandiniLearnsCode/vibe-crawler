from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush

from vibe_crawler.url_utils import path_priority_score


@dataclass(order=True, slots=True)
class FrontierItem:
    sort_index: tuple[int, int, int] = field(init=False)
    priority: int
    depth: int
    insertion_order: int
    url: str = field(compare=False)

    def __post_init__(self) -> None:
        self.sort_index = (-self.priority, self.depth, self.insertion_order)


class UrlFrontier:
    def __init__(self, *, important_path_keywords: tuple[str, ...] | None = None) -> None:
        self._queue: list[FrontierItem] = []
        self._seen: set[str] = set()
        self._counter = 0
        self._important_path_keywords = important_path_keywords

    def push(self, url: str, depth: int) -> bool:
        if url in self._seen:
            return False
        self._seen.add(url)
        priority = path_priority_score(url, self._important_path_keywords)
        self._counter += 1
        heappush(
            self._queue,
            FrontierItem(
                priority=priority,
                depth=depth,
                insertion_order=self._counter,
                url=url,
            ),
        )
        return True

    def pop(self) -> tuple[str, int] | None:
        if not self._queue:
            return None
        item = heappop(self._queue)
        return item.url, item.depth

    def __len__(self) -> int:
        return len(self._queue)
