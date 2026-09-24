from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class InMemoryRateLimiter:
    """Thread-safe fixed-window limiter for the current single-process deployment."""

    def __init__(self, window_seconds: float = 60.0):
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int) -> tuple[bool, int]:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._events[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                retry_after = max(1, int(timestamps[0] + self.window_seconds - now + 0.999))
                return False, retry_after
            timestamps.append(now)
            if len(self._events) > 10_000:
                self._cleanup_locked(cutoff)
            return True, 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def _cleanup_locked(self, cutoff: float) -> None:
        expired = [key for key, timestamps in self._events.items() if not timestamps or timestamps[-1] <= cutoff]
        for key in expired:
            self._events.pop(key, None)
