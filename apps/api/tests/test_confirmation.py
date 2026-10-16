"""Explicit sequence confirmation and immutable local version tests."""

import json

import pytest
from pydantic import ValidationError

from app.modules.information_processor.confirmation import (
    ConfirmationError,
    ConfirmationRequest,
    ConfirmedResearchObject,
    confirm_research_draft,
)
from app.modules.information_processor.contracts import IntakeRequest
from app.modules.information_processor.dataset_parser import process_fastq
from app.modules.information_processor.processing import process_input
from app.modules.information_processor.workspace import (
    LocalWorkspace,
    WorkspaceIntegrityError,
)


def _stored_sequence(workspace, *, content=">source\nACGT\n", molecule_type="DNA"):
    draft = process_input(
        IntakeRequest(
            input_method="fasta",
            content=content,
            molecule_type=molecule_type,
        )
    )
    manifest = workspace.save_draft(draft)
    return draft, manifest


def _request(draft, manifest, **changes):
    values = {
        "source_draft_id": manifest.draft_id,
        "expected_normalized_checksum": draft.normalized_checksum,
        "expected_artifact_checksum": draft.original_artifact.checksum,
        "actor_id": "local-researcher",
        "decision": "approve",
        "acknowledged_warning_codes": tuple(
            sorted({warning.code for warning in draft.warnings})
        ),
    }
    values.update(changes)
    return ConfirmationRequest(**values)


def test_explicit_confirmation_creates_reopenable_immutable_version(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft, manifest = _stored_sequence(workspace)

    version = confirm_research_draft(workspace, _request(draft, manifest))
    reopened = workspace.load_confirmed_version(version.version_id)

    assert reopened == version
    assert reopened.status == "confirmed"
    assert reopened.executable is True
    assert reopened.source_draft_id == manifest.draft_id
    assert reopened.snapshot.records == draft.records
    assert reopened.original_artifact.checksum == draft.original_artifact.checksum
    assert "content" not in workspace.version_path(version.version_id).read_text()


def test_repeating_the_same_approval_is_idempotent(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft, manifest = _stored_sequence(workspace)
    request = _request(draft, manifest)

    first = confirm_research_draft(workspace, request)
    second = confirm_research_draft(workspace, request)

    assert first == second
    assert len(tuple((tmp_path / "versions").glob("*.json"))) == 1


def test_approval_actor_is_part_of_the_immutable_version_identity(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft, manifest = _stored_sequence(workspace)

    first = confirm_research_draft(workspace, _request(draft, manifest))
    second = confirm_research_draft(
        workspace,
        _request(draft, manifest, actor_id="second-reviewer"),
    )

    assert first.normalized_checksum == second.normalized_checksum
    assert first.version_id != second.version_id


@pytest.mark.parametrize("field", ["expected_normalized_checksum", "expected_artifact_checksum"])
def test_confirmation_rejects_stale_or_mismatched_review_identity(tmp_path, field):
    workspace = LocalWorkspace(tmp_path)
    draft, manifest = _stored_sequence(workspace)
    with pytest.raises(ConfirmationError, match="identity changed"):
        confirm_research_draft(
            workspace,
            _request(draft, manifest, **{field: "sha256:" + "0" * 64}),
        )


def test_required_missing_information_blocks_confirmation(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft, manifest = _stored_sequence(workspace, molecule_type=None)

    with pytest.raises(ConfirmationError, match="Required information"):
        confirm_research_draft(workspace, _request(draft, manifest))
    assert not tuple((tmp_path / "versions").glob("*.json"))


def test_non_sequence_dataset_cannot_be_confirmed_as_research_object(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft = process_fastq(
        b"@r\nAC\n+\nII\n",
        sample_id="sample-a",
        quality_encoding="phred33",
    )
    manifest = workspace.save_draft(draft)
    request = ConfirmationRequest(
        source_draft_id=manifest.draft_id,
        expected_normalized_checksum=draft.normalized_checksum,
        expected_artifact_checksum=draft.artifacts[0].checksum,
        actor_id="local-researcher",
        decision="approve",
    )

    with pytest.raises(ConfirmationError, match="Only a sequence research draft"):
        confirm_research_draft(workspace, request)


def test_confirmation_requires_exact_warning_acknowledgement(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft, manifest = _stored_sequence(workspace, content=">source\nACGN\n")
    assert draft.warnings

    with pytest.raises(ConfirmationError, match="exact warning set"):
        confirm_research_draft(
            workspace,
            _request(draft, manifest, acknowledged_warning_codes=()),
        )


def test_confirmation_request_rejects_implicit_or_ambiguous_approval():
    values = {
        "source_draft_id": "sha256:" + "1" * 64,
        "expected_normalized_checksum": "sha256:" + "2" * 64,
        "expected_artifact_checksum": "sha256:" + "3" * 64,
        "actor_id": "researcher",
    }
    with pytest.raises(ValidationError):
        ConfirmationRequest(**values)
    with pytest.raises(ValidationError, match="unique and sorted"):
        ConfirmationRequest(
            **values,
            decision="approve",
            acknowledged_warning_codes=("b", "a", "a"),
        )


def test_tampered_confirmed_version_is_detected(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft, manifest = _stored_sequence(workspace)
    version = confirm_research_draft(workspace, _request(draft, manifest))
    path = workspace.version_path(version.version_id)
    values = json.loads(path.read_text())
    values["approval"]["actor_id"] = "forged-reviewer"
    path.write_text(json.dumps(values))

    with pytest.raises(WorkspaceIntegrityError, match="failed validation"):
        workspace.load_confirmed_version(version.version_id)


def test_workspace_refuses_version_that_does_not_match_its_source_draft(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    first_draft, first_manifest = _stored_sequence(workspace)
    _, second_manifest = _stored_sequence(workspace, content=">other\nTTTT\n")
    version = confirm_research_draft(workspace, _request(first_draft, first_manifest))
    mismatched = version.model_copy(update={"source_draft_id": second_manifest.draft_id})

    with pytest.raises(WorkspaceIntegrityError, match="no longer matches"):
        workspace.save_confirmed_version(mismatched)


def test_confirmed_contract_rejects_forged_version_identity(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft, manifest = _stored_sequence(workspace)
    version = confirm_research_draft(workspace, _request(draft, manifest))
    values = version.model_dump(round_trip=True)
    values["version_id"] = "sha256:" + "0" * 64

    with pytest.raises(ValidationError, match="canonical content"):
        ConfirmedResearchObject.model_validate(values)
