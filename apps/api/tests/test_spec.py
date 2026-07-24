import pytest

from app.modules.simulation import spec

GUIDE_C = "AAACAAAAAAAAAAAAAAAA"  # C at protospacer position 4 (window is positions 4-8)
GUIDE_A = "GGGAGGGGGGGGGGGGGGGG"  # A at protospacer position 4


def _seq(guide: str, pam: str = "AGG") -> str:
    return "TTTT" + guide + pam + "TTTT"


def _window(guide_rna: str) -> str:
    return guide_rna[3:8]  # protospacer positions 4-8, 0-indexed


def test_design_guide_cbe_returns_guide() -> None:
    d = spec.design_guide(_seq(GUIDE_C), "CBE")
    assert d is not None
    assert len(d["guide_rna"]) == 20
    assert "C" in _window(d["guide_rna"])


def test_design_guide_abe_returns_guide() -> None:
    d = spec.design_guide(_seq(GUIDE_A, pam="TGG"), "ABE")
    assert d is not None
    assert "A" in _window(d["guide_rna"])


def test_design_guide_finds_reverse_strand_site() -> None:
    # put a clean CBE site on a sequence, then reverse-complement the whole thing so
    # the only compatible site lives on the antisense strand
    forward = "AAAA" + GUIDE_C + "AGG" + "AAAA"
    seq = spec._revcomp(forward)
    d = spec.design_guide(seq, "CBE")
    assert d is not None
    assert d["strand"] == "-"


def test_design_guide_none_when_no_pam() -> None:
    assert spec.design_guide("A" * 60, "CBE") is None


def test_design_guide_none_when_no_editable_base_in_window() -> None:
    # G/C-only sequence: NGG PAMs exist, but neither strand has an A for ABE to edit
    assert spec.design_guide("GGGCCC" * 10, "ABE") is None


def test_design_guide_rejects_invalid_edit_type() -> None:
    with pytest.raises(ValueError):
        spec.design_guide(_seq(GUIDE_C), "XYZ")


def test_design_guide_skips_ambiguous_protospacer() -> None:
    guide_n = "AAACANAAAAAAAAAAAAAA"  # 20 nt, but with an ambiguous N in the protospacer
    seq = "TTTT" + guide_n + "AGG" + "TTTT"
    # the only PAM-flanked site is skipped because of the N -> no candidate found
    assert spec.design_guide(seq, "CBE") is None


# ── Validate Schema gate ─────────────────────────────────────────────────────
def _valid_spec_and_seq():
    seq = _seq(GUIDE_C)
    d = spec.design_guide(seq, "CBE")
    return spec.EditSpec(edit_type="CBE", guide_rna=d["guide_rna"], strand=d["strand"]), seq


def test_validate_passes_for_valid_spec() -> None:
    edit_spec, seq = _valid_spec_and_seq()
    assert spec.validate_edit_spec(edit_spec, seq) == []


def test_validate_flags_bad_guide_length() -> None:
    edit_spec = spec.EditSpec(edit_type="CBE", guide_rna="AAA", strand="+")
    assert spec.validate_edit_spec(edit_spec, "ACGT" * 20)


def test_validate_flags_non_acgt_guide() -> None:
    edit_spec = spec.EditSpec(edit_type="CBE", guide_rna="AAACANAAAAAAAAAAAAAA", strand="+")
    assert spec.validate_edit_spec(edit_spec, "ACGT" * 20)


def test_validate_flags_bad_edit_type() -> None:
    edit_spec, seq = _valid_spec_and_seq()
    edit_spec.edit_type = "XYZ"
    assert spec.validate_edit_spec(edit_spec, seq)


def test_validate_flags_bad_strand() -> None:
    edit_spec, seq = _valid_spec_and_seq()
    edit_spec.strand = "x"
    assert spec.validate_edit_spec(edit_spec, seq)


def test_validate_flags_window_out_of_range() -> None:
    edit_spec, seq = _valid_spec_and_seq()
    edit_spec.window = (0, 8)
    assert spec.validate_edit_spec(edit_spec, seq)


def test_validate_flags_guide_not_in_sequence() -> None:
    edit_spec, _ = _valid_spec_and_seq()
    assert spec.validate_edit_spec(edit_spec, "T" * 40)  # guide absent -> not applicable


def test_validate_flags_no_editable_base_in_window() -> None:
    guide = "A" * 20  # no C anywhere -> no editable C for CBE in the window
    seq = "TTTT" + guide + "AGG" + "TTTT"
    edit_spec = spec.EditSpec(edit_type="CBE", guide_rna=guide, strand="+")
    assert spec.validate_edit_spec(edit_spec, seq)


def test_validate_flags_malformed_window_without_crashing() -> None:
    edit_spec, seq = _valid_spec_and_seq()
    edit_spec.window = (1, 2, 3)  # not a (lo, hi) pair -> flagged, not a crash
    assert spec.validate_edit_spec(edit_spec, seq)
