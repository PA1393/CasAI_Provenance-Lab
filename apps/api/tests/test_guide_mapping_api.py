"""Guide-map API derives plans only from exact confirmed DNA records."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_intake_workspace
from app.main import app
from app.modules.information_processor.workspace import LocalWorkspace

GUIDE = "AAACACAAAAAAAAAAAAAA"
SEQUENCE = "TTTT" + GUIDE + "AGG" + "TTTT"


@pytest.mark.parametrize("sequence,code", [
    ("A" * 5_001, "target_length_limit"),
    (SEQUENCE * 65, "candidate_count_limit"),
])
def test_mapping_limits_are_visible_without_partial_results(client, sequence, code):
    http, workspace = client
    confirmed = _confirmed(http, content=f">target\n{sequence}\n")
    response = http.post("/api/v1/guide-maps", json=_request(
        confirmed["version_id"], desired_edits=[],
    ))
    assert response.status_code == 201
    body = response.json()
    assert body["candidates"] == []
    assert body["executable"] is False
    assert [issue["code"] for issue in body["issues"]] == [code]
    assert workspace.load_guide_map(body["map_id"]).candidates == ()
    assert workspace.load_guide_ranking(body["ranking_id"]).assessments == ()


@pytest.fixture
def client(tmp_path):
    workspace = LocalWorkspace(tmp_path / "workspace")
    app.dependency_overrides[get_intake_workspace] = lambda: workspace
    try:
        yield TestClient(app), workspace
    finally:
        app.dependency_overrides.pop(get_intake_workspace, None)


def _confirmed(client, *, molecule_type="DNA", content=None):
    stored = client.post(
        "/api/v1/intake/research-drafts",
        json={
            "input_method": "fasta",
            "content": content or f">target\n{SEQUENCE}\n",
            "molecule_type": molecule_type,
        },
    ).json()
    draft = stored["draft"]
    confirmed = client.post(
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
    assert confirmed.status_code == 201
    return confirmed.json()


def _request(version_id, **changes):
    body = {
        "source_version_id": version_id,
        "source_record_id": "target",
        "editor": "CBE",
        "desired_edits": [{"position": 8, "reference": "C", "alternate": "T"}],
    }
    body.update(changes)
    return body


def test_create_guide_map_returns_ranked_bounded_summary_and_persists(client):
    http, workspace = client
    confirmed = _confirmed(http)
    response = http.post("/api/v1/guide-maps", json=_request(confirmed["version_id"]))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["executable"] is False
    assert body["source_version_id"] == confirmed["version_id"]
    candidate = next(item for item in body["candidates"] if item["guide_rna"] == GUIDE)
    assert candidate["desired_edit_positions"] == [8]
    assert candidate["bystander_positions"] == [10]
    assert candidate["rank"] >= 1
    assert len(candidate["components"]) == 5
    assert SEQUENCE not in response.text
    assert workspace.load_guide_map(body["map_id"]).map_id == body["map_id"]
    assert workspace.load_guide_ranking(body["ranking_id"]).ranking_id == body["ranking_id"]


def test_repeating_the_same_request_returns_same_content_addresses(client):
    http, _ = client
    version_id = _confirmed(http)["version_id"]
    first = http.post("/api/v1/guide-maps", json=_request(version_id))
    second = http.post("/api/v1/guide-maps", json=_request(version_id))

    assert first.status_code == second.status_code == 201
    assert first.json()["map_id"] == second.json()["map_id"]
    assert first.json()["ranking_id"] == second.json()["ranking_id"]


def test_missing_version_record_and_non_dna_source_are_rejected(client):
    http, _ = client
    absent = "sha256:" + "0" * 64
    missing_version = http.post("/api/v1/guide-maps", json=_request(absent))
    assert missing_version.status_code == 404

    version_id = _confirmed(http)["version_id"]
    missing_record = http.post(
        "/api/v1/guide-maps",
        json=_request(version_id, source_record_id="absent"),
    )
    assert missing_record.status_code == 422

    protein = _confirmed(
        http,
        molecule_type="protein",
        content=">target\nACGTACGTACGTACGTACGTAGG\n",
    )
    non_dna = http.post("/api/v1/guide-maps", json=_request(protein["version_id"]))
    assert non_dna.status_code == 422
    assert "confirmed DNA" in non_dna.json()["detail"]


def test_desired_reference_mismatch_and_invalid_window_are_rejected(client):
    http, _ = client
    version_id = _confirmed(http)["version_id"]
    mismatch = http.post(
        "/api/v1/guide-maps",
        json=_request(
            version_id,
            desired_edits=[{"position": 8, "reference": "A", "alternate": "G"}],
        ),
    )
    assert mismatch.status_code == 422
    assert "reference" in mismatch.json()["detail"]

    invalid_window = http.post(
        "/api/v1/guide-maps",
        json=_request(version_id, edit_window=[0, 8]),
    )
    assert invalid_window.status_code == 422


def test_no_compatible_site_remains_a_saved_non_executable_result(client):
    http, _ = client
    confirmed = _confirmed(http, content=">target\n" + "A" * 60 + "\n")
    response = http.post(
        "/api/v1/guide-maps",
        json=_request(confirmed["version_id"], desired_edits=[]),
    )

    assert response.status_code == 201
    assert response.json()["candidates"] == []
    assert response.json()["issues"][0]["code"] == "no_compatible_guide"
