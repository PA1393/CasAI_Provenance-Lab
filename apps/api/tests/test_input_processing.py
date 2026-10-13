"""Offline scientific intake tests; no OpenAI, Supabase or reference-provider dependency."""

import hashlib
import json

import pytest
from pydantic import ValidationError

from app.modules.information_processor.contracts import (
    FieldValue,
    IntakeRequest,
    OriginalArtifact,
    ResearchDraft,
    SequenceRecord,
)
from app.modules.information_processor.parser import (
    InputValidationError,
    decode_input,
    detect_input,
    parse_sequences,
)
from app.modules.information_processor.processing import DEMO_FASTA, DEMO_VERSION, process_input


def _request(content="acgt", **kwargs):
    return IntakeRequest(input_method="pasted_sequence", content=content, **kwargs)


def _required(draft):
    return {item.field for item in draft.missing_fields if item.requirement == "required"}


def test_single_fasta_retains_header_sequence_and_exact_original_bytes():
    text = "\ufeff;comment\r\n>seq1 researcher label\r\n ac gt\t\r\n"
    draft = process_input(IntakeRequest(input_method="fasta", content=text, molecule_type="DNA"))
    (record,) = draft.records
    assert record.record_id.value == "seq1"
    assert record.description.value == "researcher label"
    assert record.sequence.value == "ACGT"
    assert record.sequence_length == 4
    assert record.sequence.origin == "file_extracted"
    assert record.sequence.source == f"{draft.original_artifact.checksum}#seq1"
    assert draft.original_artifact.content == text.encode("utf-8")
    assert (
        draft.original_artifact.checksum
        == "sha256:"
        + hashlib.sha256(
            text.encode("utf-8"),
        ).hexdigest()
    )
    assert draft.original_artifact.byte_length == len(text.encode("utf-8"))


def test_multiple_fasta_records_are_never_concatenated():
    draft = process_input(
        IntakeRequest(
            input_method="fasta",
            content=">one\nAAAA\n>two\nGGGG\n",
            molecule_type="DNA",
        )
    )
    assert [record.record_id.value for record in draft.records] == ["one", "two"]
    assert [record.sequence.value for record in draft.records] == ["AAAA", "GGGG"]
    assert len({record.checksum for record in draft.records}) == 2


@pytest.mark.parametrize(
    "molecule, text, expected",
    [
        ("DNA", " a c\tg\nT \r\n", "ACGT"),
        ("RNA", " a c\tg\nU ", "ACGU"),
        ("protein", "m kwv tf\ni", "MKWVTFI"),
    ],
)
def test_declared_molecule_normalization(molecule, text, expected):
    (record,) = process_input(_request(text, molecule_type=molecule)).records
    assert record.sequence.value == expected
    assert record.molecule_type.value == molecule
    assert record.source_molecule_type.value == molecule
    assert record.sequence.origin == "user_supplied"


def test_rna_is_preserved_unless_conversion_is_explicit():
    kept = process_input(_request("acgu", molecule_type="RNA"))
    converted = process_input(_request("acgu", molecule_type="RNA", rna_to_dna=True))
    assert kept.records[0].sequence.value == "ACGU"
    assert converted.records[0].sequence.value == "ACGT"
    assert converted.records[0].molecule_type.value == "DNA"
    assert converted.records[0].source_molecule_type.value == "RNA"
    assert any(warning.code == "rna_to_dna" for warning in converted.warnings)
    assert kept.normalized_checksum != converted.normalized_checksum


@pytest.mark.parametrize("molecule", [None, "DNA", "protein"])
def test_rna_conversion_rejects_other_or_undeclared_molecules(molecule):
    with pytest.raises(ValidationError, match="RNA declaration"):
        _request("ACGU", molecule_type=molecule, rna_to_dna=True)


@pytest.mark.parametrize(
    "molecule, text",
    [
        ("DNA", "ACGU"),
        ("RNA", "ACGT"),
        ("DNA", "ACGZ"),
        ("protein", "MKW*"),
        ("protein", "MKW-"),
        ("DNA", "AC1G"),
    ],
)
def test_invalid_alphabets_are_rejected_without_silent_repair(molecule, text):
    with pytest.raises(InputValidationError) as error:
        process_input(_request(text, molecule_type=molecule))
    assert error.value.issue.code == "invalid_alphabet"
    assert error.value.issue.record_id == "sequence_1"


