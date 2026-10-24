from fastapi.testclient import TestClient

from app.api.dependencies import get_intake_workspace
from app.main import app
from app.modules.information_processor.workspace import LocalWorkspace

client = TestClient(app)


def test_text_fastq_and_vcf_remain_evidence_only():
    response = client.post("/api/v1/intake/datasets/inspect-text", json={
        "declared_format": "fastq", "filename": "reads.fastq", "content": "@r\nAC\n+\nII\n",
        "quality_encoding": "phred33",
    })
    assert response.status_code == 200
    draft = response.json()["draft"]
    assert draft["data_role"] == "reads"
    assert draft["record_count"] == 1
    assert draft["executable"] is False
    assert "content" not in draft
    response = client.post("/api/v1/intake/datasets/inspect-text", json={
        "declared_format": "vcf", "filename": "variants.vcf", "content":
        "##fileformat=VCFv4.3\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "chr1\t2\t.\tC\tT\t50\tPASS\t.\n",
        "reference_content": ">chr1\nACGT\n", "reference_assembly": "synthetic-demo",
    })
    assert response.status_code == 200
    assert response.json()["draft"]["reference_checked"] is True


def test_desktop_evidence_rejects_paths_and_incompatible_options():
    base = {"declared_format": "vcf", "filename": "../escape", "content": "bad"}
    assert client.post("/api/v1/intake/datasets/inspect-text", json=base).status_code == 422
    base.update(filename="input.vcf", quality_encoding="phred33")
    assert client.post("/api/v1/intake/datasets/inspect-text", json=base).status_code == 422


def test_stored_draft_can_resume_without_returning_raw_sequence(tmp_path):
    workspace = LocalWorkspace(tmp_path / "workspace")
    app.dependency_overrides[get_intake_workspace] = lambda: workspace
    try:
        response = client.post("/api/v1/intake/research-drafts", json={
            "input_method": "pasted_sequence", "content": "ACGT", "molecule_type": "DNA",
        })
        assert response.status_code == 201
        identity = response.json()["draft_id"]
        reopened = client.get(f"/api/v1/intake/research-drafts/{identity}")
        assert reopened.status_code == 200
        assert reopened.json() == response.json()
        assert "ACGT" not in reopened.text
        assert reopened.json()["draft"]["field_origins"]
    finally:
        app.dependency_overrides.clear()
