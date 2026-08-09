# Heuristic scoring for CRISPR base edits — on-target efficiency and off-target risk.
# Pure functions, no I/O. Both are transparent heuristics (not trained models); the
# off-target score is a within-sequence proxy, not a genome-wide search.

from __future__ import annotations

from itertools import groupby

from app.modules.simulation.nucleotides import revcomp

_GUIDE_LEN = 20
_ACGT = set("ACGT")


def _clean_guide(guide_rna: str) -> str:
    """Uppercase and validate a guide; return the cleaned 20-nt DNA guide."""
    guide = guide_rna.upper()
    if len(guide) != _GUIDE_LEN or set(guide) - _ACGT:
        raise ValueError(f"guide_rna must be {_GUIDE_LEN} nt of A/C/G/T")
    return guide


def _longest_run(seq: str) -> int:
    """Length of the longest run of a single repeated character (0 for empty)."""
    return max((sum(1 for _ in group) for _, group in groupby(seq)), default=0)


def _hamming(a: str, b: str) -> int:
    # strict=True documents (and enforces) that both are the same length.
    return sum(x != y for x, y in zip(a, b, strict=True))


def on_target_score(guide_rna: str) -> float:
    """Heuristic on-target efficiency in [0, 1] from guide-intrinsic features.

    The engine requires an exact protospacer match and a valid PAM, so mismatch and
    PAM terms are constant for any accepted edit; this scores what actually varies:
      - GC content, best in the ~40-60% band (extremes reduce efficiency)
      - homopolymer runs, which hurt expression/efficiency (especially poly-T)
    A transparent heuristic, not a trained efficiency model.
    """
    guide = _clean_guide(guide_rna)

    gc = (guide.count("G") + guide.count("C")) / _GUIDE_LEN
    if 0.4 <= gc <= 0.6:
        gc_factor = 1.0
    elif gc < 0.4:
        gc_factor = gc / 0.4
    else:
        gc_factor = (1.0 - gc) / 0.4

    longest = _longest_run(guide)
    homopolymer_factor = 1.0 if longest < 4 else max(0.0, 1.0 - 0.2 * (longest - 3))

    return round(gc_factor * homopolymer_factor, 4)


def off_target_score(sequence: str, guide_rna: str, max_mismatches: int = 3) -> float:
    """Heuristic off-target RISK in [0, 1] from near-matches within *sequence*.

    Scans both strands of the provided sequence for sites matching the guide with
    1..max_mismatches mismatches (the exact on-target site, 0 mismatches, is excluded).
    Closer matches contribute more, and risk saturates toward 1 as matches accumulate.
    A within-sequence specificity proxy — PAM-agnostic, not a genome-wide search.
    Runs in O(len(sequence)) — intended for gene-sized sequences, not whole genomes.
    """
    guide = _clean_guide(guide_rna)
    if max_mismatches < 1:
        raise ValueError("max_mismatches must be >= 1")

    seq = sequence.upper()
    weight_total = 0.0
    for strand in (seq, revcomp(seq)):
        for i in range(len(strand) - _GUIDE_LEN + 1):
            dist = _hamming(strand[i : i + _GUIDE_LEN], guide)
            if 1 <= dist <= max_mismatches:
                # closer matches (fewer mismatches) contribute more risk
                weight_total += (max_mismatches + 1 - dist) / (max_mismatches + 1)

    return round(1 - 0.5**weight_total, 4)