@pytest.mark.parametrize("text", ["", " \n\t", "\ufeff\r\n"])
def test_empty_inputs_have_a_structured_error(text):
    with pytest.raises(InputValidationError) as error:
        process_input(_request(text, molecule_type="DNA"))
    assert error.value.issue.code == "empty_input"


@pytest.mark.parametrize(
    "content, code",
    [
        (b"\xffACGT", "invalid_encoding"),
        (b"AC\x00GT", "corrupted_input"),
        (b"AC\x7fGT", "corrupted_input"),
        (b"AC\x0bGT", "corrupted_input"),
    ],
)
def test_corrupted_input_is_rejected(content, code):
    with pytest.raises(InputValidationError) as error:
        decode_input(content)
    assert error.value.issue.code == code


def test_limits_count_utf8_bytes_and_accept_the_exact_boundary():
    assert decode_input(b"ACGT", max_bytes=4) == "ACGT"
    with pytest.raises(InputValidationError) as error:
        process_input(_request("ACGT", molecule_type="DNA"), max_bytes=3)
    assert error.value.issue.code == "input_too_large"
    with pytest.raises(InputValidationError) as error:
        process_input(IntakeRequest(input_method="objective", content="éé"), max_bytes=3)
    assert error.value.issue.code == "input_too_large"


@pytest.mark.parametrize(
    "text, code",
    [
        ("ACGT", "missing_header"),
        (">\nACGT", "missing_identifier"),
        (">only\n", "empty_record"),
        (">one\n>two\nACGT", "empty_record"),
        (">one\nACGT\n>one\nTGCA", "duplicate_identifier"),
        (";only a comment", "empty_input"),
    ],
)
def test_malformed_fasta_has_explicit_outcomes(text, code):
    with pytest.raises(InputValidationError) as error:
        process_input(IntakeRequest(input_method="fasta", content=text, molecule_type="DNA"))
    assert error.value.issue.code == code


def test_fasta_record_count_is_bounded():
    content = b">a\nACGT\n>b\nTGCA\n"
    assert (
        len(parse_sequences(content, input_format="fasta", molecule_type="DNA", max_records=2)) == 2
    )
    with pytest.raises(InputValidationError) as error:
        parse_sequences(content, input_format="fasta", molecule_type="DNA", max_records=1)
    assert error.value.issue.code == "too_many_records"


def test_declared_pasted_input_does_not_silently_consume_fasta_headers():
    with pytest.raises(InputValidationError) as error:
        process_input(_request(">sequence\nACGT", molecule_type="DNA"))
    assert error.value.issue.code == "format_mismatch"


def test_detection_does_not_guess_molecule_type_from_shared_alphabets():
    result = detect_input(b"acgt")
    assert result.detected_method == "pasted_sequence"
    assert set(result.candidate_molecule_types) == {"DNA", "protein"}
    assert set(detect_input(b"acg").candidate_molecule_types) == {"DNA", "RNA", "protein"}
    assert result.requires_confirmation is True
    draft = process_input(_request("acgt"))
    assert draft.records[0].molecule_type.origin == "unresolved"
    assert draft.records[0].molecule_type.value is None
    assert "molecule_type" in _required(draft)
    assert draft.ready_for_confirmation is False


@pytest.mark.parametrize(
    "content, method",
    [
        (b">sequence\nACGT", "fasta"),
        (b";comment\n>sequence\nACGT", "fasta"),
        (b"NM_000546.6", "accession"),
        (b"edit the crop gene", "unknown"),
        (b"@read\nACGT\n+\n!!!!", "unknown"),
    ],
)
def test_detects_formats_without_parsing_or_retrieving_them(content, method):
    assert detect_input(content).detected_method == method


def test_whitespace_and_case_equivalence_has_a_separate_original_checksum():
    a = process_input(_request("ac gt\r\n", molecule_type="DNA"))
    b = process_input(_request("ACGT", molecule_type="DNA"))
    assert a.normalized_checksum == b.normalized_checksum
    assert a.records[0].checksum == b.records[0].checksum
    assert a.original_artifact.checksum != b.original_artifact.checksum
    assert (
        a.normalized_checksum
        != process_input(_request("AGGT", molecule_type="DNA")).normalized_checksum
    )


