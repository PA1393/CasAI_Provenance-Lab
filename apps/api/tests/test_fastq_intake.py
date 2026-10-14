"""Offline FASTQ and shared dataset-contract tests; VCF/CLI arrive in later PRs."""

import gzip

import pytest
from pydantic import ValidationError

from app.modules.information_processor.contracts import checksum
from app.modules.information_processor.dataset_parser import (
    DatasetLimits,
    detect_dataset,
    process_fastq,
)
from app.modules.information_processor.datasets import (
    DatasetDraft,
    ReadRecord,
    SampleCall,
    VariantRecord,
)
from app.modules.information_processor.parser import InputValidationError

FASTQ = b"@r1 label\nacgt\n+\n!I@+\n@r2\nNN\n+\n##\n"


def _error(function, expected, *args, **kwargs):
    with pytest.raises(InputValidationError) as error:
        function(*args, **kwargs)
    assert error.value.issue.code == expected
    return error.value.issue


@pytest.mark.parametrize("compressed", [False, True])
def test_fastq_preserves_original_reads_qualities_and_declared_encoding(compressed):
    content = gzip.compress(FASTQ, mtime=0) if compressed else FASTQ
    draft = process_fastq(
        content, filename="input", sample_id="sample-a", quality_encoding="phred33"
    )
    assert draft.data_role == "reads"
    assert [r.sequence for r in draft.reads] == ["ACGT", "NN"]
    assert [r.qualities for r in draft.reads] == ["!I@+", "##"]
    assert draft.reads[0].description == "label"
    assert draft.artifacts[0].content == content
    assert draft.artifacts[0].checksum == checksum(content)
    assert draft.artifacts[0].compression == ("gzip" if compressed else "none")
    assert draft.reads[0].source == f"{checksum(content)}#record:1"
    assert draft.quality_encoding.value == "phred33"
    assert draft.quality_encoding.origin == "user_supplied"
    assert draft.quality_encoding.confirmed is False
    assert draft.missing_fields == ()
    assert draft.variants == ()
    assert draft.record_count == 2
    assert draft.executable is False


def test_fastq_without_metadata_preserves_unknown_quality_dialect():
    draft = process_fastq(FASTQ)
    assert {field.field for field in draft.missing_fields} == {"sample_id", "quality_encoding"}
    assert draft.quality_encoding.value is None
    assert draft.quality_encoding.origin == "unresolved"
    _error(process_fastq, "unsupported_quality_encoding", FASTQ, quality_encoding="phred64")


def test_wrapped_fastq_quality_markers_and_identifier_repeat():
    draft = process_fastq(b"@r description\r\nac\r\ngt\r\n+r\r\n@+\r\n!!")
    assert draft.reads[0].sequence == "ACGT"
    assert draft.reads[0].qualities == "@+!!"


@pytest.mark.parametrize("suffix", [True, False])
def test_paired_fastq_validates_identity_and_keeps_mates_separate(suffix):
    left = b"@r/1\nAC\n+\nII\n" if suffix else b"@r 1:N:0:X\nAC\n+\nII\n"
    right = b"@r/2\nGT\n+\n##\n" if suffix else b"@r 2:N:0:X\nGT\n+\n##\n"
    draft = process_fastq(left, mate_content=gzip.compress(right, mtime=0))
    assert [r.mate for r in draft.reads] == [1, 2]
    assert [r.sequence for r in draft.reads] == ["AC", "GT"]
    assert [a.role for a in draft.artifacts] == ["reads", "mate_reads"]
    assert draft.record_count == 2


@pytest.mark.parametrize(
    "right, code",
    [
        (b"@other/2\nAC\n+\nII\n", "mate_identifier_mismatch"),
        (b"@r/1\nAC\n+\nII\n", "mate_direction_mismatch"),
        (b"@r/2 1:N:0:X\nAC\n+\nII\n", "mate_direction_mismatch"),
        (b"@r/2\nAC\n+\nII\n@extra/2\nGT\n+\nII\n", "mate_count_mismatch"),
    ],
)
def test_invalid_mates_are_rejected(right, code):
    _error(process_fastq, code, b"@r/1\nAC\n+\nII\n", mate_content=right)


