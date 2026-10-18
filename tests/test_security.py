"""Exercise raw ASGI bodies, including requests without a reliable length."""

import asyncio
import json

import pytest

from app.rate_limit import RateLimiter
from app.security import MAX_JSON_BYTES, MULTIPART_OVERHEAD_BYTES, RequestProtectionMiddleware


def run_request(*, messages, headers=(), path="/api/fit-check", body_timeout_seconds=30,
                limiters=None, api_limiter=None, fit_check_limiter=None, receive_delay_seconds=0):
    # Each invocation gets a separate event loop; no network or real server.
    async def execute():
        sent = []
        received = []
        reads = 0
        pending = iter(messages)

        async def receive():
            nonlocal reads
            reads += 1
            if receive_delay_seconds:
                await asyncio.sleep(receive_delay_seconds)
            return next(pending)

        async def send(message):
            sent.append(message)

        async def downstream(scope, receive, send):
            received.append(await receive())
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        middleware = RequestProtectionMiddleware(
            downstream, max_upload_bytes=1024, limiters=limiters or {},
            api_limiter=api_limiter or RateLimiter(max_requests=10, window_seconds=60),
            fit_check_limiter=fit_check_limiter or RateLimiter(max_requests=10, window_seconds=60),
            body_timeout_seconds=body_timeout_seconds,
        )
        await middleware({"type": "http", "method": "POST", "path": path,
                          "client": ("10.0.0.1", 1234), "headers": list(headers)}, receive, send)
        return sent, received, reads

    return asyncio.run(execute())


@pytest.mark.parametrize("headers", [[], [(b"content-length", b"1")]])
def test_streamed_upload_cannot_bypass_limit_with_missing_or_false_length(headers):
    limit = 1024 + MULTIPART_OVERHEAD_BYTES
    sent, downstream, reads = run_request(headers=headers, messages=[
        {"type": "http.request", "body": b"a" * limit, "more_body": True},
        {"type": "http.request", "body": b"b", "more_body": True},
        {"type": "http.request", "body": b"never read", "more_body": False},
    ])
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"])["error_code"] == "IMAGE_TOO_LARGE"
    assert downstream == []
    assert reads == 2


def test_known_oversize_body_is_rejected_without_reading_or_parsing():
    sent, downstream, reads = run_request(headers=[(b"content-length", b"9999999")], messages=[])
    assert sent[0]["status"] == 413
    assert downstream == []
    assert reads == 0


def test_small_streamed_body_is_replayed_unchanged():
    sent, downstream, reads = run_request(messages=[
        {"type": "http.request", "body": b"first", "more_body": True},
        {"type": "http.request", "body": b"last", "more_body": False},
    ])
    assert sent[0]["status"] == 204
    assert downstream == [{"type": "http.request", "body": b"firstlast", "more_body": False}]
    assert reads == 2


@pytest.mark.parametrize("headers", [[(b"content-length", b"-1")], [(b"content-length", b"abc")], [(b"content-length", b"1"), (b"content-length", b"1")]])
def test_invalid_length_is_rejected(headers):
    sent, downstream, reads = run_request(headers=headers, messages=[])
    assert sent[0]["status"] == 400
    assert downstream == []
    assert reads == 0


def test_blocked_client_body_is_never_read():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.allow("10.0.0.1")
    sent, downstream, reads = run_request(messages=[], limiters={"/api/fit-check": limiter})
    assert sent[0]["status"] == 429
    assert downstream == []
    assert reads == 0


def test_json_limit_covers_chunked_events():
    sent, downstream, reads = run_request(path="/api/event", messages=[
        {"type": "http.request", "body": b"x" * (MAX_JSON_BYTES + 1), "more_body": False},
    ])
    assert sent[0]["status"] == 413
    assert downstream == []


def test_disconnect_does_not_reach_parser():
    sent, downstream, reads = run_request(messages=[{"type": "http.disconnect"}])
    assert sent == []
    assert downstream == []


@pytest.mark.parametrize("which_limit", ["api_limiter", "fit_check_limiter"])
def test_global_limits_block_before_body_handling(which_limit):
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.allow("all")
    sent, downstream, reads = run_request(messages=[], **{which_limit: limiter})
    assert sent[0]["status"] == 429
    assert downstream == []
    assert reads == 0


def test_slow_upload_returns_friendly_timeout_without_parsing():
    sent, downstream, reads = run_request(
        messages=[{"type": "http.request", "body": b"a", "more_body": False}],
        body_timeout_seconds=0.001, receive_delay_seconds=0.1,
    )
    assert sent[0]["status"] == 408
    assert "try again" in json.loads(sent[1]["body"])["error"]
    assert downstream == []
