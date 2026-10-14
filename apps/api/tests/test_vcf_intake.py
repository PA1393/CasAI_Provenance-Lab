"""Offline VCF inspection/ref-check tests; no CLI, FASTQ adapter or external provider calls."""

import gzip

import pytest
from pydantic import ValidationError

from app.modules.information_processor.contracts import checksum
from app.modules.information_processor.dataset_parser import DatasetLimits, process_vcf
from app.modules.information_processor.datasets import DatasetDraft, VariantRecord
from app.modules.information_processor.parser import InputValidationError

HEADER = "##fileformat=VCFv4.3\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"
ROW = "chr1\t2\trs1\tC\tT,G\t50\tPASS\tDP=12"


def _vcf(row=ROW, *, samples=False, header=HEADER):
    if samples:
        header += "\tFORMAT\ts1\ts2"
        row += "\tGT:DP\t0|2:12\t1/.:."
    return (header + "\n" + row + "\n").encode("utf-8")


def _error(function, expected, *args, **kwargs):
    with pytest.raises(InputValidationError) as error:
        function(*args, **kwargs)
    assert error.value.issue.code == expected
    return error.value.issue


@pytest.mark.parametrize("compressed", [False, True])
def test_vcf_preserves_multiallelic_genotypes_phasing_and_raw_annotations(compressed):
    original = _vcf(samples=True)
    content = gzip.compress(original, mtime=0) if compressed else original
    draft = process_vcf(content, sample_id="s1", reference_assembly="supplied-label")
    (variant,) = draft.variants
    assert variant.position == 2
    assert variant.coordinate_system == "1-based-inclusive"
    assert variant.alternatives == ("T", "G")
    assert variant.samples[0].genotype == (0, 2)
    assert variant.samples[0].phased is True
    assert variant.samples[1].genotype == (1, None)
    assert variant.samples[1].phased is False
    assert variant.format_keys == ("GT", "DP")
    assert variant.samples[0].values == ("0|2", "12")
    assert variant.info == "DP=12"
    assert draft.sample_names == ("s1", "s2")
    assert draft.artifacts[0].content == content
    assert draft.reference_checked is False
    assert {f.field for f in draft.missing_fields} == {"reference_record"}
    assert draft.reads == ()
    assert draft.executable is False


@pytest.mark.parametrize("version", ["4.2", "4.3", "4.4", "4.5"])
def test_supported_vcf_versions(version):
    content = _vcf(header=HEADER.replace("4.3", version))
    assert process_vcf(content).format_version == "VCFv" + version


def test_site_only_vcf_and_no_variant_control_are_valid_inspection_drafts():
    draft = process_vcf((HEADER + "\n").encode())
    assert draft.record_count == 0
    assert "no_variants" in {w.code for w in draft.warnings}
    assert draft.reference_checked is False
    assert {f.field for f in draft.missing_fields} == {"reference_record", "reference_assembly"}
    variant = process_vcf(_vcf("chr1\t1\t.\tA\t.\t.\t.\t.")).variants[0]
    assert variant.alternatives == ()
    assert variant.quality is None
    assert variant.filters is None


def test_reference_check_compares_exact_contigs_coordinates_and_ref_bases():
    draft = process_vcf(_vcf(), reference_content=b">chr1\nACGT\n", reference_assembly="label")
    assert draft.reference_checked is True
    assert draft.missing_fields == ()
    assert draft.artifacts[1].role == "reference"
    assert draft.reference_assembly.confirmed is False
    _error(process_vcf, "reference_mismatch", _vcf(), reference_content=b">chr1\nAAGT\n")
    _error(process_vcf, "reference_contig_missing", _vcf(), reference_content=b">other\nACGT\n")
    _error(process_vcf, "reference_mismatch", _vcf(), reference_content=b">chr1\nA\n")
    _error(
        process_vcf,
        "unsupported_reference_compression",
        _vcf(),
        reference_content=gzip.compress(b">chr1\nACGT\n"),
    )


