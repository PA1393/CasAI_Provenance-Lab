"""Exact supplied-reference contracts and deterministic VCF REF verification."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import ConfigDict, Field, computed_field, model_validator

from app.modules.information_processor.contracts import (
    MAX_INPUT_BYTES,
    MAX_RECORDS,
    Contract,
    FieldValue,
    MissingField,
    ProcessingNotice,
    checksum,
)
from app.modules.information_processor.datasets import DatasetArtifact, VariantRecord
from app.modules.information_processor.parser import InputValidationError, parse_sequences

_CHECKSUM = re.compile(r"sha256:[0-9a-f]{64}", flags=re.ASCII)
_ACCESSION_VERSION = re.compile(r"[A-Za-z0-9_]+\.[0-9]+", flags=re.ASCII)


def _fail(code: str, message: str, record_id: str | None = None) -> None:
    raise InputValidationError(code, message, record_id)


def _selection(value: str | None, source: str) -> FieldValue[str]:
    cleaned = value.strip() if value is not None else None
    return FieldValue(
        value=cleaned or None,
        origin="user_supplied" if cleaned else "unresolved",
        source=source,
    )


class SuppliedReferenceRequest(Contract):
    """Researcher-selected FASTA bytes plus optional identity assertions."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )
    content: bytes
    filename: str = Field(default="reference.fasta", min_length=1)
    assembly: str | None = None
    accession_version: str | None = None
    expected_artifact_checksum: str | None = None
    expected_sequence_checksum: str | None = None
    max_input_bytes: int = Field(default=MAX_INPUT_BYTES, gt=0, strict=True)
    max_records: int = Field(default=MAX_RECORDS, gt=0, strict=True)

    @model_validator(mode="after")
    def validate_explicit_identity(self) -> SuppliedReferenceRequest:
        if self.accession_version is not None and not _ACCESSION_VERSION.fullmatch(
            self.accession_version
        ):
            raise ValueError("Reference accession must include an exact numeric version")
        for value in (self.expected_artifact_checksum, self.expected_sequence_checksum):
            if value is not None and not _CHECKSUM.fullmatch(value):
                raise ValueError("Expected reference checksums must be lowercase SHA-256 values")
        return self


