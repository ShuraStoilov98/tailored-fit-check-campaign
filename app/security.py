"""Bound API traffic before FastAPI parses multipart files or JSON."""

import asyncio

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.rate_limit import RateLimiter, client_key

MULTIPART_OVERHEAD_BYTES = 64 * 1024
MAX_JSON_BYTES = 16 * 1024


class RequestProtectionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_upload_bytes: int,
        limiters: dict[str, RateLimiter],
        api_limiter: RateLimiter,
        fit_check_limiter: RateLimiter,
        trust_railway_proxy: bool = False,
        body_timeout_seconds: float = 30,
    ) -> None:
        self.app = app
        self.max_upload_bytes = max_upload_bytes
        self.limiters = limiters
        self.api_limiter = api_limiter
        self.fit_check_limiter = fit_check_limiter
        self.trust_railway_proxy = trust_railway_proxy
        self.body_timeout_seconds = body_timeout_seconds

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = scope["path"]
        key = client_key(request, trust_railway_proxy=self.trust_railway_proxy)
        limiter = self.limiters.get(path)
        allowed = self.api_limiter.allow("all")
        if allowed and limiter is not None:
            allowed = limiter.allow(key)
        if allowed and path == "/api/fit-check":
            allowed = self.fit_check_limiter.allow("all")
        if not allowed:
            await JSONResponse(
                {"error": "Please wait a moment before trying again.", "error_code": "RATE_LIMITED"},
                status_code=429,
                headers={"Retry-After": str(self.api_limiter.window_seconds)},
            )(scope, receive, send)
            return

        is_upload = path == "/api/fit-check"
        limit = self.max_upload_bytes + MULTIPART_OVERHEAD_BYTES if is_upload else MAX_JSON_BYTES
        too_large = JSONResponse(
            {
                "error": "This photo is too large. Please choose a smaller image." if is_upload else "This request is too large. Please try again.",
                "error_code": "IMAGE_TOO_LARGE" if is_upload else "REQUEST_TOO_LARGE",
            },
            status_code=413,
        )

        lengths = request.headers.getlist("content-length")
        try:
            if len(lengths) > 1 or (lengths and (not lengths[0].isascii() or not lengths[0].isdigit())):
                raise ValueError
            if lengths and int(lengths[0]) > limit:
                await too_large(scope, receive, send)
                return
        except ValueError:
            await JSONResponse({"error": "Please check your request and try again."}, status_code=400)(scope, receive, send)
            return

        # Buffer only a bounded body, then replay it to the multipart parser.
        # Checking actual bytes also covers chunked and misreported-length bodies.
        body = bytearray()
        try:
            async with asyncio.timeout(self.body_timeout_seconds):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > limit:
                        await too_large(scope, receive, send)
                        return
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse({"error": "The upload took too long. Please try again."}, status_code=408)(scope, receive, send)
            return

        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)
