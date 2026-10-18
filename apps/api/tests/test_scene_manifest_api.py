"""Scene manifest API stores only validated declarative scene content."""

import json

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_intake_workspace
from app.main import app
from app.modules.information_processor.contracts import checksum
from app.modules.information_processor.workspace import LocalWorkspace


@pytest.fixture
def client(tmp_path):
    workspace = LocalWorkspace(tmp_path / "workspace")
    app.dependency_overrides[get_intake_workspace] = lambda: workspace
    try:
        yield TestClient(app), workspace
    finally:
        app.dependency_overrides.pop(get_intake_workspace, None)


def _request(workspace):
    content = b"data_test\n#\n"
    identity = checksum(content)
    workspace._store_artifact(identity, content)
    return {
        "scene_status": "predicted",
        "assets": [
            {
                "asset_id": "complex",
                "source_type": "workspace_artifact",
                "source_id": identity,
                "format": "mmcif",
                "checksum": identity,
                "structure_status": "predicted",
            }
        ],
        "selections": [
            {
                "selection_id": "enzyme",
                "asset_id": "complex",
                "role": "protein",
                "chain_id": "A",
            },
            {
                "selection_id": "guide",
                "asset_id": "complex",
                "role": "guide",
                "chain_id": "G",
                "nucleotide_positions": [1, 2, 3],
            },
        ],
        "annotations": [],
        "measurements": [],
        "transforms": [],
        "cameras": [],
        "visibility_states": [],
    }


def test_create_and_get_scene_manifest_are_content_addressed(client):
    http, workspace = client
    request = _request(workspace)
    created = http.post("/api/v1/scene-manifests", json=request)

    assert created.status_code == 201
    scene = created.json()
    fetched = http.get(f"/api/v1/scene-manifests/{scene['scene_id']}")
    repeated = http.post("/api/v1/scene-manifests", json=request)

    assert fetched.status_code == 200
    assert fetched.json() == scene
    assert repeated.status_code == 201
    assert repeated.json()["scene_id"] == scene["scene_id"]


def test_missing_scene_and_unknown_references_are_rejected(client):
    http, workspace = client
    missing = http.get("/api/v1/scene-manifests/sha256:" + "0" * 64)
    assert missing.status_code == 404

    request = _request(workspace)
    request["selections"][0]["asset_id"] = "missing"
    invalid = http.post("/api/v1/scene-manifests", json=request)
    assert invalid.status_code == 422
    assert "scene asset" in invalid.json()["detail"]


def test_unsafe_asset_url_and_unbacked_workspace_asset_are_rejected(client):
    http, workspace = client
    request = _request(workspace)
    request["assets"][0].update(
        {
            "source_type": "database_record",
            "source_id": "https://untrusted.example/structure.cif",
        }
    )
    unsafe = http.post("/api/v1/scene-manifests", json=request)
    assert unsafe.status_code == 422

    request = _request(workspace)
    absent = "sha256:" + "9" * 64
    request["assets"][0]["source_id"] = absent
    request["assets"][0]["checksum"] = absent
    unbacked = http.post("/api/v1/scene-manifests", json=request)
    assert unbacked.status_code == 409
    assert "missing" in unbacked.json()["detail"]


def test_tampered_stored_scene_returns_integrity_error(client):
    http, workspace = client
    created = http.post("/api/v1/scene-manifests", json=_request(workspace)).json()
    path = workspace.scene_manifest_path(created["scene_id"])
    payload = json.loads(path.read_text())
    payload["scene_status"] = "explanatory"
    path.write_text(json.dumps(payload))

    response = http.get(f"/api/v1/scene-manifests/{created['scene_id']}")
    assert response.status_code == 409


def test_request_collections_are_bounded(client):
    http, workspace = client
    request = _request(workspace)
    request["assets"] = request["assets"] * 33
    response = http.post("/api/v1/scene-manifests", json=request)
    assert response.status_code == 422
