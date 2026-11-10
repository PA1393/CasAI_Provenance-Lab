"""Verified, request-local identity. Never decode an unverified JWT for ownership."""

from contextvars import ContextVar
from dataclasses import dataclass, field
from uuid import UUID

import httpx
from starlette.responses import JSONResponse

from app.core.config import settings


@dataclass(frozen=True)
class Identity:
    user_id: str
    access_token: str = field(repr=False)
    email: str = ""


current_identity: ContextVar[Identity | None] = ContextVar("casai_identity", default=None)


async def verify_access_token(token: str) -> Identity:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("Authentication is not configured")
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={"apikey": settings.supabase_service_key, "Authorization": f"Bearer {token}"},
        )
    if response.status_code in {401, 403}:
        raise ValueError("Invalid session")
    response.raise_for_status()
    user = response.json()
    return Identity(str(UUID(user["id"])), token, str(user.get("email") or ""))


class AuthenticationMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if settings.access_mode == "demo":
            # No user identity is inferred from headers in the shared demo.
            marker = current_identity.set(None)
            try:
                await self.app(scope, receive, send)
            finally:
                current_identity.reset(marker)
            return
        public = {
            f"{settings.api_prefix}/auth/login",
            f"{settings.api_prefix}/demo/capabilities",
        }
        if (scope["type"] != "http" or scope.get("method") == "OPTIONS"
                or not scope["path"].startswith(f"{settings.api_prefix}/")
                or scope["path"] in public):
            await self.app(scope, receive, send)
            return
        authorization = dict(scope.get("headers", [])).get(b"authorization", b"")
        try:
            scheme, token = authorization.decode("ascii").split(" ", 1)
            if scheme.lower() != "bearer" or not token or len(token) > 8192:
                raise ValueError("Invalid session")
            identity = await verify_access_token(token)
        except (ValueError, KeyError, UnicodeError):
            await JSONResponse({"detail": "Sign in to access your workspace"}, 401)(
                scope, receive, send,
            )
            return
        except (httpx.HTTPError, RuntimeError):
            await JSONResponse({"detail": "Authentication service unavailable"}, 503)(
                scope, receive, send,
            )
            return
        marker = current_identity.set(identity)
        try:
            await self.app(scope, receive, send)
        finally:
            current_identity.reset(marker)
