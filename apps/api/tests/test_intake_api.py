"""HTTP intake boundary tests; responses must never expose original biological payloads."""

from fastapi.testclient import TestClient

from app.main import app
from app.modules.information_processor.contracts import MAX_INPUT_BYTES

client = TestClient(app)
VCF = (
    b"##fileformat=VCFv4.3\n"
    b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
    b"chr1\t2\trs1\tC\tT\t50\tPASS\tDP=12\n"
)


def test_sequence_endpoint_returns_summary_without_raw_sequence():
    response = client.post(
        "/api/v1/intake/sequences/inspect",
        json={
            "declared_format": "fasta",
            "content": ">source\nACGT\n",
            "molecule_type": "DNA",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "accepted"
    assert body["draft"]["kind"] == "sequence"
    assert body["draft"]["records"][0]["sequence_length"] == 4
    assert "ACGT" not in response.text
    assert "content" not in body["draft"]


def test_sequence_endpoint_maps_parser_rejection_and_request_validation():
    rejected = client.post(
        "/api/v1/intake/sequences/inspect",
        json={"declared_format": "fasta", "content": ">bad\nACGU\n", "molecule_type": "DNA"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["issue"]["code"] == "invalid_alphabet"

    invalid = client.post(
        "/api/v1/intake/sequences/inspect",
        json={"declared_format": "unknown", "content": "ACGT"},
    )
    assert invalid.status_code == 422

def test_fastq_endpoint_accepts_pairs_and_omits_reads_and_qualities():
    response = client.post(
        "/api/v1/intake/datasets/inspect",
        data={
            "declared_format": "fastq",
            "sample_id": "sample-a",
            "quality_encoding": "phred33",
        },
        files={
            "primary": ("../r1.fastq", b"@r/1\nAC\n+\nII\n", "application/octet-stream"),
            "mate": ("r2.fastq", b"@r/2\nGT\n+\n##\n", "application/octet-stream"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["record_count"] == 2
    assert [item["filename"] for item in body["draft"]["artifacts"]] == [
        "r1.fastq",
        "r2.fastq",
    ]
    assert "qualities" not in response.text
    assert "@r/1" not in response.text


def test_vcf_endpoint_checks_exact_reference_and_preserves_safe_labels():
    response = client.post(
        "/api/v1/intake/datasets/inspect",
        data={"declared_format": "vcf", "reference_assembly": "demo"},
        files={
            "primary": ("variants.vcf", VCF, "text/plain"),
            "reference": ("folder/reference.fa", b">chr1\nACGT\n", "text/plain"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["reference_checked"] is True
    assert body["draft"]["artifacts"][1]["filename"] == "reference.fa"
    assert "DP=12" not in response.text

    mismatch = client.post(
        "/api/v1/intake/datasets/inspect",
        data={"declared_format": "vcf", "reference_assembly": "demo"},
        files={
            "primary": ("variants.vcf", VCF, "text/plain"),
            "reference": ("reference.fa", b">chr1\nAAGT\n", "text/plain"),
        },
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["issue"]["code"] == "reference_mismatch"


def test_dataset_endpoint_rejects_cross_format_options():
    response = client.post(
        "/api/v1/intake/datasets/inspect",
        data={"declared_format": "fastq", "reference_assembly": "not-applicable"},
        files={"primary": ("reads.fastq", b"@r\nAC\n+\nII\n")},
    )
    assert response.status_code == 400
    assert response.json()["issue"]["code"] == "incompatible_inputs"

    unsafe_name = client.post(
        "/api/v1/intake/datasets/inspect",
        data={"declared_format": "fastq"},
        files={"primary": ("x" * 256 + ".fastq", b"@r\nAC\n+\nII\n")},
    )
    assert unsafe_name.status_code == 400
    assert unsafe_name.json()["issue"]["code"] == "invalid_filename"


def test_upload_limit_returns_413_without_partial_draft():
    response = client.post(
        "/api/v1/intake/datasets/inspect",
        data={"declared_format": "fastq"},
        files={"primary": ("large.fastq", b"A" * (MAX_INPUT_BYTES + 1))},
    )
    assert response.status_code == 413
    body = response.json()
    assert body["outcome"] == "rejected"
    assert body["issue"]["code"] == "input_too_large"
    assert body["draft"] is None


def test_reference_endpoint_returns_manifest_without_reference_bases():
    response = client.post(
        "/api/v1/intake/references/verify",
        data={"assembly": "demo", "accession_version": "NC_000001.11"},
        files={"reference": ("reference.fa", b">chr1\nACGT\n", "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["contigs"][0]["sequence_length"] == 4
    assert body["draft"]["artifact"]["filename"] == "reference.fa"
    assert "ACGT" not in response.text


def test_reference_endpoint_maps_invalid_selection_and_checksum_mismatch():
    invalid = client.post(
        "/api/v1/intake/references/verify",
        data={"accession_version": "NC_000001"},
        files={"reference": ("reference.fa", b">chr1\nACGT\n")},
    )
    assert invalid.status_code == 422
    assert invalid.json()["issue"]["code"] == "invalid_reference_selection"

    mismatch = client.post(
        "/api/v1/intake/references/verify",
        data={"expected_artifact_checksum": "sha256:" + "0" * 64},
        files={"reference": ("reference.fa", b">chr1\nACGT\n")},
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["issue"]["code"] == "reference_artifact_checksum_mismatch"
