"""Bounded inspection contracts for reads and variants; never executable source sequences."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import ConfigDict, Field, computed_field, model_validator

from app.modules.information_processor.contracts import (
    DNA_ALPHABET,
    Contract,
    FieldValue,
    MissingField,
    ProcessingNotice,
    checksum,
)


class DatasetArtifact(Contract):
    """Exact original bytes, including compression. Filename is a label, not a path."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, ser_json_bytes="base64", val_json_bytes="base64"
    )
    filename: str = Field(min_length=1)
    content: bytes
    compression: Literal["none", "gzip"]
    role: Literal["reads", "mate_reads", "variants", "reference"]
    claim_type: Literal["user-supplied"] = "user-supplied"

    @computed_field
    @property
    def checksum(self) -> str:
        return checksum(self.content)

    @computed_field
    @property
    def byte_length(self) -> int:
        return len(self.content)


class ReadRecord(Contract):
    record_id: str = Field(min_length=1)
    description: str | None
    sequence: str = Field(min_length=1)
    qualities: str = Field(min_length=1)
    mate: Literal[1, 2] | None = None
    origin: Literal["file_extracted"] = "file_extracted"
    source: str = Field(min_length=1)
    warnings: tuple[ProcessingNotice, ...] = ()

    @model_validator(mode="after")
    def validate_read(self) -> ReadRecord:
        if set(self.sequence) - DNA_ALPHABET or self.sequence != self.sequence.upper():
            raise ValueError("Reads require normalized DNA/IUPAC symbols")
        if len(self.sequence) != len(self.qualities):
            raise ValueError("Read sequence and quality lengths differ")
        if any(not 33 <= ord(char) <= 126 for char in self.qualities):
            raise ValueError("Quality characters must be printable ASCII 33–126")
        return self


class SampleCall(Contract):
    sample: str = Field(min_length=1)
    values: tuple[str, ...]
    genotype: tuple[int | None, ...] | None = None
    phased: bool | None = None


class VariantRecord(Contract):
    contig: str = Field(min_length=1)
    position: int = Field(gt=0, strict=True)
    identifiers: tuple[str, ...] = ()
    reference: str = Field(min_length=1)
    alternatives: tuple[str, ...] = ()
    quality: float | None = Field(default=None, ge=0)
    filters: tuple[str, ...] | None = None
    info: str
    format_keys: tuple[str, ...] = ()
    samples: tuple[SampleCall, ...] = ()
    coordinate_system: Literal["1-based-inclusive"] = "1-based-inclusive"
    origin: Literal["file_extracted"] = "file_extracted"
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_alleles(self) -> VariantRecord:
        for allele in (self.reference, *self.alternatives):
            if not allele or set(allele) - set("ACGTN"):
                raise ValueError("Only explicit A/C/G/T/N alleles are supported")
        if len(set(self.alternatives)) != len(self.alternatives):
            raise ValueError("ALT alleles must be distinct")
        if self.reference in self.alternatives:
            raise ValueError("ALT must differ from REF")
        for sample in self.samples:
            if len(sample.values) != len(self.format_keys):
                raise ValueError("Sample values must correspond to FORMAT keys")
            if sample.genotype is not None and any(
                allele is not None and not 0 <= allele <= len(self.alternatives)
                for allele in sample.genotype
            ):
                raise ValueError("Genotype allele index is outside REF/ALT")
        return self


class DatasetDraft(Contract):
    schema_version: Literal["casai.dataset.v1"] = "casai.dataset.v1"
    adapter_version: Literal["1"] = "1"
    status: Literal["draft"] = "draft"
    executable: Literal[False] = False
    declared_format: Literal["fastq", "vcf"]
    data_role: Literal["reads", "variants"]
    format_version: str
    artifacts: tuple[DatasetArtifact, ...]
    sample_id: FieldValue[str]
    quality_encoding: FieldValue[Literal["phred33"]]
    reference_assembly: FieldValue[str]
    reference_checked: bool = Field(default=False, strict=True)
    reference_sequence_checksum: str | None = None
    reads: tuple[ReadRecord, ...] = ()
    variants: tuple[VariantRecord, ...] = ()
    sample_names: tuple[str, ...] = ()
    metadata_lines: tuple[str, ...] = ()
    warnings: tuple[ProcessingNotice, ...] = ()
    missing_fields: tuple[MissingField, ...] = ()

    @model_validator(mode="after")
    def validate_role(self) -> DatasetDraft:
        roles = tuple(artifact.role for artifact in self.artifacts)
        if self.declared_format == "fastq":
            if self.data_role != "reads" or self.variants or self.reference_checked:
                raise ValueError("FASTQ is a read dataset, not a variant/reference result")
            if roles not in (("reads",), ("reads", "mate_reads")) or not self.reads:
                raise ValueError("FASTQ requires primary reads and an optional mate artifact")
        elif self.data_role != "variants" or self.reads:
            raise ValueError("VCF is a variant dataset, not a source sequence")
        elif roles not in (("variants",), ("variants", "reference")):
            raise ValueError("VCF requires a variant artifact and optional exact reference")
        if self.reference_checked != ("reference" in roles):
            raise ValueError("Reference checking requires a retained reference artifact")
        if self.reference_checked != (self.reference_sequence_checksum is not None):
            raise ValueError("Reference checking requires its normalized sequence checksum")
        sources = {artifact.checksum for artifact in self.artifacts}
        if any(
            record.source.split("#", 1)[0] not in sources
            for record in (*self.reads, *self.variants)
        ):
            raise ValueError("Records must identify one of the retained input artifacts")
        return self

    @computed_field
    @property
    def record_count(self) -> int:
        return len(self.reads) if self.data_role == "reads" else len(self.variants)

    @computed_field
    @property
    def normalized_checksum(self) -> str:
        """Derived inspection identity; attribution bytes and approval stay separate."""
        values = self.model_dump(
            round_trip=True, exclude={"artifacts", "warnings", "missing_fields"}
        )
        for name in ("sample_id", "quality_encoding", "reference_assembly"):
            values[name] = getattr(self, name).value
        for name in ("reads", "variants"):
            for record in values[name]:
                record.pop("source")
                record.pop("origin")
                record.pop("warnings", None)
        return checksum(json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8"))
