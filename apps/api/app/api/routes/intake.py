"""Bounded HTTP adapters for the pure Information Processor intake services."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Response, UploadFile
from pydantic import ValidationError

from app.core.config import settings
from app.modules.information_processor.confirmation import (
    ConfirmationError,
    ConfirmationRequest,
    ConfirmedResearchObject,
    confirm_research_draft,
)
from app.modules.information_processor.contracts import (
    MAX_INPUT_BYTES,
    IntakeRequest,
    ProcessingNotice,
    ResearchDraft,
)
from app.modules.information_processor.intake import (
    FastqInspectionRequest,
    IntakeInspection,
    SequenceInspectionRequest,
    VcfInspectionRequest,
    inspect_input,
)
from app.modules.information_processor.parser import (
    InputValidationError,
    detect_input,
    encode_input,
)
from app.modules.information_processor.processing import process_input
from app.modules.information_processor.references import (
    ReferenceDraft,
    SuppliedReferenceRequest,
    resolve_supplied_reference,
)
from app.modules.information_processor.workspace import (
    DraftNotFoundError,
    LocalWorkspace,
    WorkspaceError,
)
from app.schemas.intake import (
    ArtifactSummary,
    ConfirmationBody,
    ConfirmedResearchSummary,
    DatasetDraftSummary,
    DetectionBody,
    DetectionResponse,
    IntakeInspectionResponse,
    MissingFieldsResponse,
    ReferenceDraftSummary,
    ReferenceInspectionResponse,
    SequenceDraftSummary,
    SequenceInspectBody,
    SequenceRecordSummary,
    StoredSequenceDraftResponse,
)

router = APIRouter(prefix="/intake", tags=["intake"])
_TOO_LARGE = {
    "compression_ratio_exceeded",
    "decoded_input_too_large",
    "input_too_large",
    "line_too_large",
    "too_many_lines",
    "too_many_records",
}
_SHA256_PATH = r"^sha256:[0-9a-f]{64}$"


def get_intake_workspace() -> LocalWorkspace:
    """Construct the configured local store; dependency overrides isolate tests."""

    return LocalWorkspace(settings.intake_workspace_root)


def _artifact_summary(artifact) -> ArtifactSummary:
    return ArtifactSummary(
        filename=artifact.filename,
        role=artifact.role,
        compression=artifact.compression,
        checksum=artifact.checksum,
        byte_length=artifact.byte_length,
    )


def _sequence_summary(draft: ResearchDraft) -> SequenceDraftSummary:
    return SequenceDraftSummary(
        schema_version=draft.schema_version,
        status=draft.status,
        executable=draft.executable,
        input_method=draft.input_method,
        artifact_checksum=draft.original_artifact.checksum,
        artifact_byte_length=draft.original_artifact.byte_length,
        normalized_checksum=draft.normalized_checksum,
        records=tuple(
            SequenceRecordSummary(
                record_id=record.record_id.value,
                molecule_type=record.molecule_type.value,
                sequence_length=record.sequence_length,
                checksum=record.checksum,
            )
            for record in draft.records
        ),
        warnings=draft.warnings,
        missing_fields=draft.missing_fields,
        ready_for_confirmation=draft.ready_for_confirmation,
    )


def _confirmed_summary(version: ConfirmedResearchObject) -> ConfirmedResearchSummary:
    return ConfirmedResearchSummary(
        schema_version=version.schema_version,
        version_id=version.version_id,
        source_draft_id=version.source_draft_id,
        status=version.status,
        executable=version.executable,
        normalized_checksum=version.normalized_checksum,
        original_artifact_checksum=version.original_artifact.checksum,
        records=tuple(
            SequenceRecordSummary(
                record_id=record.record_id.value,
                molecule_type=record.molecule_type.value,
                sequence_length=record.sequence_length,
                checksum=record.checksum,
            )
            for record in version.snapshot.records
        ),
        approved_by=version.approval.actor_id,
        acknowledged_warning_codes=version.approval.acknowledged_warning_codes,
    )


def _inspection_response(result: IntakeInspection) -> IntakeInspectionResponse:
    if result.issue is not None:
        return IntakeInspectionResponse(
            declared_format=result.declared_format,
            outcome="rejected",
            issue=result.issue,
        )
    draft = result.draft
    if draft is None:
        raise RuntimeError("Accepted inspection unexpectedly omitted its draft")
    if isinstance(draft, ResearchDraft):
        summary = _sequence_summary(draft)
    else:
        summary = DatasetDraftSummary(
            schema_version=draft.schema_version,
            status=draft.status,
            executable=draft.executable,
            declared_format=draft.declared_format,
            data_role=draft.data_role,
            format_version=draft.format_version,
            normalized_checksum=draft.normalized_checksum,
            record_count=draft.record_count,
            artifacts=tuple(_artifact_summary(artifact) for artifact in draft.artifacts),
            sample_id=draft.sample_id,
            quality_encoding=draft.quality_encoding,
            reference_assembly=draft.reference_assembly,
            reference_checked=draft.reference_checked,
            reference_sequence_checksum=draft.reference_sequence_checksum,
            sample_names=draft.sample_names,
            warnings=draft.warnings,
            missing_fields=draft.missing_fields,
        )
    return IntakeInspectionResponse(
        declared_format=result.declared_format,
        outcome="accepted",
        draft=summary,
    )


def _reference_response(draft: ReferenceDraft) -> ReferenceInspectionResponse:
    return ReferenceInspectionResponse(
        outcome="accepted",
        draft=ReferenceDraftSummary(
            schema_version=draft.schema_version,
            status=draft.status,
            executable=draft.executable,
            resolver=draft.resolver,
            artifact=_artifact_summary(draft.artifact),
            assembly=draft.assembly,
            accession_version=draft.accession_version,
            contigs=draft.contigs,
            sequence_checksum=draft.sequence_checksum,
            warnings=draft.warnings,
            missing_fields=draft.missing_fields,
            ready_for_confirmation=draft.ready_for_confirmation,
        ),
    )


def _set_rejection_status(response: Response, issue: ProcessingNotice) -> None:
    response.status_code = 413 if issue.code in _TOO_LARGE else 400


def _safe_filename(upload: UploadFile, fallback: str) -> str:
    label = (upload.filename or fallback).replace("\\", "/").rsplit("/", 1)[-1]
    label = label.strip() or fallback
    if len(label) > 255 or any(ord(char) < 32 or ord(char) == 127 for char in label):
        raise InputValidationError("invalid_filename", "Upload filename is not a safe label")
    return label


async def _read_bounded(upload: UploadFile) -> bytes:
    content = await upload.read(MAX_INPUT_BYTES + 1)
    if len(content) > MAX_INPUT_BYTES:
        raise InputValidationError("input_too_large", "Uploaded file exceeds the byte budget")
    return content


@router.post("/detect", response_model=DetectionResponse)
def detect_sequence(body: DetectionBody, response: Response) -> DetectionResponse:
    try:
        detection = detect_input(encode_input(body.content))
    except InputValidationError as exc:
        _set_rejection_status(response, exc.issue)
        return DetectionResponse(outcome="rejected", issue=exc.issue)
    return DetectionResponse(outcome="accepted", detection=detection)


@router.post("/research-drafts", response_model=StoredSequenceDraftResponse, status_code=201)
def store_research_draft(
    body: IntakeRequest,
    response: Response,
    workspace: LocalWorkspace = Depends(get_intake_workspace),
) -> StoredSequenceDraftResponse:
    try:
        draft = process_input(body)
        manifest = workspace.save_draft(draft)
    except InputValidationError as exc:
        _set_rejection_status(response, exc.issue)
        return StoredSequenceDraftResponse(outcome="rejected", issue=exc.issue)
    except WorkspaceError:
        response.status_code = 409
        return StoredSequenceDraftResponse(
            outcome="rejected",
            issue=ProcessingNotice(
                code="workspace_conflict",
                message="The local intake workspace could not store this immutable draft",
            ),
        )
    return StoredSequenceDraftResponse(
        outcome="accepted",
        draft_id=manifest.draft_id,
        draft=_sequence_summary(draft),
    )


@router.get("/research-drafts/{draft_id}/missing", response_model=MissingFieldsResponse)
def inspect_missing_fields(
    draft_id: str = Path(pattern=_SHA256_PATH),
    workspace: LocalWorkspace = Depends(get_intake_workspace),
) -> MissingFieldsResponse:
    try:
        draft = workspace.load_draft(draft_id)
    except DraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Research draft not found") from exc
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=409, detail="Research draft failed integrity checks"
        ) from exc
    if not isinstance(draft, ResearchDraft):
        raise HTTPException(
            status_code=400, detail="Stored object is not a sequence research draft"
        )
    return MissingFieldsResponse(
        draft_id=draft_id,
        ready_for_confirmation=draft.ready_for_confirmation,
        warnings=draft.warnings,
        missing_fields=draft.missing_fields,
    )


@router.post(
    "/research-drafts/{draft_id}/confirm",
    response_model=ConfirmedResearchSummary,
    status_code=201,
)
def confirm_stored_research_draft(
    body: ConfirmationBody,
    draft_id: str = Path(pattern=_SHA256_PATH),
    workspace: LocalWorkspace = Depends(get_intake_workspace),
) -> ConfirmedResearchSummary:
    try:
        version = confirm_research_draft(
            workspace,
            ConfirmationRequest(
                source_draft_id=draft_id,
                expected_normalized_checksum=body.expected_normalized_checksum,
                expected_artifact_checksum=body.expected_artifact_checksum,
                actor_id=body.actor_id,
                decision=body.decision,
                acknowledged_warning_codes=body.acknowledged_warning_codes,
            ),
        )
    except DraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Research draft not found") from exc
    except ConfirmationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=409, detail="Research draft failed integrity checks"
        ) from exc
    return _confirmed_summary(version)


@router.post("/sequences/inspect", response_model=IntakeInspectionResponse)
def inspect_sequence(body: SequenceInspectBody, response: Response) -> IntakeInspectionResponse:
    try:
        content = encode_input(body.content)
    except InputValidationError as exc:
        _set_rejection_status(response, exc.issue)
        return IntakeInspectionResponse(
            declared_format=body.declared_format,
            outcome="rejected",
            issue=exc.issue,
        )
    result = inspect_input(
        SequenceInspectionRequest(
            declared_format=body.declared_format,
            content=content,
            molecule_type=body.molecule_type,
            rna_to_dna=body.rna_to_dna,
            accession=body.accession,
            gene_symbol=body.gene_symbol,
            organism=body.organism,
            transcript=body.transcript,
            reference_assembly=body.reference_assembly,
        )
    )
    if result.issue is not None:
        _set_rejection_status(response, result.issue)
    return _inspection_response(result)


@router.post("/datasets/inspect", response_model=IntakeInspectionResponse)
async def inspect_dataset(
    response: Response,
    declared_format: Literal["fastq", "vcf"] = Form(),
    primary: UploadFile = File(),
    mate: UploadFile | None = File(default=None),
    reference: UploadFile | None = File(default=None),
    sample_id: str | None = Form(default=None),
    quality_encoding: Literal["phred33"] | None = Form(default=None),
    reference_assembly: str | None = Form(default=None),
) -> IntakeInspectionResponse:
    try:
        primary_content = await _read_bounded(primary)
        if declared_format == "fastq":
            if reference is not None or reference_assembly is not None:
                raise InputValidationError(
                    "incompatible_inputs", "FASTQ inspection does not accept a reference"
                )
            result = inspect_input(
                FastqInspectionRequest(
                    content=primary_content,
                    filename=_safe_filename(primary, "reads.fastq"),
                    sample_id=sample_id,
                    quality_encoding=quality_encoding,
                    mate_content=await _read_bounded(mate) if mate is not None else None,
                    mate_filename=_safe_filename(mate, "mate.fastq") if mate is not None else None,
                )
            )
        else:
            if mate is not None or quality_encoding is not None:
                raise InputValidationError(
                    "incompatible_inputs", "VCF inspection does not accept FASTQ mate options"
                )
            result = inspect_input(
                VcfInspectionRequest(
                    content=primary_content,
                    filename=_safe_filename(primary, "variants.vcf"),
                    sample_id=sample_id,
                    reference_assembly=reference_assembly,
                    reference_content=(
                        await _read_bounded(reference) if reference is not None else None
                    ),
                    reference_filename=(
                        _safe_filename(reference, "reference.fasta")
                        if reference is not None
                        else None
                    ),
                )
            )
    except InputValidationError as exc:
        _set_rejection_status(response, exc.issue)
        return IntakeInspectionResponse(
            declared_format=declared_format,
            outcome="rejected",
            issue=exc.issue,
        )
    if result.issue is not None:
        _set_rejection_status(response, result.issue)
    return _inspection_response(result)


@router.post("/references/verify", response_model=ReferenceInspectionResponse)
async def inspect_reference(
    response: Response,
    reference: UploadFile = File(),
    assembly: str | None = Form(default=None),
    accession_version: str | None = Form(default=None),
    expected_artifact_checksum: str | None = Form(default=None),
    expected_sequence_checksum: str | None = Form(default=None),
) -> ReferenceInspectionResponse:
    try:
        draft = resolve_supplied_reference(
            SuppliedReferenceRequest(
                content=await _read_bounded(reference),
                filename=_safe_filename(reference, "reference.fasta"),
                assembly=assembly,
                accession_version=accession_version,
                expected_artifact_checksum=expected_artifact_checksum,
                expected_sequence_checksum=expected_sequence_checksum,
            )
        )
    except InputValidationError as exc:
        _set_rejection_status(response, exc.issue)
        return ReferenceInspectionResponse(outcome="rejected", issue=exc.issue)
    except ValidationError:
        issue = ProcessingNotice(
            code="invalid_reference_selection",
            message="Reference identity or checksum selection is invalid",
        )
        response.status_code = 422
        return ReferenceInspectionResponse(outcome="rejected", issue=issue)
    return _reference_response(draft)
