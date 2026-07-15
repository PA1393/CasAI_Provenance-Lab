# FASTA parsing for uploaded research-object sequences.
# Pure string logic — no I/O, no DB — so it stays trivially testable.

from __future__ import annotations

# IUPAC nucleotide codes we accept. Anything outside this set means the upload
# isn't DNA, and we reject it rather than silently mangle it.
_NUCLEOTIDES = set("ACGTUNRYSWKMBDHV")

_PREVIEW_LEN = 60


def parse_fasta(text: str) -> dict:
    """Parse FASTA text into a sequence plus the fields the pipeline needs.

    Sequence lines from every record are concatenated (header lines starting
    with ``>`` or ``;`` are ignored), uppercased, and stripped of whitespace.

    Returns a dict with:
      - ``sequence``:        full nucleotide string (uppercase, no whitespace)
      - ``sequence_length``: number of bases
      - ``gc_content``:      (G+C) / (A+C+G+T), 0.0–1.0 rounded to 4 dp; 0.0 if none
      - ``fasta_preview``:   first 60 bases, with a trailing ``...`` if truncated

    Raises ``ValueError`` if the input has no sequence or contains a
    non-nucleotide character.
    """
    if not text or not text.strip():
        raise ValueError("empty FASTA input")

    seq_parts: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith((">", ";")):
            continue
        seq_parts.append(line.upper())

    sequence = "".join(seq_parts)
    if not sequence:
        raise ValueError("FASTA has header(s) but no sequence")

    invalid = set(sequence) - _NUCLEOTIDES
    if invalid:
        raise ValueError(f"non-nucleotide characters in sequence: {sorted(invalid)}")

    length = len(sequence)
    acgt = sum(sequence.count(b) for b in "ACGT")
    gc = sum(sequence.count(b) for b in "GC")
    gc_content = round(gc / acgt, 4) if acgt else 0.0

    preview = sequence[:_PREVIEW_LEN] + ("..." if length > _PREVIEW_LEN else "")

    return {
        "sequence": sequence,
        "sequence_length": length,
        "gc_content": gc_content,
        "fasta_preview": preview,
    }
