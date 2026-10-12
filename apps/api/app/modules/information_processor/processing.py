"""Pure draft preparation. Reference retrieval and explicit confirmation are not performed here."""

from __future__ import annotations

import json
from typing import TypeVar

from app.modules.information_processor.contracts import (
    MAX_INPUT_BYTES,
    FieldOrigin,
    FieldValue,
    IntakeRequest,
    MissingField,
    OriginalArtifact,
    ProcessingNotice,
    ResearchDraft,
    SequenceRecord,
)
from app.modules.information_processor.parser import (
    InputValidationError,
    encode_input,
    parse_sequences,
)

# Deliberately invented demonstration sequence, not a reference or measured sample.
DEMO_VERSION = "casai.synthetic.sequence.v1"
DEMO_FASTA = b">casai_synthetic_v1\nTTTTAAACAAAAAAAAAAAAAAAAAGGTTTT\n"
T = TypeVar("T")


def _field(value: T | None, origin: FieldOrigin, source: str) -> FieldValue[T]:
    return FieldValue(
        value=value, origin=origin if value is not None else "unresolved", source=source
    )


def _metadata(value: str | None) -> FieldValue[str]:
    cleaned = value.strip() if value is not None else None
    return _field(cleaned or None, "user_supplied", "researcher metadata")


def _missing(field: str, reason: str, action: str, *, required: bool = True) -> MissingField:
    return MissingField(
        field=field,
        requirement="required" if required else "recommended",
        reason=reason,
        action=action,
    )


