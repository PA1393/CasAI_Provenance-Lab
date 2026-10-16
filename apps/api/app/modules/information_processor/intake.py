"""Transport-neutral orchestration for bounded sequence and dataset inspection."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from app.modules.information_processor.contracts import (
    MAX_INPUT_BYTES,
    Contract,
    IntakeRequest,
    MoleculeType,
    ProcessingNotice,
    ResearchDraft,
)
from app.modules.information_processor.dataset_parser import (
    DatasetLimits,
    process_fastq,
    process_vcf,
)
from app.modules.information_processor.datasets import DatasetDraft
from app.modules.information_processor.parser import InputValidationError, decode_input
from app.modules.information_processor.processing import process_input
from app.modules.information_processor.structure_parser import (
    StructureLimits,
    process_mmcif,
    process_pdb,
)
from app.modules.information_processor.structures import StructureDraft


class InspectionRequest(Contract):
    """Base request that retains exact source bytes without transport assumptions."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )
    content: bytes


class SequenceInspectionRequest(InspectionRequest):
    declared_format: Literal["fasta", "pasted_sequence"]
    molecule_type: MoleculeType | None = None
    rna_to_dna: bool = Field(default=False, strict=True)
    accession: str | None = None
    gene_symbol: str | None = None
    organism: str | None = None
    transcript: str | None = None
    reference_assembly: str | None = None
    max_bytes: int = Field(default=MAX_INPUT_BYTES, gt=0, strict=True)


class FastqInspectionRequest(InspectionRequest):
    declared_format: Literal["fastq"] = "fastq"
    filename: str = Field(default="reads.fastq", min_length=1)
    sample_id: str | None = None
    quality_encoding: Literal["phred33"] | None = None
    mate_content: bytes | None = None
    mate_filename: str | None = Field(default=None, min_length=1)
    limits: DatasetLimits = DatasetLimits()

    @model_validator(mode="after")
    def validate_mate_label(self) -> FastqInspectionRequest:
        if self.mate_filename is not None and self.mate_content is None:
            raise ValueError("mate_filename requires mate_content")
        return self


class VcfInspectionRequest(InspectionRequest):
    declared_format: Literal["vcf"] = "vcf"
    filename: str = Field(default="variants.vcf", min_length=1)
    sample_id: str | None = None
    reference_assembly: str | None = None
    reference_content: bytes | None = None
    limits: DatasetLimits = DatasetLimits()


class PdbInspectionRequest(InspectionRequest):
    declared_format: Literal["pdb"] = "pdb"
    filename: str = Field(default="structure.pdb", min_length=1)
    limits: StructureLimits = StructureLimits()


class MmcifInspectionRequest(InspectionRequest):
    declared_format: Literal["mmcif"] = "mmcif"
    filename: str = Field(default="structure.cif", min_length=1)
    limits: StructureLimits = StructureLimits()


IntakeInspectionRequest = Annotated[
    SequenceInspectionRequest
    | FastqInspectionRequest
    | VcfInspectionRequest
    | PdbInspectionRequest
    | MmcifInspectionRequest,
    Field(discriminator="declared_format"),
]
InspectionDraft = ResearchDraft | DatasetDraft | StructureDraft


class IntakeInspection(Contract):
    """One reviewable outcome: either a non-executable draft or one rejection issue."""

    declared_format: Literal["fasta", "pasted_sequence", "fastq", "vcf", "pdb", "mmcif"]
    outcome: Literal["accepted", "rejected"]
    draft: InspectionDraft | None = None
    issue: ProcessingNotice | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> IntakeInspection:
        if self.outcome == "accepted" and (self.draft is None or self.issue is not None):
            raise ValueError("Accepted inspection requires only a draft")
        if self.outcome == "rejected" and (self.issue is None or self.draft is not None):
            raise ValueError("Rejected inspection requires only an issue")
        if isinstance(self.draft, ResearchDraft):
            expected = self.draft.input_method
        elif isinstance(self.draft, DatasetDraft):
            expected = self.draft.declared_format
        elif isinstance(self.draft, StructureDraft):
            expected = self.draft.declared_format
        else:
            expected = self.declared_format
        if self.draft is not None and self.declared_format != expected:
            raise ValueError("Inspection format must match the returned draft")
        return self


def _inspect(request: IntakeInspectionRequest) -> InspectionDraft:
    if isinstance(request, SequenceInspectionRequest):
        return process_input(
            IntakeRequest(
                input_method=request.declared_format,
                content=decode_input(request.content, max_bytes=request.max_bytes),
                molecule_type=request.molecule_type,
                rna_to_dna=request.rna_to_dna,
                accession=request.accession,
                gene_symbol=request.gene_symbol,
                organism=request.organism,
                transcript=request.transcript,
                reference_assembly=request.reference_assembly,
            ),
            max_bytes=request.max_bytes,
        )
    if isinstance(request, FastqInspectionRequest):
        return process_fastq(
            request.content,
            filename=request.filename,
            sample_id=request.sample_id,
            quality_encoding=request.quality_encoding,
            mate_content=request.mate_content,
            mate_filename=request.mate_filename or "mate.fastq",
            limits=request.limits,
        )
    if isinstance(request, VcfInspectionRequest):
        return process_vcf(
            request.content,
            filename=request.filename,
            sample_id=request.sample_id,
            reference_assembly=request.reference_assembly,
            reference_content=request.reference_content,
            limits=request.limits,
        )
    if isinstance(request, PdbInspectionRequest):
        return process_pdb(
            request.content,
            filename=request.filename,
            limits=request.limits,
        )
    if isinstance(request, MmcifInspectionRequest):
        return process_mmcif(
            request.content,
            filename=request.filename,
            limits=request.limits,
        )
    raise TypeError("Unsupported inspection request")


def inspect_input(request: IntakeInspectionRequest) -> IntakeInspection:
    """Dispatch one declared format and preserve expected parser rejection details."""

    try:
        draft = _inspect(request)
    except InputValidationError as exc:
        return IntakeInspection(
            declared_format=request.declared_format,
            outcome="rejected",
            issue=exc.issue,
        )
    return IntakeInspection(
        declared_format=request.declared_format,
        outcome="accepted",
        draft=draft,
    )
