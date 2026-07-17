import pytest

from app.modules.research_objects.fasta import _PREVIEW_LEN, parse_fasta


def test_parses_single_record() -> None:
    result = parse_fasta(">seq1 description\nAACCGGTT\n")
    assert result["sequence"] == "AACCGGTT"
    assert result["sequence_length"] == 8
    assert result["gc_content"] == 0.5  # 4 of 8 are G/C
    assert result["fasta_preview"] == "AACCGGTT"


def test_concatenates_multiple_records() -> None:
    result = parse_fasta(">a\nAAAA\n>b\nGGGG\n")
    assert result["sequence"] == "AAAAGGGG"
    assert result["sequence_length"] == 8
    assert result["gc_content"] == 0.5


def test_normalizes_lowercase_and_whitespace() -> None:
    result = parse_fasta(">s\nacgt\n  ACGT \n")
    assert result["sequence"] == "ACGTACGT"


def test_ignores_semicolon_comment_lines() -> None:
    result = parse_fasta(";old-style comment\n>s\nACGT\n")
    assert result["sequence"] == "ACGT"


def test_gc_content_ignores_n_bases() -> None:
    # denominator is A+C+G+T only, so N does not dilute GC
    result = parse_fasta(">s\nGCNN\n")
    assert result["sequence_length"] == 4
    assert result["gc_content"] == 1.0


def test_normalizes_rna_u_to_t() -> None:
    # U is treated as T: stored as DNA and counted in the GC denominator
    result = parse_fasta(">s\nACGUACGU\n")
    assert result["sequence"] == "ACGTACGT"
    assert result["sequence_length"] == 8
    assert result["gc_content"] == 0.5


def test_preview_truncates_long_sequence() -> None:
    result = parse_fasta(">s\n" + "A" * 100)
    assert result["sequence_length"] == 100
    assert result["fasta_preview"] == "A" * 60 + "..."
    assert result["gc_content"] == 0.0


def test_preview_at_exact_length_has_no_ellipsis() -> None:
    # boundary: a sequence of exactly _PREVIEW_LEN must not get a trailing "..."
    seq = "A" * _PREVIEW_LEN
    result = parse_fasta(">s\n" + seq)
    assert result["sequence_length"] == _PREVIEW_LEN
    assert result["fasta_preview"] == seq


def test_rejects_input_over_max_length() -> None:
    with pytest.raises(ValueError):
        parse_fasta(">s\nACGTACGTACGT\n", max_length=5)


@pytest.mark.parametrize("bad", ["", "   ", "\n\n", ">only a header\n"])
def test_rejects_input_without_sequence(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_fasta(bad)


def test_rejects_non_nucleotide_characters() -> None:
    with pytest.raises(ValueError):
        parse_fasta(">s\nACGTXZ\n")
