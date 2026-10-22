"""Explicit confirmation and immutable versions for sequence research drafts."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import (
    ClaimType,
    Contract,
    FieldValue,
    InputMethod,
    MissingField,
    ProcessingNotice,
    ResearchDraft,
    SequenceRecord,
    checksum,
)
from app.modules.information_processor.workspace import LocalWorkspace


class ConfirmationError(RuntimeError):
    """A draft cannot be confirmed against the submitted review decision."""


class ArtifactReference(Contract):
    checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    byte_length: int = Field(ge=0, strict=True)
    source: str = Field(min_length=1)
    claim_type: ClaimType


class ConfirmationRequest(Contract):
    source_draft_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_normalized_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_artifact_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    actor_id: str = Field(min_length=1, max_length=200)
    decision: Literal["approve"]
    acknowledged_warning_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_review(self) -> ConfirmationRequest:
        if not self.actor_id.strip():
            raise ValueError("Confirmation actor must be nonempty")
        if any(not code.strip() for code in self.acknowledged_warning_codes):
            raise ValueError("Acknowledged warning codes must be nonempty")
        if tuple(sorted(set(self.acknowledged_warning_codes))) != self.acknowledged_warning_codes:
            raise ValueError("Acknowledged warning codes must be unique and sorted")
        return self


class ConfirmationApproval(Contract):
    actor_id: str = Field(min_length=1, max_length=200)
    decision: Literal["approved"] = "approved"
    acknowledged_warning_codes: tuple[str, ...] = ()


class ConfirmedResearchSnapshot(Contract):
    input_method: InputMethod
    records: tuple[SequenceRecord, ...]
    accession: FieldValue[str]
    gene_symbol: FieldValue[str]
    organism: FieldValue[str]
    transcript: FieldValue[str]
    reference_assembly: FieldValue[str]
    objective: FieldValue[str]
    warnings: tuple[ProcessingNotice, ...] = ()
    remaining_missing_fields: tuple[MissingField, ...] = ()

    @model_validator(mode="after")
    def validate_complete_snapshot(self) -> ConfirmedResearchSnapshot:
        if not self.records:
            raise ValueError("A confirmed research object requires sequence records")
        if any(record.molecule_type.value is None for record in self.records):
            raise ValueError("Every confirmed sequence requires a molecule type")
        if any(field.requirement == "required" for field in self.remaining_missing_fields):
            raise ValueError("Required missing fields block confirmation")
        return self


def _version_identity(values: dict[str, object]) -> str:
    return checksum(
        json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )


class ConfirmedResearchObject(Contract):
    schema_version: Literal["casai.research-object.v1"] = "casai.research-object.v1"
    version_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: Literal["confirmed"] = "confirmed"
    executable: Literal[True] = True
    source_draft_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    draft_schema_version: Literal["casai.intake.v1"] = "casai.intake.v1"
    normalization_version: Literal["1"] = "1"
    normalized_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_artifact: ArtifactReference
    snapshot: ConfirmedResearchSnapshot
    approval: ConfirmationApproval

    @model_validator(mode="after")
    def validate_identity(self) -> ConfirmedResearchObject:
        warning_codes = tuple(sorted({warning.code for warning in self.snapshot.warnings}))
        if self.approval.acknowledged_warning_codes != warning_codes:
            raise ValueError("Approval must acknowledge the exact warning set")
        values = self.model_dump(round_trip=True, exclude={"version_id"})
        if self.version_id != _version_identity(values):
            raise ValueError("Confirmed version identity must match its canonical content")
        return self


def _snapshot(draft: ResearchDraft) -> ConfirmedResearchSnapshot:
    return ConfirmedResearchSnapshot(
        input_method=draft.input_method,
        records=draft.records,
        accession=draft.accession,
        gene_symbol=draft.gene_symbol,
        organism=draft.organism,
        transcript=draft.transcript,
        reference_assembly=draft.reference_assembly,
        objective=draft.objective,
        warnings=draft.warnings,
        remaining_missing_fields=tuple(
            field for field in draft.missing_fields if field.requirement != "required"
        ),
    )


def validate_confirmed_source(
    version: ConfirmedResearchObject,
    draft: ResearchDraft,
) -> None:
    """Verify that a persisted version remains an exact view of its source draft."""

    expected_artifact = ArtifactReference(
        checksum=draft.original_artifact.checksum,
        byte_length=draft.original_artifact.byte_length,
        source=draft.original_artifact.source,
        claim_type=draft.original_artifact.claim_type,
    )
    if (
        draft.schema_version != version.draft_schema_version
        or draft.normalization_version != version.normalization_version
        or draft.normalized_checksum != version.normalized_checksum
        or expected_artifact != version.original_artifact
        or _snapshot(draft) != version.snapshot
    ):
        raise ConfirmationError("Confirmed version no longer matches its source draft")


def _build_version(
    draft: ResearchDraft,
    request: ConfirmationRequest,
) -> ConfirmedResearchObject:
    approval = ConfirmationApproval(
        actor_id=request.actor_id.strip(),
        acknowledged_warning_codes=request.acknowledged_warning_codes,
    )
    values = {
        "schema_version": "casai.research-object.v1",
        "status": "confirmed",
        "executable": True,
        "source_draft_id": request.source_draft_id,
        "draft_schema_version": draft.schema_version,
        "normalization_version": draft.normalization_version,
        "normalized_checksum": draft.normalized_checksum,
        "original_artifact": ArtifactReference(
            checksum=draft.original_artifact.checksum,
            byte_length=draft.original_artifact.byte_length,
            source=draft.original_artifact.source,
            claim_type=draft.original_artifact.claim_type,
        ),
        "snapshot": _snapshot(draft),
        "approval": approval,
    }
    serializable = {
        key: value.model_dump(mode="json", round_trip=True)
        if isinstance(value, Contract)
        else value
        for key, value in values.items()
    }
    return ConfirmedResearchObject(version_id=_version_identity(serializable), **values)


def confirm_research_draft(
    workspace: LocalWorkspace,
    request: ConfirmationRequest,
) -> ConfirmedResearchObject:
    """Approve exactly one stored sequence draft; no values are guessed or rewritten."""

    draft = workspace.load_draft(request.source_draft_id)
    if not isinstance(draft, ResearchDraft):
        raise ConfirmationError("Only a sequence research draft can become a research object")
    if draft.normalized_checksum != request.expected_normalized_checksum:
        raise ConfirmationError("Draft normalized identity changed before confirmation")
    if draft.original_artifact.checksum != request.expected_artifact_checksum:
        raise ConfirmationError("Original artifact identity changed before confirmation")
    if not draft.ready_for_confirmation:
        raise ConfirmationError("Required information must be resolved before confirmation")
    warning_codes = tuple(sorted({warning.code for warning in draft.warnings}))
    if request.acknowledged_warning_codes != warning_codes:
        raise ConfirmationError("Confirmation must acknowledge the exact warning set")

    version = _build_version(draft, request)
    workspace.save_confirmed_version(version)
    return version
