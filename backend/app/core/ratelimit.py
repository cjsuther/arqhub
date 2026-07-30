"""In-memory fixed-window rate limiter (SPEC §9 rate limiting, §12 hardening).

Per-key (token or client IP) fixed window. Single-process only; a multi-replica
deploy would back this with Redis. The clock is injectable for tests.
"""

from __future__ import annotations

import time
from collections.abc import Callable


class RateLimiter:
    def __init__(self, limit: int, window: float = 60.0, clock: Callable[[], float] = time.time) -> None:
        self.limit = limit
        self.window = window
        self.clock = clock
        self._buckets: dict[str, tuple[float, int]] = {}

    def check(self, key: str) -> bool:
        """Record a hit for ``key``; return True if within the limit."""
        now = self.clock()
        start, count = self._buckets.get(key, (now, 0))
        if now - start >= self.window:
            start, count = now, 0
        count += 1
        self._buckets[key] = (start, count)
        return count <= self.limit
