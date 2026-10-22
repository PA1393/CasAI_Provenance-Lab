"""Local artifact/draft persistence tests; no database, network or confirmation."""

import base64
import errno
import json
import os

import pytest

from app.modules.information_processor.contracts import IntakeRequest, ResearchDraft
from app.modules.information_processor.dataset_parser import process_fastq, process_vcf
from app.modules.information_processor.datasets import DatasetDraft
from app.modules.information_processor.processing import process_input
from app.modules.information_processor.references import (
    ReferenceDraft,
    SuppliedReferenceRequest,
    resolve_supplied_reference,
)
from app.modules.information_processor.workspace import (
    DraftNotFoundError,
    LocalWorkspace,
    WorkspaceIntegrityError,
)


def _sequence(content: str = ">source\r\nacgt\r\n") -> ResearchDraft:
    return process_input(
        IntakeRequest(input_method="fasta", content=content, molecule_type="DNA")
    )


def test_workspace_falls_back_to_exclusive_creation_without_hard_links(tmp_path, monkeypatch):
    def unsupported(*args):
        raise OSError(errno.EOPNOTSUPP, "links unsupported")

    monkeypatch.setattr(os, "link", unsupported)
    workspace = LocalWorkspace(tmp_path)
    draft = _sequence()
    first = workspace.save_draft(draft)
    assert workspace.save_draft(draft) == first
    assert workspace.load_draft(first.draft_id) == draft
    assert not tuple(tmp_path.rglob(".casai-*"))


@pytest.mark.parametrize("same_bytes", [True, False])
def test_exclusive_fallback_never_overwrites_a_racing_writer(tmp_path, monkeypatch, same_bytes):
    target = tmp_path / "object"
    winner = b"expected" if same_bytes else b"other"

    def race(source, destination):
        target.write_bytes(winner)
        raise OSError(errno.EOPNOTSUPP, "links unsupported")

    monkeypatch.setattr(os, "link", race)
    if same_bytes:
        LocalWorkspace._atomic_create(target, b"expected")
    else:
        with pytest.raises(WorkspaceIntegrityError, match="conflicting bytes"):
            LocalWorkspace._atomic_create(target, b"expected")
    assert target.read_bytes() == winner


def test_link_race_cannot_accept_a_symlink_even_with_identical_bytes(tmp_path, monkeypatch):
    target = tmp_path / "object"
    outside = tmp_path / "outside"
    outside.write_bytes(b"expected")

    def race(source, destination):
        target.symlink_to(outside)
        raise FileExistsError

    monkeypatch.setattr(os, "link", race)
    with pytest.raises(WorkspaceIntegrityError, match="conflicting bytes"):
        LocalWorkspace._atomic_create(target, b"expected")
    assert outside.read_bytes() == b"expected"


def _fastq() -> DatasetDraft:
    return process_fastq(
        b"@r\nAC\n+\nII\n", sample_id="sample-a", quality_encoding="phred33"
    )


def _vcf() -> DatasetDraft:
    content = (
        b"##fileformat=VCFv4.3\n"
        b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        b"chr1\t2\t.\tC\tT\t.\tPASS\t.\n"
    )
    return process_vcf(
        content,
        reference_content=b">chr1\nACGT\n",
        reference_assembly="demo",
    )


def _reference() -> ReferenceDraft:
    return resolve_supplied_reference(
        SuppliedReferenceRequest(
            content=b">chr1\nACGT\n",
            assembly="demo",
            accession_version="NC_000001.11",
        )
    )


@pytest.mark.parametrize("factory", [_sequence, _fastq, _vcf, _reference])
def test_save_and_reopen_every_draft_kind_preserves_exact_contract(tmp_path, factory):
    workspace = LocalWorkspace(tmp_path / "project")
    draft = factory()
    manifest = workspace.save_draft(draft)

    reopened = workspace.load_draft(manifest.draft_id)
    assert reopened == draft
    assert reopened.executable is False
    assert workspace.manifest_path(manifest.draft_id).is_file()
    for artifact in manifest.artifacts:
        assert workspace.artifact_path(artifact.checksum).is_file()


def test_same_draft_is_idempotent_and_artifacts_are_content_addressed(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    first = workspace.save_draft(_sequence())
    second = workspace.save_draft(_sequence())

    assert first == second
    assert len(tuple((tmp_path / "artifacts" / "sha256").glob("*/*"))) == 1
    assert len(tuple((tmp_path / "drafts").glob("*.json"))) == 1
    assert not tuple(tmp_path.rglob(".casai-*"))


def test_exact_artifact_formatting_changes_draft_identity_but_not_normalized_identity(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    first = workspace.save_draft(_sequence(">source\nACGT\n"))
    second = workspace.save_draft(_sequence(">source\r\nacgt\r\n"))

    assert first.draft_id != second.draft_id
    assert first.normalized_checksum == second.normalized_checksum
    assert {artifact.checksum for artifact in (*first.artifacts, *second.artifacts)} == {
        _sequence(">source\nACGT\n").original_artifact.checksum,
        _sequence(">source\r\nacgt\r\n").original_artifact.checksum,
    }


def test_manifest_uses_artifact_references_not_embedded_original_bytes(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft = _sequence()
    manifest = workspace.save_draft(draft)
    stored = workspace.manifest_path(manifest.draft_id).read_text()

    assert '"$artifact"' in stored
    assert draft.original_artifact.checksum in stored
    encoded = base64.b64encode(draft.original_artifact.content).decode("ascii")
    assert encoded not in stored


def test_corrupt_artifact_is_detected_and_never_overwritten(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft = _sequence()
    manifest = workspace.save_draft(draft)
    path = workspace.artifact_path(manifest.artifacts[0].checksum)
    path.write_bytes(b"corrupt")

    with pytest.raises(WorkspaceIntegrityError, match="integrity check"):
        workspace.load_draft(manifest.draft_id)
    with pytest.raises(WorkspaceIntegrityError, match="conflicting bytes"):
        workspace.save_draft(draft)
    assert path.read_bytes() == b"corrupt"


def test_corrupt_or_forged_manifest_is_detected(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    manifest = workspace.save_draft(_fastq())
    path = workspace.manifest_path(manifest.draft_id)
    data = json.loads(path.read_text())
    data["normalized_checksum"] = "sha256:" + "0" * 64
    path.write_text(json.dumps(data))

    with pytest.raises(WorkspaceIntegrityError, match="manifest failed validation"):
        workspace.load_draft(manifest.draft_id)


@pytest.mark.parametrize(
    "identity",
    ["../outside", "sha256:../outside", "sha256:" + "0" * 63, "not-a-checksum"],
)
def test_untrusted_identifiers_cannot_escape_workspace(tmp_path, identity):
    workspace = LocalWorkspace(tmp_path)
    with pytest.raises(WorkspaceIntegrityError, match="SHA-256"):
        workspace.load_draft(identity)


def test_missing_draft_is_distinct_from_integrity_failure(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    identity = "sha256:" + "0" * 64
    with pytest.raises(DraftNotFoundError):
        workspace.load_draft(identity)


def test_workspace_rejects_symlinked_internal_directory(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "project"
    root.mkdir()
    (root / "drafts").symlink_to(outside, target_is_directory=True)

    with pytest.raises(WorkspaceIntegrityError, match="symbolic links"):
        LocalWorkspace(root)
