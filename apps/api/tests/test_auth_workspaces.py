"""No legacy auth fixture: these tests exercise the real authentication boundary."""
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app import db
from app.api.dependencies import get_intake_workspace
from app.api.routes import auth as auth_routes
from app.api.routes import runs as run_routes
from app.core import auth
from app.main import app

USER_A = "11111111-1111-4111-8111-111111111111"
USER_B = "22222222-2222-4222-8222-222222222222"


@pytest.fixture(autouse=True)
def account_feature_mode(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "access_mode", "accounts")


@pytest.mark.parametrize("path", [
    "/api/v1/research-objects", "/api/v1/runs", "/api/v1/runs/id/export",
    "/api/v1/runs/id/results", "/api/v1/runs/id/provenance",
    "/api/v1/folders", "/api/v1/auth/me",
    "/api/v1/intake/confirmed-versions/sha256:" + "a" * 64 + "/fasta",
])
def test_anonymous_requests_cannot_read_any_workspace(path):
    response = TestClient(app).get(path)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("header", ["", "Basic aaa", "Bearer ", "Bearer forged"])
def test_invalid_tokens_fail_closed(monkeypatch, header):
    async def reject(_):
        raise ValueError("Invalid session")
    monkeypatch.setattr(auth, "verify_access_token", reject)
    assert TestClient(app).get("/api/v1/auth/me", headers={
        "Authorization": header,
    }).status_code == 401


def test_unavailable_provider_is_not_treated_as_anonymous_or_valid(monkeypatch):
    async def unavailable(_):
        raise httpx.ConnectError("internal secret must not escape")
    monkeypatch.setattr(auth, "verify_access_token", unavailable)
    response = TestClient(app).get("/api/v1/auth/me", headers={"Authorization": "Bearer x"})
    assert response.status_code == 503
    assert "secret" not in response.text


def test_request_context_is_verified_and_reset(monkeypatch):
    async def verify(token):
        return auth.Identity(USER_A if token == "a" else USER_B, token)
    monkeypatch.setattr(auth, "verify_access_token", verify)
    client = TestClient(app)
    for user, token in [(USER_A, "a"), (USER_B, "b")]:
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.json()["id"] == user
        assert auth.current_identity.get() is None


def test_database_authorization_is_user_jwt_not_service_role(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "supabase_url", "https://example.test")
    monkeypatch.setattr(settings, "supabase_service_key", "fixture-key")
    received = []
    client = SimpleNamespace(postgrest=SimpleNamespace(auth=lambda token: received.append(token)))
    monkeypatch.setattr(db, "create_client", lambda *args: client)
    marker = auth.current_identity.set(auth.Identity(USER_A, "verified-user-jwt"))
    try:
        assert db.get_supabase() is client
        assert received == ["verified-user-jwt"]
    finally:
        auth.current_identity.reset(marker)


def test_workspace_paths_are_separate_and_do_not_adopt_shared_data():
    roots = []
    for user in (USER_A, USER_B):
        marker = auth.current_identity.set(auth.Identity(user, "x"))
        try:
            workspace = get_intake_workspace()
            roots.append(workspace.root)
        finally:
            auth.current_identity.reset(marker)
    assert roots[0] != roots[1]
    assert str(roots[0]).endswith(f"users/{USER_A}")
    assert str(roots[1]).endswith(f"users/{USER_B}")


def test_cors_allows_authorization_without_authenticating_preflight():
    from app.core.config import settings
    response = TestClient(app).options("/api/v1/runs", headers={
        "Origin": settings.cors_origin, "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization",
    })
    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_login_limits_and_provider_details_do_not_escape(monkeypatch):
    auth_routes._attempts.clear()
    monkeypatch.setattr(auth_routes.settings, "supabase_url", "")
    client = TestClient(app)
    for _ in range(10):
        assert client.post("/api/v1/auth/login", json={
            "email": "a@example.test", "password": "x",
        }).status_code == 503
    assert client.post("/api/v1/auth/login", json={
        "email": "a@example.test", "password": "x",
    }).status_code == 429
    auth_routes._attempts.clear()


def test_migration_preserves_unowned_rows_and_restricts_child_records():
    sql = (Path(__file__).parents[1] / "migrations/008_personal_workspaces.sql").read_text()
    assert "DELETE FROM" not in sql
    assert "UPDATE public.research_objects" not in sql
    assert sql.count("AS RESTRICTIVE") == 5
    assert "FROM anon, authenticated, PUBLIC" in sql
    assert "r.research_object_id = results.research_object_id" in sql
    assert "REFERENCES public.research_folders(owner_id, folder_id)" in sql


@pytest.mark.parametrize("counts,expected", [
    ({"completed": 0, "failed": 0, "queued": 0, "running": 0}, None),
    ({"completed": 1, "failed": 7, "queued": 20, "running": 2}, 12.5),
    ({"completed": 2000, "failed": 2000, "queued": 0, "running": 0}, 50),
    ({"completed": 0, "failed": 1, "queued": 0, "running": 0}, 0),
])
def test_completion_rate_uses_exact_counts_not_paginated_lists(monkeypatch, counts, expected):
    class Counter:
        def table(self, name):
            assert name == "runs"
            return self

        def select(self, column, **kwargs):
            assert column == "run_id"
            assert kwargs == {"count": "exact", "head": True}
            return self

        def eq(self, column, status):
            assert column == "status"
            self.status = status
            return self

        def execute(self):
            return SimpleNamespace(count=counts[self.status])

    monkeypatch.setattr(run_routes, "get_supabase", Counter)
    metrics = run_routes.run_metrics()
    assert metrics["percent"] == expected
    assert metrics["finished"] == counts["completed"] + counts["failed"]
    assert metrics["meaning"] == "workflow_completion_only"


def test_login_and_identity_use_provider_verification_without_leaking_refresh_tokens(monkeypatch):
    from app.core.config import settings
    auth_routes._attempts.clear()
    monkeypatch.setattr(settings, "supabase_url", "https://auth.example.test")
    monkeypatch.setattr(settings, "supabase_service_key", "fixture-admin-key")
    captured = []

    def provider(request):
        captured.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={
                "access_token": "fixture-token", "expires_in": 3600,
                "refresh_token": "must-not-return",
                "user": {"id": USER_A, "email": "a@example.test"},
            })
        if request.url.path.endswith("/logout"):
            return httpx.Response(204)
        assert request.headers["authorization"] == "Bearer fixture-token"
        return httpx.Response(200, json={"id": USER_A, "email": "a@example.test"})

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(
        **kwargs, transport=httpx.MockTransport(provider),
    ))
    client = TestClient(app)
    response = client.post("/api/v1/auth/login", json={
        "email": "a@example.test", "password": "fixture-password",
    })
    assert response.status_code == 200
    assert all(not attempts for attempts in auth_routes._attempts.values())
    assert set(response.json()) == {"access_token", "expires_in", "user"}
    assert "must-not-return" not in response.text
    assert "fixture-admin-key" not in response.text
    headers = {"Authorization": "Bearer fixture-token"}
    assert client.get("/api/v1/auth/me", headers=headers).json()["id"] == USER_A
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert len(captured) == 4  # login, verify /me, verify /logout, revoke
