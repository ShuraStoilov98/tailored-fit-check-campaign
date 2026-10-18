"""Unit tests for the in-memory rate limiter."""

from app.rate_limit import RateLimiter


def test_allows_up_to_the_budget():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert [limiter.allow("ip") for _ in range(4)] == [True, True, True, False]


def test_budgets_are_per_key():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False


def test_hits_expire_once_the_window_passes(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr("app.rate_limit.time.monotonic", lambda: clock["now"])

    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("ip") is True
    assert limiter.allow("ip") is True
    assert limiter.allow("ip") is False

    clock["now"] += 61
    assert limiter.allow("ip") is True
