"""Exact local reference-resolution tests; no network or implicit selection."""

import gzip

import pytest
from pydantic import ValidationError

from app.modules.information_processor.contracts import checksum
from app.modules.information_processor.dataset_parser import process_vcf
from app.modules.information_processor.intake import VcfInspectionRequest, inspect_input
from app.modules.information_processor.parser import InputValidationError
from app.modules.information_processor.references import (
    ReferenceDraft,
    SuppliedReferenceRequest,
    resolve_supplied_reference,
    verify_variant_reference,
)

REFERENCE = b">chr1 chromosome one\r\nacgt\r\n>chr2\nTTAA\n"
VCF = (
    b"##fileformat=VCFv4.3\n"
    b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
    b"chr1\t2\trs1\tC\tT\t50\tPASS\tDP=12\n"
)


def _error(function, expected, *args, **kwargs):
    with pytest.raises(InputValidationError) as error:
        function(*args, **kwargs)
    assert error.value.issue.code == expected
    return error.value.issue


def test_resolver_preserves_exact_artifact_and_builds_contig_identity():
    draft = resolve_supplied_reference(
        SuppliedReferenceRequest(
            content=REFERENCE,
            filename="GRCh-demo.fa",
            assembly="GRCh-demo",
            accession_version="GCF_000001405.40",
        )
    )

    assert draft.artifact.content == REFERENCE
    assert draft.artifact.filename == "GRCh-demo.fa"
    assert draft.artifact.checksum == checksum(REFERENCE)
    assert draft.assembly.value == "GRCh-demo"
    assert draft.assembly.confirmed is False
    assert draft.accession_version.value == "GCF_000001405.40"
    assert [contig.record_id for contig in draft.contigs] == ["chr1", "chr2"]
    assert [contig.sequence_length for contig in draft.contigs] == [4, 4]
    assert draft.missing_fields == ()
    assert draft.ready_for_confirmation is True
    assert draft.executable is False


def test_reference_sequence_identity_ignores_order_case_and_line_endings():
    first = resolve_supplied_reference(
        SuppliedReferenceRequest(content=b">chr1\nACGT\n>chr2\nTTAA\n", assembly="demo")
    )
    second = resolve_supplied_reference(
        SuppliedReferenceRequest(content=b">chr2\r\nttaa\r\n>chr1\r\nacgt", assembly="demo")
    )

    assert first.artifact.checksum != second.artifact.checksum
    assert first.sequence_checksum == second.sequence_checksum
    assert first.contigs[0].sequence_checksum == checksum(b"ACGT")


def test_missing_reference_identity_remains_explicit_and_unconfirmed():
    draft = resolve_supplied_reference(SuppliedReferenceRequest(content=b">chr1\nACGT\n"))

    assert draft.assembly.value is None
    assert draft.accession_version.value is None
    assert {field.field: field.requirement for field in draft.missing_fields} == {
        "reference_assembly": "required",
        "reference_accession_version": "recommended",
    }
    assert draft.ready_for_confirmation is False
    assert "reference_identity_unconfirmed" in {warning.code for warning in draft.warnings}


@pytest.mark.parametrize("accession", ["NC_000001", "NC_000001.", "NC 000001.1", ".1"])
def test_accession_requires_an_exact_numeric_version(accession):
    with pytest.raises(ValidationError, match="exact numeric version"):
        SuppliedReferenceRequest(content=b">chr1\nACGT\n", accession_version=accession)


@pytest.mark.parametrize(
    "content, filename, code",
    [
        (
            gzip.compress(b">chr1\nACGT\n", mtime=0),
            "reference.fa.gz",
            "unsupported_reference_compression",
        ),
        (b">chr1\nACGT\n", "reference.fa.gz", "compression_mismatch"),
        (b">chr1\nACGT\n>chr1\nTTAA\n", "reference.fa", "duplicate_identifier"),
        (b">chr1\nACGU\n", "reference.fa", "invalid_alphabet"),
    ],
)
def test_ambiguous_or_unsupported_references_are_rejected(content, filename, code):
    _error(
        resolve_supplied_reference,
        code,
        SuppliedReferenceRequest(content=content, filename=filename),
    )


