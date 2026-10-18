"""Small in-memory rate limiter.

Deliberately dependency-free and process-local: the campaign app runs as a
single Railway instance, so a shared store would be more moving parts than the
abuse risk justifies. The goal is to stop one device burning OpenAI credit, not
to be a hardened gateway.
"""

import time
from collections import deque


class RateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def _prune(self, hits: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()

    def allow(self, key: str) -> bool:
        """Record a hit for `key` and return False once it exceeds the window budget."""
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        self._prune(hits, now)

        # Drop keys that have gone quiet so the dict can't grow without bound.
        if len(self._hits) > 2048:
            for stale_key in [k for k, v in self._hits.items() if not v and k != key]:
                del self._hits[stale_key]

        if len(hits) >= self.max_requests:
            return False

        hits.append(now)
        return True


def client_key(request) -> str:
    """Best-effort client identity. Railway sits behind a proxy, so trust XFF's first hop."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
