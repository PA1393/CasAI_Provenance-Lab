"""Shared API transport and configuration security boundaries."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.security import RequestSizeLimitMiddleware
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
        )


def test_request_limit_configuration_is_bounded():
    with pytest.raises(ValidationError, match="MAX_REQUEST_BYTES"):
        Settings(_env_file=None, max_request_bytes=999_999)
