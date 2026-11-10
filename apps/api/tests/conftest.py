"""Legacy route-contract tests use a fake verified identity, not a live account.

Only the enumerated existing adapter suites opt in. Authentication/tenant tests
are deliberately excluded and exercise the real middleware without this shim.
There is NO test bypass or optional-auth switch in production code.
"""
import pytest
from starlette.testclient import TestClient

from app.core import auth
from app.core.config import settings

_CONTRACT_SUITES = {
    "test_rag_ask.py", "test_provenance.py", "test_intake_api.py",
    "test_confirmed_handoff.py", "test_research_draft_api.py", "test_runs.py",
    "test_runs_pipeline.py", "test_scene_manifest_api.py", "test_demo_exports.py",
    "test_desktop_intake.py", "test_simulation_plan_api.py", "test_guide_mapping_api.py",
}


@pytest.fixture(autouse=True)
def legacy_contract_identity(request, monkeypatch):
    if request.path.name not in _CONTRACT_SUITES:
        return
    monkeypatch.setattr(settings, "access_mode", "accounts")

    async def verify(token):
        assert token == "contract-test-token"
        return auth.Identity("11111111-1111-4111-8111-111111111111", token)

    original = TestClient.request

    def authenticated_request(self, method, url, **kwargs):
        kwargs["headers"] = {
            **(kwargs.get("headers") or {}), "Authorization": "Bearer contract-test-token",
        }
        return original(self, method, url, **kwargs)

    monkeypatch.setattr(auth, "verify_access_token", verify)
    monkeypatch.setattr(TestClient, "request", authenticated_request)
