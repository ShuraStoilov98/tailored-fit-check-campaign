"""Unit tests for the in-memory rate limiter."""

import pytest
from starlette.requests import Request

from app.rate_limit import RateLimiter, client_key


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


def test_cleanup_removes_inactive_clients(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr("app.rate_limit.time.monotonic", lambda: clock["now"])
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    for index in range(2050):
        assert limiter.allow(str(index))
    clock["now"] += 61
    assert limiter.allow("new")
    assert list(limiter._hits) == ["new"]


def test_client_table_is_bounded_without_evicting_active_budgets():
    limiter = RateLimiter(max_requests=1, window_seconds=60, max_clients=2)
    assert limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("c")
    assert not limiter.allow("a")
    assert len(limiter._hits) == 2


def make_request(headers):
    return Request({"type": "http", "client": ("10.0.0.1", 1234), "headers": headers})


def test_proxy_headers_are_ignored_by_default():
    request = make_request([(b"x-forwarded-for", b"198.51.100.1"), (b"x-real-ip", b"192.0.2.1")])
    assert client_key(request) == "10.0.0.1"


def test_railway_mode_uses_real_ip_and_ignores_forwarded_chain():
    request = make_request([(b"x-forwarded-for", b"198.51.100.1, 10.0.0.2"), (b"x-real-ip", b"192.0.2.1")])
    assert client_key(request, trust_railway_proxy=True) == "192.0.2.1"


@pytest.mark.parametrize("value", [b"not-an-ip", b"", b"192.0.2.1, 192.0.2.2", b"192.0.2.1:80"])
def test_invalid_proxy_addresses_fall_back_to_socket(value):
    assert client_key(make_request([(b"x-real-ip", value)]), trust_railway_proxy=True) == "10.0.0.1"


def test_duplicate_real_ip_headers_fall_back_to_socket():
    request = make_request([(b"x-real-ip", b"192.0.2.1"), (b"x-real-ip", b"192.0.2.2")])
    assert client_key(request, trust_railway_proxy=True) == "10.0.0.1"


def test_ipv6_addresses_are_canonicalized():
    request = make_request([(b"x-real-ip", b"2001:0db8:0000:0000:0000:0000:0000:0001")])
    assert client_key(request, trust_railway_proxy=True) == "2001:db8::1"


def test_mapped_ipv4_addresses_share_the_ipv4_budget():
    request = make_request([(b"x-real-ip", b"::ffff:192.0.2.1")])
    assert client_key(request, trust_railway_proxy=True) == "192.0.2.1"