@pytest.mark.parametrize(
    "content, code",
    [
        (b"", "empty_input"),
        (b"\n", "invalid_fastq_header"),
        (b">r\nAC\n+\nII\n", "invalid_fastq_header"),
        (b"@ \nAC\n+\nII\n", "invalid_fastq_header"),
        (b"@r\n+\n", "empty_record"),
        (b"@r\nAC\n", "truncated_fastq"),
        (b"@r\nAC\n+\nI", "truncated_fastq"),
        (b"@r\nAC\n+\nIII\n", "quality_length_mismatch"),
        (b"@r\nAC\n+other\nII\n", "fastq_identifier_mismatch"),
        (b"@r\nAC\n+\nI \n", "invalid_quality"),
        (b"@r\nA U\n+\nIII\n", "invalid_alphabet"),
        ("@r\nAC\u2028GT\n+\nIIIII\n".encode(), "invalid_alphabet"),
        (b"@r\nAC\x00\n+\nII\n", "corrupted_input"),
        (b"@r\n\xff\n+\nI\n", "invalid_encoding"),
    ],
)
def test_malformed_fastq_has_structured_outcomes(content, code):
    _error(process_fastq, code, content)


def test_compression_expansion_has_a_separate_budget():
    content = b"@r\n" + b"A" * 4000 + b"\n+\n" + b"I" * 4000 + b"\n"
    compressed = gzip.compress(content, mtime=0)
    _error(process_fastq, "compression_ratio_exceeded", compressed)
    assert (
        process_fastq(compressed, limits=DatasetLimits(max_compression_ratio=1000)).record_count
        == 1
    )


@pytest.mark.parametrize(
    "field",
    [
        "max_input_bytes",
        "max_decoded_bytes",
        "max_line_bytes",
        "max_records",
        "max_compression_ratio",
    ],
)
def test_invalid_limits_are_rejected(field):
    with pytest.raises(ValidationError):
        DatasetLimits(**{field: 0})


def test_record_sources_must_bind_to_retained_artifacts():
    data = process_fastq(FASTQ).model_dump(round_trip=True)
    data["reads"][0]["source"] = "invented#record:1"
    with pytest.raises(ValidationError):
        DatasetDraft.model_validate(data)


def test_fastq_byte_decoding_and_compression_budgets():
    function, content = process_fastq, FASTQ
    compressed = gzip.compress(content, mtime=0)
    function(
        content, limits=DatasetLimits(max_input_bytes=len(content), max_decoded_bytes=len(content))
    )
    function(compressed, limits=DatasetLimits(max_decoded_bytes=len(content)))
    _error(
        function, "input_too_large", content, limits=DatasetLimits(max_input_bytes=len(content) - 1)
    )
    _error(
        function, "decoded_input_too_large", compressed, limits=DatasetLimits(max_decoded_bytes=1)
    )
    _error(function, "line_too_large", content, limits=DatasetLimits(max_line_bytes=2))
    _error(function, "invalid_compression", compressed[:-4])
    _error(function, "invalid_compression", b"\x1f\x8bgarbage")
    _error(function, "compression_mismatch", content, filename="input.gz")


def test_fastq_immutability_json_roundtrip_and_no_confirmation_forgery():
    draft = process_fastq(FASTQ)
    restored = DatasetDraft.model_validate_json(draft.model_dump_json(round_trip=True))
    assert restored == draft
    assert restored.normalized_checksum == draft.normalized_checksum
    assert draft.normalized_checksum.startswith("sha256:")
    with pytest.raises(ValidationError):
        draft.executable = True
    values = draft.model_dump(round_trip=True)
    values["executable"] = True
    with pytest.raises(ValidationError):
        DatasetDraft.model_validate(values)
    values = draft.model_dump(round_trip=True)
    values["unexpected"] = "inferred"
    with pytest.raises(ValidationError):
        DatasetDraft.model_validate(values)