def test_expected_artifact_and_sequence_checksums_are_enforced():
    original = resolve_supplied_reference(
        SuppliedReferenceRequest(content=b">chr1\nACGT\n", assembly="demo")
    )
    repeated = resolve_supplied_reference(
        SuppliedReferenceRequest(
            content=b">chr1\nACGT\n",
            assembly="demo",
            expected_artifact_checksum=original.artifact.checksum,
            expected_sequence_checksum=original.sequence_checksum,
        )
    )
    assert repeated == original

    wrong = "sha256:" + "0" * 64
    _error(
        resolve_supplied_reference,
        "reference_artifact_checksum_mismatch",
        SuppliedReferenceRequest(
            content=b">chr1\nACGT\n", expected_artifact_checksum=wrong
        ),
    )
    _error(
        resolve_supplied_reference,
        "reference_sequence_checksum_mismatch",
        SuppliedReferenceRequest(
            content=b">chr1\nACGT\n", expected_sequence_checksum=wrong
        ),
    )


def test_variant_verification_returns_exact_reference_evidence():
    reference = resolve_supplied_reference(
        SuppliedReferenceRequest(content=b">chr1\nACGT\n", assembly="demo")
    )
    draft = process_vcf(VCF)
    verification = verify_variant_reference(reference, draft.variants)

    assert verification.reference_artifact_checksum == reference.artifact.checksum
    assert verification.reference_sequence_checksum == reference.sequence_checksum
    assert verification.checked_variant_count == 1


def test_vcf_parser_uses_resolver_and_preserves_reference_filename():
    draft = process_vcf(
        VCF,
        reference_content=b">chr1\nACGT\n",
        reference_filename="selected-reference.fa",
        reference_assembly="demo",
    )
    assert draft.reference_checked is True
    assert draft.artifacts[1].filename == "selected-reference.fa"

    duplicate = b">chr1\nACGT\n>chr1\nACGT\n"
    _error(process_vcf, "duplicate_identifier", VCF, reference_content=duplicate)


def test_intake_dispatch_routes_reference_filename_and_normalizes_rejection():
    accepted = inspect_input(
        VcfInspectionRequest(
            content=VCF,
            reference_content=b">chr1\nACGT\n",
            reference_filename="chosen.fa",
            reference_assembly="demo",
        )
    )
    assert accepted.outcome == "accepted"
    assert accepted.draft is not None
    assert accepted.draft.artifacts[1].filename == "chosen.fa"

    rejected = inspect_input(
        VcfInspectionRequest(
            content=VCF,
            reference_content=b">chr1\nAAGT\n",
            reference_filename="wrong.fa",
            reference_assembly="demo",
        )
    )
    assert rejected.outcome == "rejected"
    assert rejected.issue is not None
    assert rejected.issue.code == "reference_mismatch"


def test_reference_filename_without_bytes_is_rejected_by_intake_contract():
    with pytest.raises(ValidationError, match="reference_filename requires reference_content"):
        VcfInspectionRequest(content=VCF, reference_filename="orphan.fa")


def test_reference_draft_roundtrip_revalidates_exact_contract():
    draft = resolve_supplied_reference(
        SuppliedReferenceRequest(
            content=REFERENCE,
            assembly="demo",
            accession_version="NC_000001.11",
        )
    )
    decoded = ReferenceDraft.model_validate_json(draft.model_dump_json(round_trip=True))
    assert decoded == draft


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda data: data.update(sequence_checksum="sha256:" + "0" * 64),
            "sequence checksum",
        ),
        (
            lambda data: data["contigs"][0].update(sequence_length=99),
            "contig identities",
        ),
        (
            lambda data: data.update(missing_fields=[]),
            "required missing field",
        ),
    ],
)
def test_reference_draft_rejects_forged_identity_fields(mutation, message):
    draft = resolve_supplied_reference(SuppliedReferenceRequest(content=b">chr1\nACGT\n"))
    data = draft.model_dump(round_trip=True)
    mutation(data)
    with pytest.raises(ValidationError, match=message):
        ReferenceDraft.model_validate(data)
