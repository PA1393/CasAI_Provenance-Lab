# Deterministic CRISPR base-editing engine.
# Pure functions — no I/O, no DB — so the whole thing is trivially unit-testable.
#
# Encodes the rules documented in the vault's techniques/base-editing.md:
#   - CBE converts C->T, ABE converts A->G
#   - editing window is roughly protospacer positions 4-8 (PAM-distal = position 1)
#   - SpCas9 requires an NGG PAM immediately 3' of the 20-nt protospacer
# Positions returned are 1-indexed base pairs (per the target_region convention in CLAUDE.md).

from __future__ import annotations

_GUIDE_LEN = 20

# Full IUPAC complement so reverse-strand handling works even with ambiguity/N bases.
_COMPLEMENT = str.maketrans(
    "ACGTUNRYSWKMBDHV",
    "TGCAANYRSWMKVHDB",
)

# IUPAC code -> the set of concrete bases it matches (used for PAM matching, e.g. N=any).
_IUPAC = {
    "A": "A", "C": "C", "G": "G", "T": "T",
    "N": "ACGT", "R": "AG", "Y": "CT", "S": "GC", "W": "AT",
    "K": "GT", "M": "AC", "B": "CGT", "D": "AGT", "H": "ACT", "V": "ACG",
}

_EDITS = {"CBE": ("C", "T"), "ABE": ("A", "G")}


def _revcomp(seq: str) -> str:
    return seq.translate(_COMPLEMENT)[::-1]


def _pam_matches(segment: str, pam: str) -> bool:
    if len(segment) != len(pam):
        return False
    # Each PAM code (e.g. N) expands to the bases it allows; the actual base must be one.
    return all(base in _IUPAC.get(code, code) for code, base in zip(pam, segment))


def _locate(seq: str, guide: str, pam: str) -> tuple[int | None, str | None, bool]:
    """First occurrence of *guide* in *seq* that has a valid PAM immediately 3'.

    Returns (protospacer_start, pam_segment, guide_found). If no occurrence has a
    valid PAM, protospacer_start/pam_segment are None and guide_found says whether
    the guide appeared at all (to distinguish "no match" from "no PAM").
    """
    guide_found = False
    start = 0
    while True:
        i = seq.find(guide, start)
        if i == -1:
            return None, None, guide_found
        guide_found = True
        segment = seq[i + _GUIDE_LEN : i + _GUIDE_LEN + len(pam)]
        if _pam_matches(segment, pam):
            return i, segment, True
        start = i + 1


def _apply_window(
    seq: str, proto_start: int, w0: int, w1: int, target: str, repl: str
) -> tuple[str, list[int]]:
    """Convert every *target* base to *repl* within the editing window; return
    the edited string and the 0-indexed positions that changed."""
    chars = list(seq)
    positions: list[int] = []
    for offset in range(w0, w1 + 1):
        idx = proto_start + offset
        if chars[idx] == target:
            chars[idx] = repl
            positions.append(idx)
    return "".join(chars), positions


def _no_edit(sequence: str, reason: str) -> dict:
    return {
        "edited": False,
        "edited_sequence": sequence,
        "edited_positions": [],
        "strand": None,
        "protospacer_start": None,
        "pam_found": None,
        "reason": reason,
    }


def apply_base_edit(
    sequence: str,
    guide_rna: str,
    edit_type: str,
    window: tuple[int, int] = (4, 8),
    pam: str = "NGG",
) -> dict:
    """Apply a CRISPR base edit to *sequence* using *guide_rna*.

    Locates the 20-nt protospacer on the sense or antisense strand (requiring a
    valid *pam* immediately 3'), then converts eligible bases in the editing
    *window* (protospacer positions, 1-indexed): CBE C->T or ABE A->G. All
    eligible bases in the window are converted (bystander edits included).

    Returns a dict: edited (bool), edited_sequence, edited_positions (1-indexed
    bp, sense orientation), strand ("+"/"-"/None), protospacer_start (1-indexed),
    pam_found, and reason (set when nothing changed). Never raises on biology —
    only on invalid inputs.

    First valid match wins if the guide occurs more than once.
    """
    seq = sequence.upper()
    guide = guide_rna.upper()

    if len(guide) != _GUIDE_LEN or set(guide) - set("ACGT"):
        raise ValueError(f"guide_rna must be {_GUIDE_LEN} nt of A/C/G/T")
    edit_type = edit_type.upper()
    if edit_type not in _EDITS:
        raise ValueError("edit_type must be 'CBE' or 'ABE'")
    if not (1 <= window[0] <= window[1] <= _GUIDE_LEN):
        raise ValueError("window must be within protospacer positions 1..20")

    target, repl = _EDITS[edit_type]
    w0, w1 = window[0] - 1, window[1] - 1  # 0-indexed, inclusive

    # Sense strand first.
    i, pam_seg, guide_found_fwd = _locate(seq, guide, pam)
    if i is not None:
        edited, positions0 = _apply_window(seq, i, w0, w1, target, repl)
        proto_start = i
        strand = "+"
    else:
        # Antisense: reuse the exact forward logic on the reverse complement,
        # then map the result back to sense orientation.
        rc = _revcomp(seq)
        j, pam_seg, guide_found_rev = _locate(rc, guide, pam)
        if j is None:
            found = guide_found_fwd or guide_found_rev
            return _no_edit(
                seq, f"no {pam} PAM adjacent to protospacer" if found else "guide not found"
            )
        edited_rc, positions_rc = _apply_window(rc, j, w0, w1, target, repl)
        n = len(seq)
        edited = _revcomp(edited_rc)
        positions0 = [n - 1 - p for p in positions_rc]
        proto_start = n - (j + _GUIDE_LEN)
        strand = "-"

    positions_1 = sorted(p + 1 for p in positions0)
    return {
        "edited": bool(positions_1),
        "edited_sequence": edited,
        "edited_positions": positions_1,
        "strand": strand,
        "protospacer_start": proto_start + 1,
        "pam_found": pam_seg,
        "reason": None if positions_1 else "no editable base in window",
    }
