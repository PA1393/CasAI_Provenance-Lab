# Shared nucleotide utilities for CRISPR base editing.
# Consolidated from engine.py, spec.py, and scoring.py.

from __future__ import annotations

# IUPAC complement lookup for reverse-complement and strand handling.
COMPLEMENT = str.maketrans(
    "ACGTUNRYSWKMBDHV",
    "TGCAANYRSWMKVHDB",
)

# IUPAC code -> the set of concrete bases it matches (used for PAM matching, e.g. N=any).
IUPAC = {
    "A": "A", "C": "C", "G": "G", "T": "T",
    "N": "ACGT", "R": "AG", "Y": "CT", "S": "GC", "W": "AT",
    "K": "GT", "M": "AC", "B": "CGT", "D": "AGT", "H": "ACT", "V": "ACG",
}


def revcomp(seq: str) -> str:
    """Return the reverse complement of a DNA sequence."""
    return seq.translate(COMPLEMENT)[::-1]


def pam_matches(segment: str, pam: str) -> bool:
    """Check if *segment* matches the PAM pattern *pam*.

    Each PAM code (e.g. N) expands to the bases it allows; the actual base must be one.
    """
    if len(segment) != len(pam):
        return False
    return all(base in IUPAC.get(code, code) for code, base in zip(pam, segment))
