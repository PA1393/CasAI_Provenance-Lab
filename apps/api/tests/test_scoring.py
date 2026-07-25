import pytest

from app.modules.simulation.scoring import off_target_score, on_target_score

BALANCED = "ACGTTGCAAGCTTACGGATC"  # 50% GC, no long runs, non-repetitive


def test_on_target_balanced_guide_is_max() -> None:
    assert on_target_score(BALANCED) == 1.0


def test_on_target_penalizes_extreme_gc() -> None:
    high_gc = "GCGCGCGCGCGCGCGCGCGC"  # 100% GC
    assert on_target_score(high_gc) < on_target_score(BALANCED)


def test_on_target_penalizes_homopolymer_run() -> None:
    with_run = "ACGTTGCAAGCTTACGAAAA"  # trailing run of 4 A's
    assert on_target_score(with_run) < on_target_score(BALANCED)


def test_on_target_in_unit_range() -> None:
    for guide in (BALANCED, "GCGCGCGCGCGCGCGCGCGC", "AAAAAAAAAAAAAAAAAAAA"):
        assert 0.0 <= on_target_score(guide) <= 1.0


def test_off_target_zero_when_no_near_matches() -> None:
    assert off_target_score("T" * 40, BALANCED) == 0.0


def test_off_target_excludes_exact_on_target_site() -> None:
    # the true target site (0 mismatches) must not be counted as off-target risk
    seq = "GGGG" + BALANCED + "GGGG"
    assert off_target_score(seq, BALANCED) == 0.0


def test_off_target_positive_with_near_match() -> None:
    near = "ACGTTGCAAGCTTACGGATA"  # 1 mismatch vs BALANCED (last base C->A)
    seq = "GGGG" + near + "GGGG"
    assert off_target_score(seq, BALANCED) > 0.0


def test_off_target_more_matches_higher_risk() -> None:
    near1 = "ACGTTGCAAGCTTACGGATA"  # 1 mismatch
    near2 = "ACGTTGCAAGCTTACGGATG"  # 1 mismatch (different base)
    one = "GGGG" + near1 + "GGGG"
    two = "GGGG" + near1 + "GGGG" + near2 + "GGGG"
    assert off_target_score(two, BALANCED) > off_target_score(one, BALANCED)


def test_off_target_in_unit_range() -> None:
    seq = "GGGG" + "ACGTTGCAAGCTTACGGATA" + "GGGG"
    assert 0.0 <= off_target_score(seq, BALANCED) <= 1.0


@pytest.mark.parametrize("bad", ["AAA", "A" * 19 + "N", "acgt"])
def test_scoring_validates_guide(bad: str) -> None:
    with pytest.raises(ValueError):
        on_target_score(bad)
    with pytest.raises(ValueError):
        off_target_score("ACGT" * 12, bad)


def test_off_target_rejects_invalid_max_mismatches() -> None:
    with pytest.raises(ValueError):
        off_target_score("ACGT" * 12, BALANCED, max_mismatches=0)
