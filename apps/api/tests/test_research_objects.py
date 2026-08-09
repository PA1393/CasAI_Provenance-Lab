"""Research-object creation tests — proves an uploaded FASTA is parsed and its
sequence persisted, which is what lets the base-edit pipeline get past the
`input` stage. Uses a fake Supabase so no live DB is needed."""

import pytest

from app.modules.research_objects import service


class _Recorder:
    """Minimal Supabase stub that records a single research_objects insert."""

    def __init__(self) -> None:
        self.inserted: dict | None = None

    def table(self, name: str):
        assert name == "research_objects"
        return self

    def insert(self, row: dict):
        self.inserted = row
        return self

    def execute(self):
        return type("Resp", (), {"data": [{**self.inserted, "research_object_id": "ro-1"}]})()


def _base_payload(**extra) -> dict:
    return {
        "name": "Rice OsSWEET14",
        "input_filename": "ossweet14.fasta",
        "input_file_type": "fasta",
        "pdb_id": "1ABC",
        **extra,
    }


def _wire(monkeypatch) -> _Recorder:
    rec = _Recorder()
    monkeypatch.setattr(service, "get_supabase", lambda: rec)
    return rec


def test_fasta_upload_persists_the_real_sequence(monkeypatch) -> None:
    rec = _wire(monkeypatch)

    service.create_research_object(_base_payload(fasta_text=">os\nACGTACGTAA\n"))

    # The sequence itself is the whole point: without it the pipeline halts at input.
    assert rec.inserted["sequence"] == "ACGTACGTAA"
    # Fields derived from the upload must win over the placeholders.
    assert rec.inserted["sequence_length"] == 10
    assert rec.inserted["gc_content"] == 0.4
    assert rec.inserted["fasta_preview"] == "ACGTACGTAA"


def test_fasta_text_is_not_persisted_as_a_column(monkeypatch) -> None:
    # fasta_text is upload input, not a research_objects column — inserting it
    # would fail against the real schema.
    rec = _wire(monkeypatch)

    service.create_research_object(_base_payload(fasta_text=">os\nACGT\n"))

    assert "fasta_text" not in rec.inserted


def test_ro_hash_is_content_addressed(monkeypatch) -> None:
    # Reproducibility is the product claim: identical uploads must hash identically,
    # and a different sequence must not collide with the mock placeholder.
    rec_a = _wire(monkeypatch)
    service.create_research_object(_base_payload(fasta_text=">a\nACGTACGT\n"))
    hash_a = rec_a.inserted["ro_hash"]

    rec_b = _wire(monkeypatch)
    service.create_research_object(_base_payload(fasta_text=">b-different-header\nACGTACGT\n"))
    hash_b = rec_b.inserted["ro_hash"]

    rec_c = _wire(monkeypatch)
    service.create_research_object(_base_payload(fasta_text=">c\nTTTTTTTT\n"))
    hash_c = rec_c.inserted["ro_hash"]

    assert hash_a.startswith("sha256:")
    assert hash_a == hash_b  # same bases, different header -> same hash
    assert hash_a != hash_c  # different bases -> different hash
    assert "mock" not in hash_a


def test_rna_upload_is_normalized_to_dna(monkeypatch) -> None:
    # The engine matches guides against ACGT; a U would never match.
    rec = _wire(monkeypatch)

    service.create_research_object(_base_payload(fasta_text=">rna\nACGUACGU\n"))

    assert rec.inserted["sequence"] == "ACGTACGT"


def test_without_fasta_no_sequence_is_stored(monkeypatch) -> None:
    # Back-compat: creating without an upload still works, but stores no sequence
    # so the pipeline fails honestly at input instead of fabricating a result.
    rec = _wire(monkeypatch)

    service.create_research_object(_base_payload())

    assert rec.inserted.get("sequence") is None
    assert rec.inserted["ro_hash"].startswith("sha256:mock_")


def test_malformed_fasta_raises(monkeypatch) -> None:
    # Surfaced by the route as a 400 rather than persisting an unusable object.
    _wire(monkeypatch)

    with pytest.raises(ValueError):
        service.create_research_object(_base_payload(fasta_text=">bad\nACGTXZ\n"))
