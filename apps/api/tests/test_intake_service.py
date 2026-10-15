"""Transport-neutral orchestration tests; no HTTP, persistence or provider calls."""

import pytest
from pydantic import ValidationError

from app.modules.information_processor.contracts import ProcessingNotice, ResearchDraft
from app.modules.information_processor.dataset_parser import DatasetLimits
from app.modules.information_processor.datasets import DatasetDraft
from app.modules.information_processor.intake import (
    FastqInspectionRequest,
    IntakeInspection,
    SequenceInspectionRequest,
    VcfInspectionRequest,
    inspect_input,
)

FASTQ_LEFT = b"@r/1\nAC\n+\nII\n"
FASTQ_RIGHT = b"@r/2\nGT\n+\n##\n"
VCF = (
    b"##fileformat=VCFv4.3\n"
    b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
    b"chr1\t2\trs1\tC\tT\t50\tPASS\tDP=12\n"
)


@pytest.mark.parametrize("declared_format", ["fasta", "pasted_sequence"])
def test_sequence_dispatch_preserves_exact_bytes_and_metadata(declared_format):
    content = b">source\r\nacgt\r\n" if declared_format == "fasta" else b"ac gt\r\n"
    result = inspect_input(
        SequenceInspectionRequest(
            declared_format=declared_format,
            content=content,
            molecule_type="DNA",
            organism="synthetic organism",
        )
    )

    assert result.outcome == "accepted"
    assert result.issue is None
    assert isinstance(result.draft, ResearchDraft)
    assert result.draft.original_artifact.content == content
    assert result.draft.records[0].sequence.value == "ACGT"
    assert result.draft.organism.value == "synthetic organism"
    assert result.draft.executable is False


def test_fastq_dispatch_routes_pairing_metadata_and_limits():
    result = inspect_input(
        FastqInspectionRequest(
            content=FASTQ_LEFT,
            filename="sample-r1.fastq",
            mate_content=FASTQ_RIGHT,
            mate_filename="sample-r2.fastq",
            sample_id="sample-a",
            quality_encoding="phred33",
            limits=DatasetLimits(max_records=1),
        )
    )

    assert result.outcome == "accepted"
    assert isinstance(result.draft, DatasetDraft)
    assert [artifact.filename for artifact in result.draft.artifacts] == [
        "sample-r1.fastq",
        "sample-r2.fastq",
    ]
    assert [read.mate for read in result.draft.reads] == [1, 2]
    assert result.draft.sample_id.value == "sample-a"
    assert result.draft.executable is False


def test_vcf_dispatch_routes_exact_reference_for_existing_validation():
    result = inspect_input(
        VcfInspectionRequest(
            content=VCF,
            filename="sample.vcf",
            sample_id="sample-a",
            reference_assembly="synthetic-v1",
            reference_content=b">chr1\nACGT\n",
        )
    )

    assert result.outcome == "accepted"
    assert isinstance(result.draft, DatasetDraft)
    assert result.draft.reference_checked is True
    assert result.draft.reference_assembly.value == "synthetic-v1"
    assert result.draft.variants[0].reference == "C"


@pytest.mark.parametrize(
    "inspection_request, code, record_id",
    [
        (
            SequenceInspectionRequest(
                declared_format="fasta", content=b"\xff", molecule_type="DNA"
            ),
            "invalid_encoding",
            None,
        ),
        (FastqInspectionRequest(content=b"@broken\nAC\n"), "truncated_fastq", "line:1"),
        (
            VcfInspectionRequest(
                content=VCF,
                reference_assembly="synthetic-v1",
                reference_content=b">chr1\nAAGT\n",
            ),
            "reference_mismatch",
            None,
        ),
    ],
)
def test_expected_parser_failures_become_one_structured_rejection(
    inspection_request, code, record_id
):
    result = inspect_input(inspection_request)

    assert result.outcome == "rejected"
    assert result.draft is None
    assert result.issue is not None
    assert result.issue.code == code
    assert result.issue.record_id == record_id


def test_request_contract_rejects_mate_filename_without_mate_bytes():
    with pytest.raises(ValidationError, match="mate_filename requires mate_content"):
        FastqInspectionRequest(content=FASTQ_LEFT, mate_filename="orphan.fastq")


def test_result_contract_prevents_forged_or_mismatched_outcomes():
    issue = ProcessingNotice(code="rejected", message="rejected")
    with pytest.raises(ValidationError, match="Accepted inspection requires only a draft"):
        IntakeInspection(declared_format="fastq", outcome="accepted", issue=issue)

    accepted = inspect_input(FastqInspectionRequest(content=FASTQ_LEFT))
    assert accepted.draft is not None
    with pytest.raises(ValidationError, match="Inspection format must match"):
        IntakeInspection(
            declared_format="vcf",
            outcome="accepted",
            draft=accepted.draft,
        )


@pytest.mark.parametrize(
    "inspection_request",
    [
        SequenceInspectionRequest(
            declared_format="fasta", content=b">source\nACGT\n", molecule_type="DNA"
        ),
        FastqInspectionRequest(content=FASTQ_LEFT),
        VcfInspectionRequest(content=VCF),
        FastqInspectionRequest(content=b"not-fastq"),
    ],
)
def test_inspection_result_json_roundtrip_is_immutable(inspection_request):
    result = inspect_input(inspection_request)
    decoded = IntakeInspection.model_validate_json(result.model_dump_json(round_trip=True))
    assert decoded == result


def test_sequence_limit_is_routed_to_existing_parser():
    result = inspect_input(
        SequenceInspectionRequest(
            declared_format="pasted_sequence",
            content=b"ACGT",
            molecule_type="DNA",
            max_bytes=3,
        )
    )
    assert result.outcome == "rejected"
    assert result.issue is not None
    assert result.issue.code == "input_too_large"
