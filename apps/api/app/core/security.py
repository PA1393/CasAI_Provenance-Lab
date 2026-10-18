"""Small ASGI security boundaries shared by every API route."""

from __future__ import annotations

import json
import math
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class RequestTooLargeError(RuntimeError):
    pass


class RequestSizeLimitMiddleware:
    """Reject declared or streamed request bodies beyond a fixed byte ceiling."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", ()))
        declared = headers.get(b"content-length")
        if declared is not None:
            try:
                content_length = int(declared)
            except ValueError:
                await _error(send, 400, "invalid_content_length", "Invalid Content-Length")
                return
            if content_length < 0:
                await _error(send, 400, "invalid_content_length", "Invalid Content-Length")
                return
            if content_length > self.max_bytes:
                await _error(send, 413, "request_too_large", "Request body exceeds limit")
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLargeError:
            await _error(send, 413, "request_too_large", "Request body exceeds limit")


class SecurityHeadersMiddleware:
    """Attach conservative browser-facing headers to API responses."""

    def __init__(self, app: ASGIApp, *, production: bool = False) -> None:
        self.app = app
        self.production = production

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secured_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", ()))
                existing = {name.lower() for name, _ in headers}
                additions = (
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                    (b"cache-control", b"no-store"),
                )
                headers.extend(item for item in additions if item[0] not in existing)
                if self.production and b"strict-transport-security" not in existing:
                    headers.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, secured_send)


class RateLimitMiddleware:
    """Bound request bursts per direct client in one API worker."""

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int,
        *,
        max_clients: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.app = app
        self.limit = requests_per_minute
        self.max_clients = max_clients
        self.clock = clock
        self._buckets: OrderedDict[str, tuple[float, int]] = OrderedDict()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self.limit == 0:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        key = str(client[0]) if client else "unknown"
        now = self.clock()
        started, count = self._buckets.get(key, (now, 0))
        if now - started >= 60:
            started, count = now, 0
        if count >= self.limit:
            retry_after = max(1, math.ceil(60 - (now - started)))
            await _error(
                send,
                429,
                "rate_limit_exceeded",
                "Request rate limit exceeded",
                headers=((b"retry-after", str(retry_after).encode("ascii")),),
            )
            return

        self._buckets[key] = (started, count + 1)
        self._buckets.move_to_end(key)
        while len(self._buckets) > self.max_clients:
            self._buckets.popitem(last=False)
        await self.app(scope, receive, send)


async def _error(
    send: Send,
    status: int,
    code: str,
    message: str,
    *,
    headers: tuple[tuple[bytes, bytes], ...] = (),
) -> None:
    body = json.dumps({"error": {"code": code, "message": message}}).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                *headers,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
