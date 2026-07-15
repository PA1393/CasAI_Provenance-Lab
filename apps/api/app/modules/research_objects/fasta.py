# FASTA parsing for uploaded research-object sequences.
# Pure string logic — no I/O, no DB — so it stays trivially testable.

from __future__ import annotations

# IUPAC nucleotide codes we accept. Anything outside this set means the upload
# isn't DNA, and we reject it rather than silently mangle it.
_NUCLEOTIDES = set("ACGTUNRYSWKMBDHV")

_PREVIEW_LEN = 60

# Guard against pathologically large uploads before we do any work. Crop gene
# fragments are tiny; this only stops an accidental/abusive multi-MB upload.
# Callers may pass a smaller max_length. ~10 MB of text.
_MAX_INPUT_CHARS = 10_000_000


def parse_fasta(text: str, max_length: int = _MAX_INPUT_CHARS) -> dict:
    """Parse FASTA text into a sequence plus the fields the pipeline needs.

    Sequence lines from every record are concatenated (header lines starting
    with ``>`` or ``;`` are ignored), uppercased, and stripped of whitespace.
    RNA input is accepted and ``U`` is normalized to ``T`` so the stored
    sequence is DNA — what the base-edit engine downstream operates on.

    Returns a dict with:
      - ``sequence``:        full nucleotide string (uppercase DNA, no whitespace)
      - ``sequence_length``: number of bases
      - ``gc_content``:      (G+C) / (A+C+G+T), 0.0–1.0 rounded to 4 dp; 0.0 if none
      - ``fasta_preview``:   first 60 bases, with a trailing ``...`` if truncated

    Raises ``ValueError`` if the input is empty, exceeds ``max_length`` characters,
    has no sequence, or contains a non-nucleotide character.
    """
    if not text or not text.strip():
        raise ValueError("empty FASTA input")
    if len(text) > max_length:
        raise ValueError(f"FASTA input too large: {len(text)} chars (max {max_length})")

    seq_parts: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith((">", ";")):
            continue
        seq_parts.append(line.upper())

    # Normalize RNA to DNA (U->T) before validation/counting so GC is computed
    # over the full base count and downstream ACGT guide-matching still works.
    sequence = "".join(seq_parts).replace("U", "T")
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
