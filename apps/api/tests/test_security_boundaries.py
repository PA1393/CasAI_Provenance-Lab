"""Shared API transport and configuration security boundaries."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.security import RateLimitMiddleware, RequestSizeLimitMiddleware
from app.main import app


def test_api_responses_include_conservative_security_headers():
    response = TestClient(app).get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )
    assert response.headers["cache-control"] == "no-store"


def test_declared_oversized_request_is_rejected_before_routing():
    client = TestClient(app)
    response = client.post(
        "/health",
        content=b"x",
        headers={"content-length": str(settings.max_request_bytes + 1)},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_streamed_body_is_bounded_even_without_content_length():
    reached = False

    async def consuming_app(scope, receive, send):
        nonlocal reached
        while True:
            message = await receive()
            if not message.get("more_body", False):
                break
        reached = True

    middleware = RequestSizeLimitMiddleware(consuming_app, max_bytes=3)
    incoming = iter(
        (
            {"type": "http.request", "body": b"aa", "more_body": True},
            {"type": "http.request", "body": b"bb", "more_body": False},
        )
    )
    outgoing = []

    async def receive():
        return next(incoming)

    async def send(message):
        outgoing.append(message)

    asyncio.run(middleware({"type": "http", "headers": []}, receive, send))

    assert reached is False
    assert outgoing[0]["status"] == 413


def test_rate_limit_rejects_burst_and_reports_retry_window():
    clock_value = 100.0

    async def endpoint(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    limiter = RateLimitMiddleware(
        endpoint,
        requests_per_minute=2,
        max_clients=100,
        clock=lambda: clock_value,
    )

    async def call():
        outgoing = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            outgoing.append(message)

        await limiter(
            {"type": "http", "headers": [], "client": ("192.0.2.1", 5000)},
            receive,
            send,
        )
        return outgoing

    first, second, third = asyncio.run(_three_calls(call))
    assert first[0]["status"] == second[0]["status"] == 204
    assert third[0]["status"] == 429
    assert (b"retry-after", b"60") in third[0]["headers"]


async def _three_calls(call):
    return await call(), await call(), await call()


@pytest.mark.parametrize("origin", ["*", "ftp://example.test", "https://one.test,https://two.test"])
def test_cors_configuration_requires_one_explicit_http_origin(origin):
    with pytest.raises(ValidationError, match="CORS_ORIGIN"):
        Settings(_env_file=None, cors_origin=origin)


def test_production_cors_requires_https():
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            _env_file=None,
            environment="production",
            cors_origin="http://example.test",
            rate_limit_requests_per_minute=60,
        )


def test_production_requires_rate_limiting():
    with pytest.raises(ValidationError, match="nonzero rate limit"):
        Settings(
            _env_file=None,
            environment="production",
            cors_origin="https://example.test",
        )


def test_request_limit_configuration_is_bounded():
    with pytest.raises(ValidationError, match="MAX_REQUEST_BYTES"):
        Settings(_env_file=None, max_request_bytes=999_999)
