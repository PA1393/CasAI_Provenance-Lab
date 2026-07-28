import pytest

from app.modules.simulation.engine import _revcomp, apply_base_edit

# 20-nt guides with a single target base inside the editing window (positions 4-8).
GUIDE_C = "AAACAAAAAAAAAAAAAAAA"  # one C at protospacer position 4
GUIDE_A = "GGGAGGGGGGGGGGGGGGGG"  # one A at protospacer position 4
GUIDE_CC = "AAACACAAAAAAAAAAAAAA"  # two C's, positions 4 and 6 (bystander)
GUIDE_FLAT = "AAAAAAAAAAAAAAAAAAAA"  # no C/G, no editable base for CBE


def _construct(guide: str, pam: str = "AGG") -> str:
    return "TTTT" + guide + pam + "TTTT"


def test_forward_cbe_edits_c_to_t() -> None:
    seq = _construct(GUIDE_C)  # protospacer at index 4, its C at index 7
    result = apply_base_edit(seq, GUIDE_C, "CBE")
    assert result["edited"] is True
    assert result["strand"] == "+"
    assert result["protospacer_start"] == 5
    assert result["pam_found"] == "AGG"
    assert result["edited_positions"] == [8]
    assert result["edited_sequence"][7] == "T"  # the C became T


def test_forward_abe_edits_a_to_g() -> None:
    seq = _construct(GUIDE_A, pam="TGG")
    result = apply_base_edit(seq, GUIDE_A, "ABE")
    assert result["edited"] is True
    assert result["edited_positions"] == [8]
    assert result["edited_sequence"][7] == "G"  # the A became G


def test_bystander_edits_all_targets_in_window() -> None:
    seq = _construct(GUIDE_CC, pam="CGG")
    result = apply_base_edit(seq, GUIDE_CC, "CBE")
    assert result["edited_positions"] == [8, 10]  # both C's converted
    assert result["edited_sequence"][7] == "T"
    assert result["edited_sequence"][9] == "T"


def test_reverse_strand_match_shows_as_g_to_a() -> None:
    # revcomp of a forward construct -> the guide now matches the antisense strand
    seq = _revcomp(_construct(GUIDE_C))
    result = apply_base_edit(seq, GUIDE_C, "CBE")
    assert result["edited"] is True
    assert result["strand"] == "-"
    assert len(result["edited_positions"]) == 1
    pos = result["edited_positions"][0]
    assert seq[pos - 1] == "G"  # sense base was G (complement of the edited C)
    assert result["edited_sequence"][pos - 1] == "A"  # ...and becomes A


def test_no_pam_means_no_edit() -> None:
    seq = _construct(GUIDE_C, pam="AAA")  # protospacer present, but PAM is not NGG
    result = apply_base_edit(seq, GUIDE_C, "CBE")
    assert result["edited"] is False
    assert result["strand"] is None
    assert result["edited_sequence"] == seq
    assert "PAM" in result["reason"]


def test_guide_not_found_means_no_edit() -> None:
    result = apply_base_edit("ACGT" * 12, GUIDE_C, "CBE")
    assert result["edited"] is False
    assert result["reason"] == "guide not found"


def test_valid_match_but_no_editable_base_in_window() -> None:
    seq = _construct(GUIDE_FLAT)  # valid protospacer + PAM, but no C to edit
    result = apply_base_edit(seq, GUIDE_FLAT, "CBE")
    assert result["edited"] is False
    assert result["strand"] == "+"
    assert result["protospacer_start"] == 5
    assert result["edited_positions"] == []
    assert "window" in result["reason"]


@pytest.mark.parametrize(
    "guide, edit_type",
    [
        ("AAA", "CBE"),  # wrong length
        ("A" * 19 + "N", "CBE"),  # non-ACGT base
        ("A" * 20, "XYZ"),  # unknown edit type
    ],
)
def test_invalid_inputs_raise(guide: str, edit_type: str) -> None:
    with pytest.raises(ValueError):
        apply_base_edit("ACGT" * 12, guide, edit_type)
