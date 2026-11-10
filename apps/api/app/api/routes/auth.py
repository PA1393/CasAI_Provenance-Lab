"""Supabase password sign-in; no credentials or tokens are persisted by CasAI."""

import time
from collections import OrderedDict
from threading import Lock

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import current_identity
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
_attempts: OrderedDict[str, list[float]] = OrderedDict()
_lock = Lock()


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


@router.post("/login")
async def login(body: LoginBody, request: Request):
    if settings.access_mode != "accounts":
        raise HTTPException(409, "Accounts are saved for a later release; use the demo workspace")
    # Supplemental per-instance bound. Configure provider/global abuse controls too.
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _lock:
        times = [t for t in _attempts.get(key, []) if now - t < 900]
        if len(times) >= 10:
            raise HTTPException(429, "Too many sign-in attempts")
        _attempts[key] = [*times, now]
        _attempts.move_to_end(key)
        while len(_attempts) > 10_000:
            _attempts.popitem(last=False)
    if not settings.supabase_url or not settings.supabase_service_key:
        raise HTTPException(503, "Sign-in is not configured")
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.post(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password",
                headers={"apikey": settings.supabase_service_key},
                json={"email": body.email.strip(), "password": body.password},
            )
        if response.status_code in {400, 401, 403, 422}:
            raise HTTPException(401, "Email or password is incorrect")
        if response.status_code == 429:
            raise HTTPException(429, "Too many sign-in attempts")
        response.raise_for_status()
        data = response.json()
        result = {
            "access_token": data["access_token"],
            "expires_in": data["expires_in"],
            "user": {"id": data["user"]["id"], "email": data["user"].get("email", "")},
        }
        # Successful logins should not lock out reviewers who reload the app.
        with _lock:
            _attempts[key] = [attempt for attempt in _attempts.get(key, []) if attempt != now]
        return result
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(503, "Sign-in is temporarily unavailable") from exc


@router.get("/me")
def me():
    identity = current_identity.get()
    if identity is None:
        raise HTTPException(401, "Sign in")
    return {"id": identity.user_id, "email": identity.email}


@router.post("/logout")
async def logout():
    if settings.access_mode != "accounts":
        raise HTTPException(409, "Accounts are not enabled in this demo")
    identity = current_identity.get()
    if identity is None:
        raise HTTPException(401, "Sign in")
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.post(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/logout",
                headers={"apikey": settings.supabase_service_key,
                         "Authorization": f"Bearer {identity.access_token}"},
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Remote session revocation unavailable") from exc
    return {"signed_out": True}
