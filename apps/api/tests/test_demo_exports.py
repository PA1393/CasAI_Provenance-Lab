import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.runs import export as service


@pytest.fixture
def snapshot(monkeypatch):
    run = {"run_id": "r1", "research_object_id": "input1", "created_at": "2026-10-23",
           "prompt": "Demo", "status": "completed", "started_at": None,
           "completed_at": None, "secret": "NEVER_EXPORT"}
    source = {"research_object_id": "input1", "created_at": "2026-10-23", "name": "Demo",
              "input_filename": "../../user.fa", "input_file_type": "fasta", "pdb_id": "",
              "ro_hash": "sha256:example", "status": "ready", "sequence": "ACGT",
              "service_key": "NEVER_EXPORT"}
    monkeypatch.setattr(service, "get_run", lambda _: run)
    monkeypatch.setattr(service, "get_research_object", lambda _: source)
    monkeypatch.setattr(service, "list_results", lambda _: [])
    monkeypatch.setattr(service, "list_provenance_events", lambda _: [])
    return run, source


def test_snapshot_is_deterministic_checksummed_and_allowlisted(snapshot):
    first = service.build_run_export("r1")
    assert first == service.build_run_export("r1")
    assert "NEVER_EXPORT" not in json.dumps(first)
    assert first["rights"]["commercial_reuse_authorized"] is False
    assert {file["path"] for file in first["files"]} == {
        "input.json", "results.json", "provenance.json", "run.json",
    }
    for file in first["files"]:
        encoded = file["content"].encode("utf-8")
        assert file["byte_length"] == len(encoded)
        assert file["sha256"] == hashlib.sha256(encoded).hexdigest()
        json.loads(file["content"])


def test_export_http_missing_running_and_terminal(snapshot, monkeypatch):
    client = TestClient(app)
    assert client.get("/api/v1/runs/r1/export").status_code == 200
    snapshot[0]["status"] = "running"
    assert client.get("/api/v1/runs/r1/export").status_code == 409
    snapshot[0]["status"] = "failed"
    assert client.get("/api/v1/runs/r1/export").status_code == 200
    monkeypatch.setattr(service, "get_run", lambda _: None)
    assert client.get("/api/v1/runs/missing/export").status_code == 404


def test_export_never_silently_truncates(snapshot, monkeypatch):
    monkeypatch.setattr(service, "MAX_EXPORT_BYTES", 5)
    with pytest.raises(ValueError, match="size limit"):
        service.build_run_export("r1")