def test_scientific_metadata_molecule_and_record_order_affect_identity():
    dna = process_input(_request("ACG", molecule_type="DNA", organism="A"))
    changed = process_input(_request("ACG", molecule_type="DNA", organism="B"))
    protein = process_input(_request("ACG", molecule_type="protein", organism="A"))
    assert (
        len({dna.normalized_checksum, changed.normalized_checksum, protein.normalized_checksum})
        == 3
    )
    first = process_input(
        IntakeRequest(
            input_method="fasta",
            content=">a\nAAA\n>b\nCCC",
            molecule_type="DNA",
        )
    )
    swapped = process_input(
        IntakeRequest(
            input_method="fasta",
            content=">b\nCCC\n>a\nAAA",
            molecule_type="DNA",
        )
    )
    assert first.normalized_checksum != swapped.normalized_checksum


def test_no_required_missing_fields_still_needs_explicit_confirmation():
    draft = process_input(_request("ACGT", molecule_type="DNA"))
    assert _required(draft) == set()
    assert draft.ready_for_confirmation is True
    assert draft.executable is False
    assert draft.status == "draft"
    assert all(
        not getattr(draft.records[0], name).confirmed for name in SequenceRecord.model_fields
    )
    assert any(
        item.field == "organism" and item.requirement == "recommended"
        for item in draft.missing_fields
    )


def test_all_normalized_sequence_fields_have_an_origin_and_source():
    (record,) = process_input(
        _request("ACGT", molecule_type="DNA", organism="Oryza sativa")
    ).records
    for name in SequenceRecord.model_fields:
        field = getattr(record, name)
        assert field.source
        assert field.origin == "unresolved" if field.value is None else field.origin != "unresolved"
    assert record.organism.origin == "user_supplied"
    assert record.reference_source.origin == "unresolved"
    assert record.coordinate_system.value == "1-based-inclusive"
    assert record.coordinate_system.origin == "system_default"


@pytest.mark.parametrize("accession", [None, "", "UNKNOWN_123", "NM_000546.6"])
def test_accessions_remain_unresolved_until_an_adapter_retrieves_an_exact_record(accession):
    draft = process_input(IntakeRequest(input_method="accession", accession=accession))
    assert not draft.records
    assert "reference_record" in _required(draft)
    assert draft.ready_for_confirmation is False
    assert draft.executable is False
    preserved = json.loads(draft.original_artifact.content)
    assert preserved["accession"] == accession
    if not accession:
        assert "accession" in _required(draft)
    else:
        assert draft.accession.origin == "user_supplied"


def test_gene_input_exposes_organism_and_transcript_ambiguity():
    draft = process_input(IntakeRequest(input_method="gene", gene_symbol="BRCA2"))
    assert _required(draft) == {"organism", "transcript", "reference_record"}
    assert draft.organism.origin == "unresolved"
    assert draft.transcript.origin == "unresolved"
    assert draft.reference_assembly.origin == "unresolved"
    supplied = process_input(
        IntakeRequest(
            input_method="gene",
            gene_symbol="BRCA2",
            organism="Homo sapiens",
            transcript="NM_000059.4",
        )
    )
    assert _required(supplied) == {"reference_record"}
    assert not supplied.records
    assert supplied.transcript.confirmed is False


def test_written_objective_is_retained_without_generating_biological_information():
    text = "Design a CBE edit for the crop gene; ACGT is mentioned in this objective."
    draft = process_input(IntakeRequest(input_method="objective", content=text))
    assert draft.original_artifact.content == text.encode()
    assert draft.objective.value == text
    assert draft.objective.origin == "user_supplied"
    assert not draft.records
    assert _required(draft) == {"source_sequence", "objective_specification"}