def process_input(request: IntakeRequest, *, max_bytes: int = MAX_INPUT_BYTES) -> ResearchDraft:
    """Prepare a non-executable draft without I/O or fabricated biological metadata.

    All returned data remains unconfirmed. Malformed input raises a structured issue;
    incomplete but valid input returns a draft with actionable missing information.
    """
    method = request.input_method
    if request.sequence_origin == "ai_inferred" and method != "objective":
        raise InputValidationError("ai_sequence_rejected", "AI-created sequence is not source data")
    accession = _metadata(request.accession)
    gene = _metadata(request.gene_symbol)
    organism = _metadata(request.organism)
    transcript = _metadata(request.transcript)
    assembly = _metadata(request.reference_assembly)
    objective = _field(None, "unresolved", "no objective supplied")
    warnings: list[ProcessingNotice] = []
    missing: list[MissingField] = []
    records: list[SequenceRecord] = []

    if method == "demo":
        if request.molecule_type not in (None, "DNA") or request.rna_to_dna:
            raise InputValidationError("demo_type_mismatch", "The versioned demo fixture is DNA")
        content = DEMO_FASTA
        origin: FieldOrigin = "file_extracted"
        source = DEMO_VERSION
        molecule = "DNA"
        encode_input(content.decode("utf-8"), max_bytes=max_bytes)
        warnings.append(
            ProcessingNotice(
                code="synthetic_demo",
                message="CasAI synthetic demo; no reference or experimental evidence",
            )
        )
    elif method in ("fasta", "pasted_sequence", "objective"):
        content = encode_input(request.content or "", max_bytes=max_bytes)
        origin = "file_extracted" if method == "fasta" else "user_supplied"
        source = "original input artifact"
        molecule = request.molecule_type
    else:
        # Preserve exact supplied metadata in a deterministic source artifact before normalizing it.
        content = encode_input(
            json.dumps(
                request.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
            max_bytes=max_bytes,
        )
        origin = "user_supplied"
        source = "researcher reference request"
        molecule = request.molecule_type

    artifact = OriginalArtifact(
        content=content,
        source=source,
        claim_type="explanatory"
        if method == "demo"
        else ("AI-inferred" if request.sequence_origin == "ai_inferred" else "user-supplied"),
    )
    if method in ("fasta", "pasted_sequence", "demo"):
        parsed = parse_sequences(
            content,
            input_format="fasta" if method != "pasted_sequence" else "pasted_sequence",
            molecule_type=molecule,
            rna_to_dna=request.rna_to_dna,
            max_bytes=max_bytes,
        )
        artifact_checksum = artifact.checksum
        for item in parsed:
            record_source = f"{artifact_checksum}#{item.record_id}"
            records.append(
                SequenceRecord(
                    record_id=_field(
                        item.record_id,
                        origin if method != "pasted_sequence" else "system_default",
                        record_source,
                    ),
                    description=_field(item.description, origin, record_source),
                    sequence=_field(item.sequence, origin, record_source),
                    molecule_type=_field(
                        item.molecule_type,
                        "system_default"
                        if method == "demo" or request.rna_to_dna
                        else "user_supplied",
                        "declared normalization policy",
                    ),
                    source_molecule_type=_field(
                        molecule,
                        "system_default" if method == "demo" else "user_supplied",
                        "declared input molecule",
                    ),
                    organism=organism,
                    reference_source=_field(None, "unresolved", "no reference retrieved"),
                    reference_accession=accession,
                    reference_assembly=assembly,
                    transcript=transcript,
                    coordinate_system=_field(
                        "1-based-inclusive", "system_default", "CasAI coordinate convention"
                    ),
                    input_method=_field(method, "user_supplied", "selected intake method"),
                )
            )
            warnings.extend(item.warnings)
        if molecule is None:
            missing.append(
                _missing(
                    "molecule_type",
                    "Molecule type cannot be inferred from alphabet",
                    "Declare DNA, RNA or protein",
                )
            )
        if organism.value is None and method != "demo":
            missing.append(
                _missing(
                    "organism",
                    "No organism supplied",
                    "Supply the organism when known",
                    required=False,
                )
            )
    elif method == "accession":
        if accession.value is None:
            missing.append(
                _missing(
                    "accession",
                    "No accession supplied",
                    "Supply an NCBI, RefSeq or GenBank accession",
                )
            )
        missing.append(
            _missing(
                "reference_record",
                "No exact reference has been retrieved",
                "Resolve and select an accession version through a reference adapter",
            )
        )
        warnings.append(
            ProcessingNotice(
                code="reference_unresolved",
                message="Accession request is unresolved; no sequence retrieved",
            )
        )
    elif method == "gene":
        for name, field, action in (
            ("gene_symbol", gene, "Supply a gene symbol"),
            ("organism", organism, "Select an organism explicitly"),
            ("transcript", transcript, "Resolve the gene and select an exact transcript/isoform"),
        ):
            if field.value is None:
                missing.append(_missing(name, f"{name} has not been selected", action))
        missing.append(
            _missing(
                "reference_record",
                "Gene/transcript has not been resolved",
                "Resolve exact transcript and assembly records through a gene adapter",
            )
        )
        warnings.append(
            ProcessingNotice(
                code="gene_unresolved",
                message="No organism, transcript or assembly will be guessed",
            )
        )
    else:
        objective = _field(
            request.content.strip(),
            "ai_inferred" if request.sequence_origin == "ai_inferred" else "user_supplied",
            "written research objective",
        )
        missing.extend(
            (
                _missing(
                    "source_sequence",
                    "A written objective is not biological source data",
                    "Attach a source sequence or resolve an exact reference",
                ),
                _missing(
                    "objective_specification",
                    "Objective text has not become a confirmed specification",
                    "Review a structured objective specification before confirmation",
                ),
            )
        )
        warnings.append(
            ProcessingNotice(
                code="objective_draft",
                message="Objective retained as draft text; no biological facts inferred",
            )
        )

    return ResearchDraft(
        input_method=method,
        original_artifact=artifact,
        records=tuple(records),
        accession=accession,
        gene_symbol=gene,
        organism=organism,
        transcript=transcript,
        reference_assembly=assembly,
        objective=objective,
        warnings=tuple(warnings),
        missing_fields=tuple(missing),
    )
