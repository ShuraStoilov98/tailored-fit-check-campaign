"""Small in-memory rate limiter.

Deliberately dependency-free and process-local: the campaign app runs as a
single Railway instance, so a shared store would be more moving parts than the
abuse risk justifies. The goal is to stop one device burning OpenAI credit, not
to be a hardened gateway.
"""

import time
from collections import deque
from ipaddress import ip_address


class RateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int, max_clients: int = 4096) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._hits: dict[str, deque[float]] = {}
        self._last_cleanup = time.monotonic()

    def _prune(self, hits: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()

    def allow(self, key: str) -> bool:
        """Record a hit for `key` and return False once it exceeds the window budget."""
        now = time.monotonic()
        if now - self._last_cleanup >= self.window_seconds:
            for stale_key, hits in list(self._hits.items()):
                self._prune(hits, now)
                if not hits:
                    del self._hits[stale_key]
            self._last_cleanup = now

        if key not in self._hits:
            # Do not evict active clients: doing so would reset their budgets.
            if len(self._hits) >= self.max_clients:
                return False
            self._hits[key] = deque()
        hits = self._hits[key]
        self._prune(hits, now)

        if len(hits) >= self.max_requests:
            return False

        hits.append(now)
        return True


def client_key(request, *, trust_railway_proxy: bool = False) -> str:
    """Use the socket peer unless explicitly deployed behind Railway HTTP ingress.

    Railway provides X-Real-IP. Opt in only when every request passes through
    that ingress; X-Forwarded-For is never used. Run Uvicorn with
    --no-proxy-headers so it cannot rewrite the socket peer before this check.
    """
    if trust_railway_proxy:
        values = request.headers.getlist("x-real-ip")
        if len(values) == 1:
            try:
                address = ip_address(values[0].strip())
                return str(getattr(address, "ipv4_mapped", None) or address)
            except ValueError:
                pass
    return request.client.host if request.client else "unknown"