def test_no_haplotype_inference_and_missing_sample_selection_are_visible():
    draft = process_vcf(_vcf(samples=True))
    assert {f.field for f in draft.missing_fields} == {
        "sample_id",
        "reference_record",
        "reference_assembly",
    }
    assert "variants_not_haplotype" in {w.code for w in draft.warnings}
    _error(process_vcf, "sample_not_found", _vcf(samples=True), sample_id="unknown")


@pytest.mark.parametrize(
    "row, code",
    [
        (ROW.replace("\t2\t", "\t0\t"), "invalid_position"),
        (ROW.replace("\t2\t", "\t٢\t"), "invalid_position"),
        (ROW.replace("\t2\t", "\t2.0\t"), "invalid_position"),
        (ROW.replace("T,G", "<DEL>"), "unsupported_allele"),
        (ROW.replace("T,G", "T]chr2:1]"), "unsupported_allele"),
        (ROW.replace("T,G", "*"), "unsupported_allele"),
        (ROW.replace("T,G", "T,T"), "invalid_alleles"),
        (ROW.replace("T,G", "C"), "invalid_alleles"),
        (ROW.replace("50", "NaN"), "invalid_variant_quality"),
        (ROW.replace("50", "inf"), "invalid_variant_quality"),
        (ROW.replace("50", "-1"), "invalid_variant_quality"),
        (ROW.replace("50", "1_000"), "invalid_variant_quality"),
        (ROW.replace("PASS", "PASS;q10"), "invalid_filter"),
        (ROW.replace("PASS", "q10;q10"), "invalid_filter"),
        (ROW.replace("chr1", "chr 1"), "invalid_contig"),
        (ROW + "\textra", "invalid_vcf_record"),
    ],
)
def test_invalid_vcf_records_are_not_repaired(row, code):
    issue = _error(process_vcf, code, _vcf(row))
    assert issue.record_id == "line:3"


@pytest.mark.parametrize(
    "header",
    [
        HEADER.replace("4.3", "3.3"),
        HEADER.replace("#CHROM", "#CHR"),
        "##fileformat=VCFv4.3",
        HEADER + "\tFORMAT",
        HEADER + "\tFORMAT\ts1\ts1",
    ],
)
def test_invalid_vcf_headers_fail_clearly(header):
    with pytest.raises(InputValidationError):
        process_vcf(_vcf(header=header))


@pytest.mark.parametrize(
    "genotype, code",
    [
        ("3/0", "invalid_genotype"),
        ("-1/0", "invalid_genotype"),
        ("0|1/2", "unsupported_genotype"),
        ("0//1", "invalid_genotype"),
    ],
)
def test_invalid_or_unsupported_genotypes(genotype, code):
    content = _vcf(samples=True).replace(b"0|2", genotype.encode())
    _error(process_vcf, code, content)


def test_missing_trailing_sample_values_are_preserved_as_missing_not_zero():
    draft = process_vcf(_vcf(samples=True).replace(b"0|2:12", b"."))
    assert draft.variants[0].samples[0].values == (".", ".")
    assert draft.variants[0].samples[0].genotype == (None,)
    assert draft.variants[0].samples[0].phased is None


def test_reference_identity_ignores_case_and_line_formatting():
    a = process_vcf(_vcf(), reference_content=b">chr1\nACGT\n")
    b = process_vcf(_vcf(), reference_content=b">chr1\r\nac\r\ngt")
    assert a.reference_sequence_checksum == b.reference_sequence_checksum
    assert a.normalized_checksum == b.normalized_checksum
    assert a.artifacts[1].checksum != b.artifacts[1].checksum


@pytest.mark.parametrize(
    "field, value",
    [
        ("reference_checked", True),
        ("data_role", "reads"),
        ("reference_sequence_checksum", "invented"),
        ("artifacts", ()),
    ],
)
def test_draft_rejects_forged_role_reference_check_and_missing_artifacts(field, value):
    data = process_vcf(_vcf()).model_dump(round_trip=True)
    data[field] = value
    with pytest.raises(ValidationError):
        DatasetDraft.model_validate(data)


