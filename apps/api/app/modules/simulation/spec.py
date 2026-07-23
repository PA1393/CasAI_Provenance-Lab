# Analysis agent (S5) — FIRST SCAFFOLD.
#
# Turns a prompt + retrieved vault context into a *candidate* base-edit spec (edit intent
# + a compatible guide site) which the engine can apply. design_guide() currently finds a
# base-editor-COMPATIBLE candidate guide but does NOT validate biological effect, off-target
# risk, codon consequence, knockout status, or gene-specific targeting — those are later
# layers. Keep this module STANDALONE: do not wire it into create_run() / the run pipeline
# until the base engine merges, EditSpec has a validation gate, and we've decided how the
# output maps into the provenance + simulation schema.
#
#   design_guide()       — deterministic guide design (pure).
#   _extract_intent()    — LLM intent extraction, grounded in retrieved chunks.
#   resolve_edit_spec()  — orchestrates retrieve -> intent -> guide -> EditSpec.
#
# NOTE: _revcomp / _pam_matches / _GUIDE_LEN are inlined here so this module is
# self-contained. They mirror simulation.engine; consolidate into a shared
# nucleotides module once the engine lands on main.

from __future__ import annotations

import json

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.modules.rag.service import _format_context, search_vault

_GUIDE_LEN = 20
_ACGT = set("ACGT")
_TARGET = {"CBE": "C", "ABE": "A"}  # base each editor converts within the window

_COMPLEMENT = str.maketrans("ACGTUNRYSWKMBDHV", "TGCAANYRSWMKVHDB")
_IUPAC = {
    "A": "A", "C": "C", "G": "G", "T": "T",
    "N": "ACGT", "R": "AG", "Y": "CT", "S": "GC", "W": "AT",
    "K": "GT", "M": "AC", "B": "CGT", "D": "AGT", "H": "ACT", "V": "ACG",
}

_INTENT_SYSTEM = (
    "You are a CRISPR base-editing analysis agent for a crop gene-editing lab. "
    "From the user's request and the numbered context passages, determine the intended edit. "
    "Respond with STRICT JSON only, with exactly these keys: "
    '"organism" (string or null), "gene" (string or null), '
    '"edit_type" ("CBE" for a C->T change, "ABE" for an A->G change, or null if unclear), '
    '"rationale" (one sentence grounded in the context, citing passages like [1]). '
    "Do NOT guess missing biological details. If the organism, gene, or edit type is not "
    "supported by the provided context, return null for that field and say what is missing "
    "in the rationale. Use only the provided context — do not invent facts."
)


class EditSpec(BaseModel):
    """Structured base-edit spec produced by the analysis agent and consumed by the
    engine. Stored on the run so re-runs are deterministic."""

    edit_type: str  # "CBE" (C->T) or "ABE" (A->G)
    guide_rna: str  # candidate 20-nt base-editor-compatible spacer (not validated/optimal)
    strand: str  # "+" or "-"
    window: tuple[int, int] = (4, 8)
    pam: str = "NGG"
    organism: str | None = None
    gene: str | None = None
    rationale: str | None = None  # the LLM's grounded, cited explanation


def _revcomp(seq: str) -> str:
    return seq.translate(_COMPLEMENT)[::-1]


def _pam_matches(segment: str, pam: str) -> bool:
    if len(segment) != len(pam):
        return False
    return all(base in _IUPAC.get(code, code) for code, base in zip(pam, segment))


def design_guide(
    sequence: str,
    edit_type: str,
    window: tuple[int, int] = (4, 8),
    pam: str = "NGG",
) -> dict | None:
    """Find a *candidate* base-editor-compatible guide site in *sequence*.

    Returns the first site (sense strand first, then antisense) with a valid *pam*
    immediately 3' AND an editable base (C for CBE, A for ABE) inside the editing
    *window*, as ``{guide_rna, strand}`` (protospacer in 5'->3'); None if no site.

    "Compatible" only means the site is edit-able — it does NOT prove the edit causes a
    knockout, hits a stop codon, disrupts a splice site, changes the intended codon, is
    off-target-safe, or that the named gene is actually present in the sequence. This is
    a candidate site, not a validated or biologically optimal guide.
    """
    edit_type = edit_type.upper()
    if edit_type not in _TARGET:
        raise ValueError("edit_type must be 'CBE' or 'ABE'")
    target = _TARGET[edit_type]
    w0, w1 = window[0] - 1, window[1] - 1
    seq = sequence.upper()

    for strand, strand_seq in (("+", seq), ("-", _revcomp(seq))):
        for i in range(len(strand_seq) - _GUIDE_LEN + 1):
            proto = strand_seq[i : i + _GUIDE_LEN]
            if set(proto) - _ACGT:
                continue
            if not _pam_matches(strand_seq[i + _GUIDE_LEN : i + _GUIDE_LEN + len(pam)], pam):
                continue
            if target in proto[w0 : w1 + 1]:
                return {"guide_rna": proto, "strand": strand}
    return None


def _extract_intent(prompt: str, chunks: list[dict]) -> dict:
    """Ask the LLM to extract a structured edit intent, grounded in retrieved *chunks*.

    Returns a dict with keys organism, gene, edit_type, rationale. Raises ValueError
    if the API key is missing or the model returns invalid JSON.
    """
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not set — analysis agent unavailable")

    client = OpenAI(api_key=settings.openai_api_key)
    context = _format_context(chunks)
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _INTENT_SYSTEM},
            {"role": "user", "content": f"Request:\n{prompt}\n\nContext:\n{context}"},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"analysis agent returned invalid JSON: {exc}") from exc


def resolve_edit_spec(
    prompt: str,
    sequence: str,
    *,
    match_count: int = 5,
    edit_type: str | None = None,
) -> EditSpec:
    """Run the full analysis agent: retrieve vault context, extract the edit intent
    (LLM), design a usable guide against *sequence*, and return an EditSpec.

    *edit_type* may be passed to override the LLM's choice. Raises ValueError if the
    edit type is unsupported or no usable guide site exists in the sequence.
    """
    chunks = search_vault(prompt, match_count=match_count)
    intent = _extract_intent(prompt, chunks)

    et = (edit_type or intent.get("edit_type") or "").upper()
    if et not in _TARGET:
        raise ValueError(
            f"edit type unclear or unsupported ({et!r}); the request and retrieved context "
            "did not clearly indicate CBE (C->T) or ABE (A->G) — not guessing"
        )

    design = design_guide(sequence, et)
    if design is None:
        raise ValueError(f"no candidate {et}-compatible guide site found in the sequence")

    return EditSpec(
        edit_type=et,
        guide_rna=design["guide_rna"],
        strand=design["strand"],
        organism=intent.get("organism"),
        gene=intent.get("gene"),
        rationale=intent.get("rationale"),
    )