@pytest.mark.parametrize("method", ["fasta", "pasted_sequence", "accession", "gene", "demo"])
def test_ai_created_sequence_is_rejected_for_every_source_entry_path(method):
    request = IntakeRequest(
        input_method=method,
        sequence_origin="ai_inferred",
        content=">x\nACGT"
        if method == "fasta"
        else "ACGT"
        if method == "pasted_sequence"
        else None,
    )
    with pytest.raises(InputValidationError) as error:
        process_input(request)
    assert error.value.issue.code == "ai_sequence_rejected"


def test_ai_interpretation_can_be_saved_only_as_unconfirmed_objective_text():
    draft = process_input(
        IntakeRequest(
            input_method="objective",
            content="Candidate research objective",
            sequence_origin="ai_inferred",
        )
    )
    assert draft.objective.origin == "ai_inferred"
    assert draft.objective.confirmed is False
    assert draft.original_artifact.claim_type == "AI-inferred"
    assert draft.executable is False
    with pytest.raises(ValidationError):
        FieldValue(value="AI suggestion", origin="ai_inferred", source="model", confirmed=True)


def test_synthetic_demo_is_versioned_and_never_claims_reference_or_experimental_evidence():
    draft = process_input(IntakeRequest(input_method="demo"))
    repeated = process_input(IntakeRequest(input_method="demo"))
    assert draft.normalized_checksum == repeated.normalized_checksum
    assert draft.original_artifact.content == DEMO_FASTA
    assert draft.original_artifact.source == DEMO_VERSION
    assert draft.original_artifact.claim_type == "explanatory"
    assert draft.records[0].molecule_type.value == "DNA"
    assert draft.records[0].reference_source.origin == "unresolved"
    assert draft.records[0].organism.origin == "unresolved"
    assert any(warning.code == "synthetic_demo" for warning in draft.warnings)


@pytest.mark.parametrize("molecule, text", [("DNA", "ACGN"), ("RNA", "ACGUY"), ("protein", "MKWX")])
def test_ambiguous_symbols_are_retained_with_visible_warnings(molecule, text):
    draft = process_input(_request(text, molecule_type=molecule))
    assert draft.records[0].sequence.value == text
    assert any(warning.code == "ambiguous_symbols" for warning in draft.warnings)


def test_nested_models_are_immutable_and_drafts_roundtrip_without_losing_original_bytes():
    draft = process_input(_request("acgt\r\n", molecule_type="DNA"))
    with pytest.raises(ValidationError):
        draft.status = "confirmed"
    with pytest.raises(ValidationError):
        draft.records[0].sequence.value = "TTTT"
    encoded = draft.model_dump_json(round_trip=True)
    decoded = ResearchDraft.model_validate_json(encoded)
    assert decoded == draft
    assert decoded.original_artifact.content == b"acgt\r\n"
    assert decoded.normalized_checksum == draft.normalized_checksum


def test_unknown_fields_and_forged_confirmed_input_are_rejected():
    with pytest.raises(ValidationError):
        IntakeRequest(input_method="pasted_sequence", content="ACGT", experimental=True)
    with pytest.raises(ValidationError):
        IntakeRequest(input_method="pasted_sequence", content="ACGT", confirmed=True)
    with pytest.raises(ValidationError):
        OriginalArtifact(content=b"ACGT", source="input", claim_type="validated")
    with pytest.raises(ValidationError):
        FieldValue(value=None, origin="user_supplied", source="researcher")


def test_demo_content_cannot_be_replaced_or_declared_as_another_molecule():
    with pytest.raises(ValidationError):
        IntakeRequest(input_method="demo", content="customer sequence")
    with pytest.raises(InputValidationError):
        process_input(IntakeRequest(input_method="demo", molecule_type="protein"))


def test_normalization_is_disclosed_without_mutating_the_source():
    draft = process_input(_request("ac gt\r\n", molecule_type="DNA"))
    assert {warning.code for warning in draft.warnings} >= {
        "case_normalized",
        "whitespace_normalized",
    }
    assert draft.original_artifact.content == b"ac gt\r\n"


def test_protein_compatible_prose_and_genes_need_an_explicit_method():
    result = detect_input(b"edit the crop gene")
    assert result.detected_method == "unknown"
    assert result.candidate_molecule_types == ("protein",)
    assert result.requires_confirmation is True


