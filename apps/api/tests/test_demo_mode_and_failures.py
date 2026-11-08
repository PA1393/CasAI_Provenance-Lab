"""No-login namespace isolation and truthful failure classification."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import db
from app.api.dependencies import get_intake_workspace
from app.api.routes import runs as routes
from app.core.config import settings
from app.main import app
from app.modules.rag import service as rag
from app.modules.runs.issues import run_issue
from app.modules.simulation import spec


def test_no_login_demo_reaches_only_the_demo_workspace(monkeypatch):
    monkeypatch.setattr(settings, "access_mode", "demo")
    monkeypatch.setattr(routes, "list_runs", lambda: [])
    client = TestClient(app)
    assert client.get("/api/v1/runs").json() == {"items": []}
    capabilities = client.get("/api/v1/demo/capabilities").json()
    assert capabilities["access_mode"] == "demo"
    assert capabilities["authentication"] == "none"
    assert not capabilities["personal_workspaces"]
    assert client.post("/api/v1/auth/login", json={
        "email": "someone@example.test", "password": "not-a-real-password",
    }).status_code == 409
    assert str(get_intake_workspace().root).endswith("/demo")


def test_demo_db_routes_every_domain_table_and_rejects_unknown_access(monkeypatch):
    monkeypatch.setattr(settings, "access_mode", "demo")
    monkeypatch.setattr(settings, "supabase_url", "https://example.test")
    monkeypatch.setattr(settings, "supabase_service_key", "fixture-key")
    client = MagicMock()
    monkeypatch.setattr(db, "create_client", lambda *args: client)
    demo = db.get_supabase()
    for table in db.DEMO_TABLES:
        demo.table(table)
        client.table.assert_called_with(f"demo_{table}")
    with pytest.raises(ValueError):
        demo.table("auth.users")
    with pytest.raises(ValueError):
        demo.table("vault_sources")
    with pytest.raises(ValueError):
        demo.rpc("arbitrary_admin_function", {})
    demo.rpc("match_vault_chunks", {"match_count": 3})
    client.rpc.assert_called_once_with("match_vault_chunks", {"match_count": 3})
    client.postgrest.auth.assert_not_called()


def test_vault_not_configured_is_not_reported_as_no_evidence(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(rag.VaultSearchError) as caught:
        rag.search_vault("rice", strict=True)
    assert caught.value.code == "vault_not_configured"
    assert rag.search_vault("rice") == []  # Legacy optional retrieval still supported.


@pytest.mark.parametrize("cause", ["embedding", "database"])
def test_vault_service_failure_is_not_reported_as_no_matches(monkeypatch, cause):
    monkeypatch.setattr(settings, "openai_api_key", "fixture-key")
    monkeypatch.setattr(rag, "embed_query", lambda _: None if cause == "embedding" else [0.1])
    def broken():
        raise RuntimeError("private-provider-error-must-not-escape")
    monkeypatch.setattr(rag, "get_supabase", broken)
    with pytest.raises(rag.VaultSearchError) as caught:
        rag.search_vault("rice", strict=True)
    assert caught.value.code == "vault_unavailable"
    issue = run_issue("extract", caught.value.code)
    assert "Coverage is unknown" in issue.message
    assert "private-provider" not in issue.model_dump_json()


def test_real_zero_matches_blocks_ai_instead_of_guessing(monkeypatch):
    seen = []
    monkeypatch.setattr(spec, "search_vault", lambda *args, **kwargs: [])
    monkeypatch.setattr(spec, "_extract_intent", lambda *args: seen.append(args))
    with pytest.raises(spec.AnalysisIssue) as caught:
        spec.resolve_edit_spec("uncovered objective", "ACGT")
    assert caught.value.code == "vault_no_evidence"
    assert seen == []


@pytest.mark.parametrize("intent,code", [
    ({"edit_type": None}, "intent_unclear"),
    ({"edit_type": "CBE"}, "no_compatible_site"),
])
def test_unclear_objective_and_no_site_have_different_reasons(monkeypatch, intent, code):
    monkeypatch.setattr(spec, "search_vault", lambda *args, **kwargs: [{"source_key": "fixture"}])
    monkeypatch.setattr(spec, "_extract_intent", lambda *args: intent)
    with pytest.raises(spec.AnalysisIssue) as caught:
        spec.resolve_edit_spec("objective", "AT" * 20)
    assert caught.value.code == code


def test_accepted_analysis_preserves_exact_retrieved_sources(monkeypatch):
    chunks = [{"chunk_id": "c1", "source_key": "reviewed-reference",
               "chunk_text": "Fixture evidence, not a biological assertion.", "similarity": 0.8,
               "private_metadata": "do-not-copy"}]
    monkeypatch.setattr(spec, "search_vault", lambda *args, **kwargs: chunks)
    monkeypatch.setattr(spec, "_extract_intent", lambda *args: {"edit_type": "CBE"})
    result = spec.resolve_edit_spec("explicit conversion", "TTACGTACGTACGTACGTACGTCGGTT")
    assert result.rag_sources[0]["source_key"] == "reviewed-reference"
    assert result.rag_sources[0]["chunk_text"] == chunks[0]["chunk_text"]
    assert "private_metadata" not in result.rag_sources[0]


def test_default_mode_is_demo():
    from app.core.config import Settings
    assert Settings(_env_file=None).access_mode == "demo"


def test_storage_capability_describes_adapter_not_database_readiness():
    from app.api.dependencies import get_storage_backend
    client = TestClient(app)
    try:
        assert client.get("/api/v1/demo/capabilities").json()["storage_backend"] == "supabase"
        app.dependency_overrides[get_storage_backend] = lambda: "temporary"
        response = client.get("/api/v1/demo/capabilities")
        assert response.status_code == 200
        assert response.json()["storage_backend"] == "temporary"
        assert "database_verified" not in response.json()
    finally:
        app.dependency_overrides.pop(get_storage_backend, None)


def test_missing_demo_schema_gives_setup_instructions_without_sql_details(monkeypatch):
    from postgrest.exceptions import APIError
    monkeypatch.setattr(settings, "access_mode", "demo")
    def missing():
        raise APIError({"code": "PGRST205", "message": "private-schema-detail"})
    monkeypatch.setattr(routes, "list_runs", missing)
    response = TestClient(app).get("/api/v1/runs")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "workspace_setup_required"
    assert "private-schema" not in response.text
