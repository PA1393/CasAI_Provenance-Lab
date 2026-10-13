"""Serializable intake contracts. No database, model calls, or implicit confirmation."""

from __future__ import annotations

import hashlib
import json
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

MoleculeType = Literal["DNA", "RNA", "protein"]
InputMethod = Literal["fasta", "pasted_sequence", "accession", "gene", "demo", "objective"]
FieldOrigin = Literal[
    "user_supplied",
    "file_extracted",
    "database_retrieved",
    "ai_inferred",
    "system_default",
    "user_confirmed",
    "unresolved",
]
ClaimType = Literal[
    "user-supplied",
    "database-retrieved",
    "AI-inferred",
    "heuristic",
    "predicted",
    "explanatory",
    "experimentally reported",
    "experimentally validated",
    "unresolved",
]
DNA_ALPHABET = frozenset("ACGTNRYSWKMBDHV")
RNA_ALPHABET = frozenset("ACGUNRYSWKMBDHV")
PROTEIN_ALPHABET = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO")
ALPHABETS = {"DNA": DNA_ALPHABET, "RNA": RNA_ALPHABET, "protein": PROTEIN_ALPHABET}
MAX_INPUT_BYTES = 10_000_000
MAX_RECORDS = 1_000
T = TypeVar("T")


def checksum(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class FieldValue(Contract, Generic[T]):
    value: T | None
    origin: FieldOrigin
    source: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    confirmed: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_origin(self) -> FieldValue[T]:
        if (self.value is None) != (self.origin == "unresolved"):
            raise ValueError("Missing values must be unresolved; known values need an origin")
        if self.confirmed != (self.origin == "user_confirmed"):
            raise ValueError("Only an explicit user_confirmed origin may be confirmed")
        if not self.source.strip():
            raise ValueError("Every field must identify its source")
        return self


class IntakeRequest(Contract):
    input_method: InputMethod
    content: str | None = None
    molecule_type: MoleculeType | None = None
    rna_to_dna: bool = Field(default=False, strict=True)
    sequence_origin: Literal["user_supplied", "ai_inferred"] = "user_supplied"
    accession: str | None = None
    gene_symbol: str | None = None
    organism: str | None = None
    transcript: str | None = None
    reference_assembly: str | None = None

    @model_validator(mode="after")
    def validate_conversion(self) -> IntakeRequest:
        if self.rna_to_dna and self.molecule_type != "RNA":
            raise ValueError("RNA-to-DNA conversion requires an explicit RNA declaration")
        if self.input_method == "demo" and self.content is not None:
            raise ValueError("Demo input uses the versioned CasAI fixture, not supplied content")
        if self.input_method in ("accession", "gene") and self.content is not None:
            raise ValueError("Use explicit accession/gene metadata fields for reference intake")
        return self


class ProcessingNotice(Contract):
    code: str
    message: str
    record_id: str | None = None


class InputDetection(Contract):
    detected_method: Literal["fasta", "pasted_sequence", "accession", "unknown"]
    candidate_molecule_types: tuple[MoleculeType, ...] = ()
    requires_confirmation: Literal[True] = True
    reason: str


class MissingField(Contract):
    field: str
    requirement: Literal["required", "recommended", "optional"]
    reason: str
    action: str


class OriginalArtifact(Contract):
    """Exact UTF-8 text bytes, including BOM and line endings, retained in a draft."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )
    content: bytes
    encoding: Literal["utf-8"] = "utf-8"
    source: str
    claim_type: ClaimType

    @computed_field
    @property
    def checksum(self) -> str:
        return checksum(self.content)

    @computed_field
    @property
    def byte_length(self) -> int:
        return len(self.content)


class SequenceRecord(Contract):
    record_id: FieldValue[str]
    description: FieldValue[str]
    sequence: FieldValue[str]
    molecule_type: FieldValue[MoleculeType]
    source_molecule_type: FieldValue[MoleculeType]
    organism: FieldValue[str]
    reference_source: FieldValue[str]
    reference_accession: FieldValue[str]
    reference_assembly: FieldValue[str]
    transcript: FieldValue[str]
    coordinate_system: FieldValue[Literal["1-based-inclusive"]]
    input_method: FieldValue[InputMethod]

    @model_validator(mode="after")
    def validate_sequence(self) -> SequenceRecord:
        sequence = self.sequence.value
        if not sequence or sequence != sequence.upper():
            raise ValueError(
                "A sequence record requires nonempty normalized uppercase bases/residues"
            )
        alphabet = ALPHABETS.get(self.molecule_type.value, PROTEIN_ALPHABET | DNA_ALPHABET)
        if set(sequence) - alphabet:
            raise ValueError("Sequence alphabet does not match the declared molecule type")
        if self.sequence.origin == "ai_inferred":
            raise ValueError("AI-inferred biological sequence cannot be source data")
        if not self.record_id.value:
            raise ValueError("Sequence record identifiers must be nonempty")
        if self.coordinate_system.value != "1-based-inclusive":
            raise ValueError("Internal coordinates must be 1-based and inclusive")
        return self

    @computed_field
    @property
    def checksum(self) -> str:
        return checksum(self.sequence.value.encode("ascii"))

    @computed_field
    @property
    def sequence_length(self) -> int:
        return len(self.sequence.value)


class ResearchDraft(Contract):
    schema_version: Literal["casai.intake.v1"] = "casai.intake.v1"
    normalization_version: Literal["1"] = "1"
    status: Literal["draft"] = "draft"
    executable: Literal[False] = False
    input_method: InputMethod
    original_artifact: OriginalArtifact
    records: tuple[SequenceRecord, ...] = ()
    accession: FieldValue[str]
    gene_symbol: FieldValue[str]
    organism: FieldValue[str]
    transcript: FieldValue[str]
    reference_assembly: FieldValue[str]
    objective: FieldValue[str]
    warnings: tuple[ProcessingNotice, ...] = ()
    missing_fields: tuple[MissingField, ...] = ()

    @computed_field
    @property
    def ready_for_confirmation(self) -> bool:
        return (
            bool(self.records)
            and all(record.molecule_type.value is not None for record in self.records)
            and not any(field.requirement == "required" for field in self.missing_fields)
        )

    @computed_field
    @property
    def normalized_checksum(self) -> str:
        """Hash normalized values; byte formatting and field attribution stay in the artifact.

        This identifies a draft's scientific payload, not an approved/executable version.
        Record order, identifiers, molecule semantics, metadata and objectives are significant.
        """
        record_values = [
            {name: getattr(record, name).value for name in SequenceRecord.model_fields}
            for record in self.records
        ]
        payload = {
            "schema_version": self.schema_version,
            "normalization_version": self.normalization_version,
            "input_method": self.input_method,
            "records": record_values,
            **{
                name: getattr(self, name).value
                for name in (
                    "accession",
                    "gene_symbol",
                    "organism",
                    "transcript",
                    "reference_assembly",
                    "objective",
                )
            },
        }
        return checksum(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        )
