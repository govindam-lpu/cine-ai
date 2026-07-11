"""In-memory fixed-window rate limiter.

A public, no-auth app still needs an abuse throttle — but it's someone else's free tier (Groq's
daily cap, the Space's CPU) at risk now, so a lightweight in-process limiter is enough for v1. Not
shared across processes; the single free Space runs one worker, so that's fine.
"""

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        """Record a hit for `key`; return False if it exceeds the window budget."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            cutoff = now - self.window
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
