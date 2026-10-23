import hashlib

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_intake_workspace
from app.main import app
from app.modules.information_processor import handoff
from app.modules.information_processor.workspace import LocalWorkspace
from app.modules.research_objects import service as research_service

client = TestClient(app)


@pytest.fixture
def context(tmp_path, monkeypatch):
    workspace = LocalWorkspace(tmp_path / "workspace")
    rows = {}
    app.dependency_overrides[get_intake_workspace] = lambda: workspace

    class Database:
        def table(self, name):
            assert name == "research_objects"
            return self

        def insert(self, payload):
            self.payload = payload
            return self

        def execute(self):
            row = {"created_at": "2026-10-23", **self.payload}
            rows[row["research_object_id"]] = row
            return type("Response", (), {"data": [row]})()

    monkeypatch.setattr(research_service, "get_supabase", Database)
    monkeypatch.setattr(handoff, "get_research_object", rows.get)
    try:
        yield workspace, rows
    finally:
        app.dependency_overrides.clear()


def confirmed(content, molecule="DNA", convert=False):
    response = client.post("/api/v1/intake/research-drafts", json={
        "input_method": "fasta", "content": content,
        "molecule_type": molecule, "rna_to_dna": convert,
    })
    assert response.status_code == 201
    body = response.json()
    result = client.post(f"/api/v1/intake/research-drafts/{body['draft_id']}/confirm", json={
        "expected_normalized_checksum": body["draft"]["normalized_checksum"],
        "expected_artifact_checksum": body["draft"]["artifact_checksum"],
        "actor_id": "synthetic-test-reviewer", "decision": "approve",
        "acknowledged_warning_codes": sorted({w["code"] for w in body["draft"]["warnings"]}),
    })
    assert result.status_code == 201
    return result.json()["version_id"], body["draft_id"]


def test_download_preserves_all_records_and_checksums(context):
    version, _ = confirmed(
        ">first description\nacgtacgt\n>second\nTTTTAAACAAAAAAAAAAAAAAAAAGGTTTT\n"
    )
    response = client.get(f"/api/v1/intake/confirmed-versions/{version}/fasta")
    assert response.status_code == 200
    body = response.json()
    assert body["record_count"] == 2
    content = body["content"]
    assert content.startswith(">first ") and "\n>second " in content
    assert "\nACGTACGT\n" in content
    assert f"casai_version={version}" in content
    assert body["checksum"] == "sha256:" + hashlib.sha256(content.encode()).hexdigest()
    assert body["byte_length"] == len(content.encode())
    assert "source_checksum=" in content and "record_checksum=" in content


def test_use_in_run_selects_exact_record_and_reopens_without_duplicates(context):
    _, rows = context
    version, _ = confirmed(">first\nACGTACGT\n>second\nTTTTAAACAAAAAAAAAAAAAAAAAGGTTTT\n")
    path = f"/api/v1/intake/confirmed-versions/{version}/research-objects"
    result = client.post(path, json={"record_id": "second", "name": "My confirmed input"})
    assert result.status_code == 200
    row = result.json()
    assert row["sequence"] == "TTTTAAACAAAAAAAAAAAAAAAAAGGTTTT"
    assert row["sequence_length"] == 31
    assert row["confirmed_version_id"] == version
    assert row["confirmed_record_id"] == "second"
    assert len(rows) == 1
    again = client.post(path, json={"record_id": "second", "name": "Changed label"})
    assert again.json() == row
    assert len(rows) == 1
    missing = client.post(path, json={"record_id": "missing", "name": "No"})
    assert missing.status_code == 422 and len(rows) == 1
    # A modified existing research object may never silently replace confirmed bytes.
    rows[row["research_object_id"]]["sequence"] = "AAAA"
    assert client.post(path, json={"record_id": "second", "name": "Again"}).status_code == 422


@pytest.mark.parametrize("molecule, sequence", [("RNA", "ACGU"), ("protein", "MKWV"),
                                                ("DNA", "ACNT"), ("DNA", "A" * 5001)])
def test_non_runnable_records_can_download_but_never_prepare_a_run(context, molecule, sequence):
    version, _ = confirmed(f">record\n{sequence}\n", molecule)
    assert client.get(f"/api/v1/intake/confirmed-versions/{version}/fasta").status_code == 200
    response = client.post(f"/api/v1/intake/confirmed-versions/{version}/research-objects",
                           json={"record_id": "record", "name": "Unsupported"})
    assert response.status_code == 422
    assert not context[1]


def test_explicit_rna_conversion_and_missing_confirmed_versions(context):
    version, draft_id = confirmed(">record\nACGUACGU\n", "RNA", True)
    response = client.post(f"/api/v1/intake/confirmed-versions/{version}/research-objects",
                           json={"record_id": "record", "name": "Explicit conversion"})
    assert response.status_code == 200 and response.json()["sequence"] == "ACGTACGT"
    assert client.get(f"/api/v1/intake/confirmed-versions/{draft_id}/fasta").status_code == 404
    assert client.get("/api/v1/intake/confirmed-versions/not-a-hash/fasta").status_code == 422


def test_database_failures_are_sanitized_and_do_not_submit_runs(context, monkeypatch):
    version, _ = confirmed(">record\nACGT\n")

    def broken(_):
        raise RuntimeError("private database credential must not leak")

    monkeypatch.setattr(handoff, "create_research_object", broken)
    response = client.post(f"/api/v1/intake/confirmed-versions/{version}/research-objects",
                           json={"record_id": "record", "name": "Unavailable"})
    assert response.status_code == 503
    assert "credential" not in response.text and "migration 007" in response.text
