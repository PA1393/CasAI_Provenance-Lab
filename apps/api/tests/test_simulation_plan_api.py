"""Draft simulation-plan API binds only stored confirmed mapping inputs."""

import json

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_intake_workspace
from app.main import app
from app.modules.information_processor.workspace import LocalWorkspace

GUIDE = "AAACACAAAAAAAAAAAAAA"
SEQUENCE = "TTTT" + GUIDE + "AGG" + "TTTT"


@pytest.fixture
def client(tmp_path):
    workspace = LocalWorkspace(tmp_path / "workspace")
    app.dependency_overrides[get_intake_workspace] = lambda: workspace
    try:
        yield TestClient(app), workspace
    finally:
        app.dependency_overrides.pop(get_intake_workspace, None)


def _mapping(http):
    stored = http.post(
        "/api/v1/intake/research-drafts",
        json={
            "input_method": "fasta",
            "content": f">target\n{SEQUENCE}\n",
            "molecule_type": "DNA",
        },
    ).json()
    draft = stored["draft"]
    confirmed = http.post(
        f"/api/v1/intake/research-drafts/{stored['draft_id']}/confirm",
        json={
            "expected_normalized_checksum": draft["normalized_checksum"],
            "expected_artifact_checksum": draft["artifact_checksum"],
            "actor_id": "researcher-01",
            "decision": "approve",
            "acknowledged_warning_codes": sorted(
                {warning["code"] for warning in draft["warnings"]}
            ),
        },
    ).json()
    mapped = http.post(
        "/api/v1/guide-maps",
        json={
            "source_version_id": confirmed["version_id"],
            "source_record_id": "target",
            "editor": "CBE",
        },
    ).json()
    return confirmed, mapped


def _request(confirmed, mapped, **changes):
    body = {
        "confirmed_version_id": confirmed["version_id"],
        "guide_map_id": mapped["map_id"],
        "guide_ranking_id": mapped["ranking_id"],
        "stages": [
            {
                "stage_id": "sequence_edit",
                "engine": "casai.sequence-edit",
                "engine_version": "1",
                "operation": "apply_base_edit",
                "requirement": "required",
                "settings": [{"name": "editor", "value": "CBE"}],
            }
        ],
        "limitations": ["Sequence-level explanatory computation only"],
    }
    body.update(changes)
    return body


def test_create_and_get_draft_plan_are_content_addressed(client):
    http, _ = client
    confirmed, mapped = _mapping(http)
    request = _request(confirmed, mapped)
    created = http.post("/api/v1/simulation-plans", json=request)

    assert created.status_code == 201
    plan = created.json()
    fetched = http.get(f"/api/v1/simulation-plans/{plan['plan_id']}")
    repeated = http.post("/api/v1/simulation-plans", json=request)

    assert plan["status"] == "draft"
    assert plan["executable"] is False
    assert fetched.status_code == 200
    assert fetched.json() == plan
    assert repeated.json()["plan_id"] == plan["plan_id"]


def test_missing_plan_and_missing_inputs_return_not_found(client):
    http, _ = client
    absent = "sha256:" + "0" * 64
    assert http.get(f"/api/v1/simulation-plans/{absent}").status_code == 404

    response = http.post(
        "/api/v1/simulation-plans",
        json={
            "confirmed_version_id": absent,
            "guide_map_id": absent,
            "stages": [
                {
                    "stage_id": "edit",
                    "engine": "casai.sequence-edit",
                    "engine_version": "1",
                    "operation": "apply_base_edit",
                    "requirement": "required",
                }
            ],
        },
    )
    assert response.status_code == 404


def test_api_cannot_self_approve_or_mark_plan_executable(client):
    http, _ = client
    confirmed, mapped = _mapping(http)
    request = _request(confirmed, mapped, status="approved", executable=True)
    response = http.post("/api/v1/simulation-plans", json=request)
    assert response.status_code == 422


def test_tampered_stored_plan_returns_integrity_error(client):
    http, workspace = client
    confirmed, mapped = _mapping(http)
    created = http.post(
        "/api/v1/simulation-plans",
        json=_request(confirmed, mapped),
    ).json()
    path = workspace.simulation_plan_path(created["plan_id"])
    payload = json.loads(path.read_text())
    payload["limitations"] = ["tampered"]
    path.write_text(json.dumps(payload))

    response = http.get(f"/api/v1/simulation-plans/{created['plan_id']}")
    assert response.status_code == 409


def test_stage_collection_is_bounded(client):
    http, _ = client
    confirmed, mapped = _mapping(http)
    request = _request(confirmed, mapped)
    request["stages"] = request["stages"] * 33
    response = http.post("/api/v1/simulation-plans", json=request)
    assert response.status_code == 422