class ReferenceContig(Contract):
    record_id: str = Field(min_length=1)
    description: str | None = None
    sequence_length: int = Field(gt=0, strict=True)
    sequence_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ReferenceDraft(Contract):
    """Exact local reference evidence; identity labels remain unconfirmed selections."""

    schema_version: Literal["casai.reference.v1"] = "casai.reference.v1"
    status: Literal["draft"] = "draft"
    executable: Literal[False] = False
    resolver: Literal["supplied-fasta"] = "supplied-fasta"
    artifact: DatasetArtifact
    assembly: FieldValue[str]
    accession_version: FieldValue[str]
    contigs: tuple[ReferenceContig, ...]
    sequence_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    warnings: tuple[ProcessingNotice, ...] = ()
    missing_fields: tuple[MissingField, ...] = ()

    @model_validator(mode="after")
    def validate_reference(self) -> ReferenceDraft:
        if self.artifact.role != "reference" or self.artifact.compression != "none":
            raise ValueError("Reference draft requires one uncompressed reference artifact")
        identifiers = tuple(contig.record_id for contig in self.contigs)
        if not identifiers or len(set(identifiers)) != len(identifiers):
            raise ValueError("Reference contigs must be nonempty and uniquely identified")
        records = parse_sequences(
            self.artifact.content,
            input_format="fasta",
            molecule_type="DNA",
            max_bytes=self.artifact.byte_length,
            max_records=len(self.contigs),
        )
        expected_contigs = tuple(
            ReferenceContig(
                record_id=record.record_id,
                description=record.description,
                sequence_length=len(record.sequence),
                sequence_checksum=checksum(record.sequence.encode("ascii")),
            )
            for record in records
        )
        if self.contigs != expected_contigs:
            raise ValueError("Reference contig identities must match the retained artifact")
        normalized = {record.record_id: record.sequence for record in records}
        expected_checksum = checksum(
            json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        if self.sequence_checksum != expected_checksum:
            raise ValueError("Reference sequence checksum must match the retained artifact")
        missing = {field.field: field.requirement for field in self.missing_fields}
        if (self.assembly.value is None) != (missing.get("reference_assembly") == "required"):
            raise ValueError("Unresolved reference assembly must remain a required missing field")
        if (self.accession_version.value is None) != (
            missing.get("reference_accession_version") == "recommended"
        ):
            raise ValueError("Unresolved accession must remain a recommended missing field")
        if self.accession_version.value is not None and not _ACCESSION_VERSION.fullmatch(
            self.accession_version.value
        ):
            raise ValueError("Reference accession must include an exact numeric version")
        return self

    @computed_field
    @property
    def ready_for_confirmation(self) -> bool:
        return not any(field.requirement == "required" for field in self.missing_fields)


class ReferenceVerification(Contract):
    reference_artifact_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reference_sequence_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    checked_variant_count: int = Field(ge=0, strict=True)


def resolve_supplied_reference(request: SuppliedReferenceRequest) -> ReferenceDraft:
    """Parse exact local FASTA bytes without retrieval, guessing or confirmation."""

    if len(request.content) > request.max_input_bytes:
        _fail("input_too_large", "Reference exceeds the configured byte budget")
    if request.content.startswith(b"\x1f\x8b"):
        _fail("unsupported_reference_compression", "Reference FASTA must be uncompressed")
    if request.filename.lower().endswith(".gz"):
        _fail("compression_mismatch", "A .gz reference filename requires gzip data")

    artifact = DatasetArtifact(
        filename=request.filename,
        content=request.content,
        compression="none",
        role="reference",
    )
    records = parse_sequences(
        request.content,
        input_format="fasta",
        molecule_type="DNA",
        max_bytes=request.max_input_bytes,
        max_records=request.max_records,
    )
    normalized = {record.record_id: record.sequence for record in records}
    sequence_digest = checksum(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    if (
        request.expected_artifact_checksum is not None
        and request.expected_artifact_checksum != artifact.checksum
    ):
        _fail("reference_artifact_checksum_mismatch", "Reference file checksum does not match")
    if (
        request.expected_sequence_checksum is not None
        and request.expected_sequence_checksum != sequence_digest
    ):
        _fail("reference_sequence_checksum_mismatch", "Reference sequence checksum does not match")

    assembly = _selection(request.assembly, "researcher-selected reference assembly")
    accession = _selection(request.accession_version, "researcher-selected accession version")
    missing = []
    if assembly.value is None:
        missing.append(
            MissingField(
                field="reference_assembly",
                requirement="required",
                reason="Reference assembly is unresolved",
                action="Select the exact assembly for this reference",
            )
        )
    if accession.value is None:
        missing.append(
            MissingField(
                field="reference_accession_version",
                requirement="recommended",
                reason="No accession version identifies the supplied reference",
                action="Record an exact accession version when one exists",
            )
        )
    warnings = tuple(warning for record in records for warning in record.warnings) + (
        ProcessingNotice(
            code="reference_identity_unconfirmed",
            message="Supplied reference labels are researcher assertions pending confirmation",
        ),
    )
    return ReferenceDraft(
        artifact=artifact,
        assembly=assembly,
        accession_version=accession,
        contigs=tuple(
            ReferenceContig(
                record_id=record.record_id,
                description=record.description,
                sequence_length=len(record.sequence),
                sequence_checksum=checksum(record.sequence.encode("ascii")),
            )
            for record in records
        ),
        sequence_checksum=sequence_digest,
        warnings=warnings,
        missing_fields=tuple(missing),
    )


def verify_variant_reference(
    reference: ReferenceDraft,
    variants: tuple[VariantRecord, ...],
) -> ReferenceVerification:
    """Verify every VCF REF allele against the exact resolved local reference."""

    records = parse_sequences(
        reference.artifact.content,
        input_format="fasta",
        molecule_type="DNA",
        max_bytes=reference.artifact.byte_length,
        max_records=len(reference.contigs),
    )
    sequences = {record.record_id: record.sequence for record in records}
    for variant in variants:
        sequence = sequences.get(variant.contig)
        if sequence is None:
            _fail("reference_contig_missing", f"Reference lacks contig {variant.contig}")
        start = variant.position - 1
        if sequence[start : start + len(variant.reference)] != variant.reference:
            _fail(
                "reference_mismatch",
                f"REF does not match supplied sequence at {variant.contig}:{variant.position}",
            )
    return ReferenceVerification(
        reference_artifact_checksum=reference.artifact.checksum,
        reference_sequence_checksum=reference.sequence_checksum,
        checked_variant_count=len(variants),
    )