@pytest.mark.parametrize(
    "column, code", [("position", "invalid_position"), ("GT", "invalid_genotype")]
)
def test_huge_integers_have_structured_errors(column, code):
    if column == "position":
        content = _vcf(ROW.replace("\t2\t", "\t" + "9" * 5000 + "\t"))
    else:
        content = _vcf(samples=True).replace(b"0|2", b"9" * 5000)
    _error(process_vcf, code, content)


def test_vcf_byte_decoding_and_compression_budgets():
    function, content = process_vcf, _vcf()
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


def test_vcf_immutability_json_roundtrip_and_no_confirmation_forgery():
    draft = process_vcf(_vcf(samples=True))
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


def test_vcf_record_limits_reject_instead_of_silently_truncating():
    content = _vcf(ROW + "\n" + ROW)
    _error(process_vcf, "too_many_records", content, limits=DatasetLimits(max_records=1))


def test_vcf_line_count_bounds_large_metadata_headers():
    header = "##fileformat=VCFv4.3\n" + "##source=fixture\n" * 5 + HEADER.split("\n")[1]
    _error(process_vcf, "too_many_lines", _vcf(header=header), limits=DatasetLimits(max_lines=4))


def test_vcf_scientific_identity_ignores_compression_but_includes_calls_and_reference():
    content = _vcf(samples=True)
    plain = process_vcf(content)
    compressed = process_vcf(gzip.compress(content, mtime=0))
    assert plain.normalized_checksum == compressed.normalized_checksum
    assert plain.artifacts[0].checksum != compressed.artifacts[0].checksum
    assert (
        plain.normalized_checksum
        != process_vcf(content.replace(b"0|2", b"1|2")).normalized_checksum
    )
    one = process_vcf(_vcf(), reference_content=b">chr1\nACGT\n")
    two = process_vcf(_vcf(), reference_content=b">chr1\nACGA\n")
    assert one.normalized_checksum != two.normalized_checksum


def test_vcf_case_normalization_is_visible_without_changing_scientific_identity():
    lower = process_vcf(_vcf(ROW.replace("\tC\tT,G\t", "\tc\tt,g\t")))
    assert "case_normalized" in {w.code for w in lower.warnings}
    assert lower.normalized_checksum == process_vcf(_vcf()).normalized_checksum


def test_vcf_record_sources_bind_to_retained_original_artifacts():
    content = _vcf()
    draft = process_vcf(content)
    assert draft.variants[0].source == f"{checksum(content)}#line:3"
    values = draft.model_dump(round_trip=True)
    values["variants"][0]["source"] = "invented#record:1"
    with pytest.raises(ValidationError):
        DatasetDraft.model_validate(values)


@pytest.mark.parametrize("quality", ["1e2", ".5", "+2.0", "0"])
def test_vcf_numeric_quality_profile_accepts_finite_nonnegative_numbers(quality):
    draft = process_vcf(_vcf(ROW.replace("\t50\t", "\t" + quality + "\t")))
    assert draft.variants[0].quality == float(quality)


@pytest.mark.parametrize(
    "fields, code",
    [
        ("DP:GT\t12:0/1\t.:0/0", "invalid_format"),
        ("GT:GT\t0/1:0/1\t0/0:0/0", "invalid_format"),
        ("GT:DP\t0/1:12:extra\t0/0:0", "invalid_sample"),
        ("GT:DP\t0/1:\t0/0:0", "invalid_sample"),
    ],
)
def test_vcf_sample_structure_is_checked_without_interpreting_annotation_tags(fields, code):
    header = HEADER + "\tFORMAT\ts1\ts2"
    _error(process_vcf, code, _vcf(ROW + "\t" + fields, header=header))


def test_variant_model_rejects_invalid_coordinates_and_ai_origin():
    values = process_vcf(_vcf()).variants[0].model_dump(round_trip=True)
    for changes in ({"position": 0}, {"origin": "ai_inferred"}):
        changed = {**values, **changes}
        with pytest.raises(ValidationError):
            VariantRecord.model_validate(changed)
