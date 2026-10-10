from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

CONTRACT_SCHEMA_VERSION = 1
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class SourceKind(StrEnum):
    CUSTOMER_UPLOAD = "customer_upload"
    PASTED_SEQUENCE = "pasted_sequence"
    REFERENCE_ACCESSION = "reference_accession"
    CURATED_DATASET = "curated_dataset"
    GENERATED = "generated"


class Visibility(StrEnum):
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunStage(StrEnum):
    INPUT = "input"
    FIELDS = "fields"
    EXTRACT = "extract"
    SIMULATE = "simulate"
    SCORE = "score"
    RESULTS = "results"
    SUMMARY = "summary"


class ProvenanceStage(StrEnum):
    INPUT = "input"
    FIELDS = "fields"
    EXTRACT = "extract"
    SIMULATE = "simulate"
    SCORE = "score"
    RESULTS = "results"


class ActorType(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ENGINE = "engine"


class ApprovalScope(StrEnum):
    INPUT = "input"
    PLAN = "plan"
    EXPORT = "export"
    COMMERCIAL_USE = "commercial_use"


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    LOCKED = "locked"


class RightsScope(StrEnum):
    RESEARCH_USE = "research_use"
    COMMERCIAL_LICENSE = "commercial_license"


class RightsStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class PermissionBasis(StrEnum):
    EXPLICIT_CONSENT = "explicit_consent"
    CUSTOMER_TERMS = "customer_terms"
    PUBLIC_LICENSE = "public_license"
    OWNED = "owned"
    CUSTOM_AGREEMENT = "custom_agreement"


class ContractRecord(BaseModel):
    schema_version: int = Field(default=CONTRACT_SCHEMA_VERSION, ge=1)


class SourceRecord(ContractRecord):
    source_id: UUID
    source_version_id: UUID
    version: int = Field(ge=1)
    source_kind: SourceKind
    owner_ref: str = Field(min_length=1)
    visibility: Visibility = Visibility.PRIVATE
    sha256: Sha256 | None = None
    locator: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    supersedes_source_version_id: UUID | None = None
    created_at: datetime


class ArtifactRecord(ContractRecord):
    artifact_id: UUID
    artifact_version_id: UUID
    version: int = Field(ge=1)
    artifact_type: str = Field(min_length=1)
    owner_ref: str = Field(min_length=1)
    visibility: Visibility = Visibility.PRIVATE
    sha256: Sha256
    byte_size: int = Field(ge=0)
    media_type: str = Field(min_length=1)
    storage_uri: str = Field(min_length=1)
    run_id: UUID | None = None
    source_version_id: UUID | None = None
    engine_version_id: UUID | None = None
    supersedes_artifact_version_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class EngineVersion(ContractRecord):
    engine_version_id: UUID
    engine_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    executable_digest: Sha256 | None = None
    capabilities: tuple[str, ...] = ()
    enabled: bool = True
    created_at: datetime


class ApprovalRecord(ContractRecord):
    approval_id: UUID
    source_version_id: UUID | None = None
    artifact_version_id: UUID | None = None
    run_id: UUID | None = None
    scope: ApprovalScope
    status: ApprovalStatus = ApprovalStatus.DRAFT
    requested_by: str = Field(min_length=1)
    decided_by: str | None = None
    decision_note: str | None = None
    submitted_at: datetime | None = None
    decided_at: datetime | None = None
    locked_at: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def exactly_one_target(self) -> ApprovalRecord:
        targets = (self.source_version_id, self.artifact_version_id, self.run_id)
        if sum(target is not None for target in targets) != 1:
            raise ValueError(
                "an approval must target exactly one source version, artifact version, or run"
            )
        return self


class RightsGrant(ContractRecord):
    rights_grant_id: UUID
    source_version_id: UUID | None = None
    artifact_version_id: UUID | None = None
    run_id: UUID | None = None
    scope: RightsScope
    status: RightsStatus = RightsStatus.ACTIVE
    permission_basis: PermissionBasis
    explicit_permission: bool = False
    granted_by: str = Field(min_length=1)
    evidence_artifact_version_id: UUID | None = None
    effective_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def exactly_one_target(self) -> RightsGrant:
        targets = (self.source_version_id, self.artifact_version_id, self.run_id)
        if sum(target is not None for target in targets) != 1:
            raise ValueError(
                "a rights grant must target exactly one source version, artifact version, or run"
            )
        return self
