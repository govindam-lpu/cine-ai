"""Groq daily generation budget.

No paid inference means no surprise bill — the ceiling is Groq's free daily request cap
(~1,000/day ≈ 110 profiles). When it's spent, the product must degrade gracefully ("back
tomorrow") rather than error. Only meaningful when WRITER_BACKEND=groq; Ollama is unlimited, so the
budget never blocks locally.
"""

import threading
from datetime import date, datetime, timezone

from app.core.config import settings

# Groq free tier ~1,000 requests/day. Leave headroom below the hard cap.
DEFAULT_DAILY_LIMIT = 950


class GenerationBudget:
    def __init__(self, daily_limit: int = DEFAULT_DAILY_LIMIT) -> None:
        self.daily_limit = daily_limit
        self._count = 0
        self._day: date | None = None
        self._lock = threading.Lock()

    def _today(self) -> date:
        return datetime.now(timezone.utc).date()

    def _roll(self) -> None:
        today = self._today()
        if self._day != today:
            self._day = today
            self._count = 0

    @property
    def metered(self) -> bool:
        # Ollama (local dev) is free and unlimited — only meter Groq.
        return settings.writer_backend == "groq"

    def exhausted(self, need: int = 1) -> bool:
        if not self.metered:
            return False
        with self._lock:
            self._roll()
            return self._count + need > self.daily_limit

    def consume(self, n: int = 1) -> None:
        if not self.metered:
            return
        with self._lock:
            self._roll()
            self._count += n

    def remaining(self) -> int:
        with self._lock:
            self._roll()
            return max(0, self.daily_limit - self._count)

    def reset(self) -> None:
        with self._lock:
            self._count = 0
            self._day = self._today()


# Process-wide budget.
budget = GenerationBudget()