def test_record_limits_fail_instead_of_silently_truncating():
    _error(process_fastq, "too_many_records", FASTQ, limits=DatasetLimits(max_records=1))


def test_read_identity_excludes_compression_but_includes_quality():
    plain = process_fastq(FASTQ)
    compressed = process_fastq(gzip.compress(FASTQ, mtime=0))
    assert plain.normalized_checksum == compressed.normalized_checksum
    assert plain.artifacts[0].checksum != compressed.artifacts[0].checksum
    assert (
        plain.normalized_checksum
        != process_fastq(FASTQ.replace(b"!I@+", b"IIII")).normalized_checksum
    )


def test_case_normalization_is_disclosed_without_changing_scientific_identity():
    lower = process_fastq(FASTQ)
    upper = process_fastq(FASTQ.replace(b"acgt", b"ACGT"))
    assert "case_normalized" in {w.code for w in lower.warnings}
    assert "case_normalized" not in {w.code for w in upper.warnings}
    assert lower.normalized_checksum == upper.normalized_checksum


@pytest.mark.parametrize(
    "content, expected",
    [
        (FASTQ, "fastq"),
        (b">r\nACGT", "unknown"),
        (b"##fileformat=VCFv4.3\n", "vcf"),
    ],
)
@pytest.mark.parametrize("compressed", [False, True])
def test_header_hints_require_confirmation(content, expected, compressed):
    detection = detect_dataset(gzip.compress(content, mtime=0) if compressed else content)
    assert detection.detected_format == expected
    assert detection.requires_confirmation is True


def test_line_count_budget_rejects_without_a_partial_readset():
    _error(process_fastq, "too_many_lines", FASTQ, limits=DatasetLimits(max_lines=3))
    with pytest.raises(ValidationError):
        DatasetLimits(max_lines=0)


def test_read_contract_rejects_forged_symbols_quality_lengths_and_ai_origin():
    for changes in ({"sequence": "AU"}, {"qualities": "I"}, {"origin": "ai_inferred"}):
        values = process_fastq(FASTQ).reads[0].model_dump(round_trip=True)
        values.update(changes)
        with pytest.raises(ValidationError):
            ReadRecord.model_validate(values)


@pytest.mark.parametrize(
    "changes",
    [
        {"data_role": "variants"},
        {"declared_format": "vcf"},
        {"reference_checked": True},
        {"reference_sequence_checksum": "invented"},
        {"artifacts": ()},
    ],
)
def test_read_draft_rejects_role_reference_and_artifact_forgery(changes):
    values = process_fastq(FASTQ).model_dump(round_trip=True)
    values.update(changes)
    with pytest.raises(ValidationError):
        DatasetDraft.model_validate(values)


def test_shared_variant_contract_is_only_a_schema_not_a_vcf_adapter():
    # Common schemas are included for the next dependent PR; no VCF parsing occurs.
    variant = VariantRecord(
        contig="synthetic",
        position=1,
        reference="A",
        alternatives=("C",),
        info=".",
        source="user-supplied-artifact",
        format_keys=("GT",),
        samples=(SampleCall(sample="test", values=("0/1",), genotype=(0, 1), phased=False),),
    )
    assert variant.coordinate_system == "1-based-inclusive"
    for changes in (
        {"position": 0},
        {"reference": "<DEL>"},
        {"alternatives": ("C", "C")},
        {"samples": (SampleCall(sample="test", values=("0/2",), genotype=(0, 2)),)},
    ):
        values = variant.model_dump(round_trip=True)
        values.update(changes)
        with pytest.raises(ValidationError):
            VariantRecord.model_validate(values)
