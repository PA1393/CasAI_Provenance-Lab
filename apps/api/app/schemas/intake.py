"""Public intake API schemas that omit original biological payload bytes."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import (
    MAX_INPUT_BYTES,
    Contract,
    FieldValue,
    MissingField,
    MoleculeType,
    ProcessingNotice,
)
from app.modules.information_processor.references import ReferenceContig


class SequenceInspectBody(Contract):
    declared_format: Literal["fasta", "pasted_sequence"]
    content: str = Field(min_length=1, max_length=MAX_INPUT_BYTES)
    molecule_type: MoleculeType | None = None
    rna_to_dna: bool = Field(default=False, strict=True)
    accession: str | None = None
    gene_symbol: str | None = None
    organism: str | None = None
    transcript: str | None = None
    reference_assembly: str | None = None


class ArtifactSummary(Contract):
    filename: str
    role: Literal["reads", "mate_reads", "variants", "reference"]
    compression: Literal["none", "gzip"]
    checksum: str
    byte_length: int


class SequenceRecordSummary(Contract):
    record_id: str
    molecule_type: MoleculeType
    sequence_length: int
    checksum: str


class SequenceDraftSummary(Contract):
    kind: Literal["sequence"] = "sequence"
    schema_version: str
    status: Literal["draft"]
    executable: Literal[False]
    input_method: Literal["fasta", "pasted_sequence"]
    artifact_checksum: str
    artifact_byte_length: int
    normalized_checksum: str
    records: tuple[SequenceRecordSummary, ...]
    warnings: tuple[ProcessingNotice, ...]
    missing_fields: tuple[MissingField, ...]
    ready_for_confirmation: bool


class DatasetDraftSummary(Contract):
    kind: Literal["dataset"] = "dataset"
    schema_version: str
    status: Literal["draft"]
    executable: Literal[False]
    declared_format: Literal["fastq", "vcf"]
    data_role: Literal["reads", "variants"]
    format_version: str
    normalized_checksum: str
    record_count: int
    artifacts: tuple[ArtifactSummary, ...]
    sample_id: FieldValue[str]
    quality_encoding: FieldValue[Literal["phred33"]]
    reference_assembly: FieldValue[str]
    reference_checked: bool
    reference_sequence_checksum: str | None
    sample_names: tuple[str, ...]
    warnings: tuple[ProcessingNotice, ...]
    missing_fields: tuple[MissingField, ...]


DraftSummary = Annotated[SequenceDraftSummary | DatasetDraftSummary, Field(discriminator="kind")]


class IntakeInspectionResponse(Contract):
    declared_format: Literal["fasta", "pasted_sequence", "fastq", "vcf"]
    outcome: Literal["accepted", "rejected"]
    draft: DraftSummary | None = None
    issue: ProcessingNotice | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> IntakeInspectionResponse:
        if self.outcome == "accepted" and (self.draft is None or self.issue is not None):
            raise ValueError("Accepted API response requires only a draft summary")
        if self.outcome == "rejected" and (self.issue is None or self.draft is not None):
            raise ValueError("Rejected API response requires only an issue")
        return self


class ReferenceDraftSummary(Contract):
    schema_version: str
    status: Literal["draft"]
    executable: Literal[False]
    resolver: Literal["supplied-fasta"]
    artifact: ArtifactSummary
    assembly: FieldValue[str]
    accession_version: FieldValue[str]
    contigs: tuple[ReferenceContig, ...]
    sequence_checksum: str
    warnings: tuple[ProcessingNotice, ...]
    missing_fields: tuple[MissingField, ...]
    ready_for_confirmation: bool


class ReferenceInspectionResponse(Contract):
    outcome: Literal["accepted", "rejected"]
    draft: ReferenceDraftSummary | None = None
    issue: ProcessingNotice | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> ReferenceInspectionResponse:
        if self.outcome == "accepted" and (self.draft is None or self.issue is not None):
            raise ValueError("Accepted reference response requires only a draft summary")
        if self.outcome == "rejected" and (self.issue is None or self.draft is not None):
            raise ValueError("Rejected reference response requires only an issue")
        return self