def test_missing_analysis_cannot_override_an_unresolved_molecule():
    draft = process_input(_request("ACGT"))
    data = draft.model_dump(round_trip=True)
    data["missing_fields"] = ()
    assert ResearchDraft.model_validate(data).ready_for_confirmation is False


def test_unknown_nested_fields_and_sequence_origins_are_rejected():
    draft = process_input(_request("ACGT", molecule_type="DNA"))
    data = draft.model_dump(round_trip=True)
    data["records"][0]["sequence"]["invented_source"] = True
    with pytest.raises(ValidationError):
        ResearchDraft.model_validate(data)
    data = draft.records[0].model_dump(round_trip=True)
    data["sequence"]["origin"] = "ai_inferred"
    with pytest.raises(ValidationError, match="AI-inferred biological sequence"):
        SequenceRecord.model_validate(data)


@pytest.mark.parametrize("text", ["ſACG", "ßMKW", "ACGT\u00a0"])
@pytest.mark.parametrize("method", ["fasta", "pasted_sequence"])
def test_unicode_letters_cannot_silently_become_biological_symbols(text, method):
    with pytest.raises(InputValidationError) as error:
        process_input(
            IntakeRequest(
                input_method=method,
                content=f">seq\n{text}" if method == "fasta" else text,
                molecule_type="protein",
            )
        )
    assert error.value.issue.code == "invalid_alphabet"


def test_fasta_formatting_changes_preserve_scientific_identity():
    a = process_input(
        IntakeRequest(
            input_method="fasta",
            content=">seq description\r\n ac gt\r\n",
            molecule_type="DNA",
        )
    )
    b = process_input(
        IntakeRequest(
            input_method="fasta",
            content=">seq description\nACGT\n",
            molecule_type="DNA",
        )
    )
    assert a.normalized_checksum == b.normalized_checksum
    assert a.original_artifact.checksum != b.original_artifact.checksum


@pytest.mark.parametrize("text", ["ſACG", "ßMKW", "NC_٠٠٠٠٠٠.1"])
def test_detection_does_not_rewrite_unicode_as_a_sequence_or_accession(text):
    detected = detect_input(text.encode("utf-8"))
    assert detected.detected_method == "unknown"
    assert detected.candidate_molecule_types == ()


@pytest.mark.parametrize("method", ["accession", "gene"])
def test_reference_methods_require_their_explicit_metadata_fields(method):
    with pytest.raises(ValidationError, match="explicit accession/gene metadata"):
        IntakeRequest(input_method=method, content="NM_000546.6")


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
@pytest.mark.parametrize("method", ["fasta", "pasted_sequence"])
def test_unicode_line_separators_are_not_consumed_before_alphabet_validation(separator, method):
    content = f"AC{separator}GT"
    with pytest.raises(InputValidationError) as error:
        process_input(IntakeRequest(
            input_method=method,
            content=f">seq\n{content}" if method == "fasta" else content,
            molecule_type="DNA",
        ))
    assert error.value.issue.code == "invalid_alphabet"


@pytest.mark.parametrize("text", ["ACGT\u00a0", "ACGT\u2028", "ACGT\u0085"])
def test_detection_does_not_strip_unsupported_unicode_whitespace(text):
    detected = detect_input(text.encode("utf-8"))
    assert detected.detected_method == "unknown"
    assert detected.candidate_molecule_types == ()


@pytest.mark.parametrize(
    "content, removed",
    [(">seq\nACGT", False), (">seq\nACGT\n", True), (">seq\n AC GT\t", True)],
)
def test_fasta_whitespace_notices_describe_only_source_sequence_whitespace(content, removed):
    draft = process_input(IntakeRequest(input_method="fasta", content=content, molecule_type="DNA"))
    assert ("whitespace_normalized" in {w.code for w in draft.warnings}) is removed
    assert draft.original_artifact.content == content.encode("utf-8")


@pytest.mark.parametrize("ending", ["\r\n", "\r", "\n"])
def test_supported_ascii_line_boundaries_preserve_separate_records(ending):
    content = ending.join([">a", "AC", "GT", ">b", "GGGG"])
    draft = process_input(IntakeRequest(input_method="fasta", content=content, molecule_type="DNA"))
    assert [r.sequence.value for r in draft.records] == ["ACGT", "GGGG"]
