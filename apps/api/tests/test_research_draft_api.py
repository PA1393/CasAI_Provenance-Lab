"""HTTP boundaries for detection, persisted drafts, missing fields and confirmation."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_intake_workspace
from app.main import app
from app.modules.information_processor.workspace import LocalWorkspace


@pytest.fixture
def client(tmp_path):
    workspace = LocalWorkspace(tmp_path / "workspace")
    app.dependency_overrides[get_intake_workspace] = lambda: workspace
    try:
        yield TestClient(app), workspace
    finally:
        app.dependency_overrides.pop(get_intake_workspace, None)


def _store(client, **changes):
    body = {
        "input_method": "fasta",
        "content": ">source\nACGT\n",
        "molecule_type": "DNA",
    }
    body.update(changes)
    return client.post("/api/v1/intake/research-drafts", json=body)


def test_detect_requires_review_and_never_echoes_sequence(client):
    http, _ = client
    response = http.post("/api/v1/intake/detect", json={"content": "acgt"})

    assert response.status_code == 200
    assert response.json()["detection"] == {
        "detected_method": "pasted_sequence",
        "candidate_molecule_types": ["DNA", "protein"],
        "requires_confirmation": True,
        "reason": "Compatible letters alone cannot distinguish a sequence from prose",
    }
    assert "acgt" not in response.text


def test_store_draft_returns_identity_summary_without_raw_bases(client):
    http, workspace = client
    response = _store(http)

    assert response.status_code == 201
    body = response.json()
    assert body["outcome"] == "accepted"
    assert body["draft_id"].startswith("sha256:")
    assert body["draft"]["ready_for_confirmation"] is True
    assert workspace.manifest_path(body["draft_id"]).is_file()
    assert "ACGT" not in response.text
    assert "content" not in body["draft"]


def test_sequence_inspection_can_summarize_unresolved_molecule_type(client):
    http, _ = client
    response = http.post(
        "/api/v1/intake/sequences/inspect",
        json={"declared_format": "pasted_sequence", "content": "ACGT"},
    )

    assert response.status_code == 200
    assert response.json()["draft"]["records"][0]["molecule_type"] is None
    assert response.json()["draft"]["ready_for_confirmation"] is False


def test_unresolved_draft_can_be_saved_and_missing_fields_inspected(client):
    http, _ = client
    stored = _store(http, molecule_type=None).json()
    response = http.get(f"/api/v1/intake/research-drafts/{stored['draft_id']}/missing")

    assert response.status_code == 200
    body = response.json()
    assert body["ready_for_confirmation"] is False
    required = {
        field["field"] for field in body["missing_fields"] if field["requirement"] == "required"
    }
    assert required == {"molecule_type"}


def test_confirm_exact_stored_draft_and_reopen_version(client):
    http, workspace = client
    stored = _store(http).json()
    draft = stored["draft"]
    response = http.post(
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
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["executable"] is True
    assert body["approved_by"] == "researcher-01"
    assert "ACGT" not in response.text
    assert workspace.load_confirmed_version(body["version_id"]).version_id == body["version_id"]


def test_confirm_rejects_missing_information_stale_identity_and_unacknowledged_warning(client):
    http, _ = client
    incomplete = _store(http, molecule_type=None).json()
    rejected = http.post(
        f"/api/v1/intake/research-drafts/{incomplete['draft_id']}/confirm",
        json={
            "expected_normalized_checksum": incomplete["draft"]["normalized_checksum"],
            "expected_artifact_checksum": incomplete["draft"]["artifact_checksum"],
            "actor_id": "researcher-01",
            "decision": "approve",
            "acknowledged_warning_codes": sorted(
                {warning["code"] for warning in incomplete["draft"]["warnings"]}
            ),
        },
    )
    assert rejected.status_code == 409
    assert "Required information" in rejected.json()["detail"]

    warned = _store(http, content=">source\nACGN\n").json()
    stale = http.post(
        f"/api/v1/intake/research-drafts/{warned['draft_id']}/confirm",
        json={
            "expected_normalized_checksum": "sha256:" + "0" * 64,
            "expected_artifact_checksum": warned["draft"]["artifact_checksum"],
            "actor_id": "researcher-01",
            "decision": "approve",
            "acknowledged_warning_codes": [],
        },
    )
    assert stale.status_code == 409
    assert "identity changed" in stale.json()["detail"]


def test_missing_and_confirmation_paths_validate_identity_and_absence(client):
    http, _ = client
    malformed = http.get("/api/v1/intake/research-drafts/not-a-hash/missing")
    assert malformed.status_code == 422

    absent = "sha256:" + "0" * 64
    response = http.get(f"/api/v1/intake/research-drafts/{absent}/missing")
    assert response.status_code == 404

    invalid_confirmation = http.post(
        f"/api/v1/intake/research-drafts/{absent}/confirm",
        json={
            "expected_normalized_checksum": absent,
            "expected_artifact_checksum": absent,
            "actor_id": "researcher",
            "decision": "approve",
            "acknowledged_warning_codes": ["z", "a", "a"],
        },
    )
    assert invalid_confirmation.status_code == 422


def test_store_supports_incomplete_gene_and_objective_entry_without_invention(client):
    http, _ = client
    gene = _store(
        http,
        input_method="gene",
        content=None,
        molecule_type=None,
        gene_symbol="BRCA2",
    )
    objective = _store(
        http,
        input_method="objective",
        content="Study a user-written editing objective",
        molecule_type=None,
    )

    assert gene.status_code == 201
    assert gene.json()["draft"]["records"] == []
    assert gene.json()["draft"]["ready_for_confirmation"] is False
    assert objective.status_code == 201
    assert objective.json()["draft"]["records"] == []
    assert "Study a user-written" not in objective.text
