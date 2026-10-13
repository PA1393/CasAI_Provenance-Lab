"""Record-preserving sequence parsing, with declared molecule and normalization rules."""

from __future__ import annotations

import re
from typing import Literal

from app.modules.information_processor.contracts import (
    ALPHABETS,
    MAX_INPUT_BYTES,
    MAX_RECORDS,
    Contract,
    InputDetection,
    MoleculeType,
    ProcessingNotice,
)

_ACCESSION = re.compile(r"[A-Za-z]{1,6}_?\d{5,9}(?:\.\d+)?", flags=re.ASCII)
_WHITESPACE = str.maketrans("", "", " \t\r\n")


class InputValidationError(ValueError):
    def __init__(self, code: str, message: str, record_id: str | None = None) -> None:
        self.issue = ProcessingNotice(code=code, message=message, record_id=record_id)
        super().__init__(message)


class ParsedRecord(Contract):
    record_id: str
    description: str | None
    sequence: str
    molecule_type: MoleculeType | None
    warnings: tuple[ProcessingNotice, ...] = ()


def decode_input(content: bytes, *, max_bytes: int = MAX_INPUT_BYTES) -> str:
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    if len(content) > max_bytes:
        raise InputValidationError("input_too_large", f"Input exceeds the {max_bytes}-byte limit")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputValidationError("invalid_encoding", "Input must be valid UTF-8 text") from exc
    if not text.lstrip("\ufeff").strip():
        raise InputValidationError("empty_input", "Input contains no content")
    if any(ord(char) < 32 and char not in "\t\r\n" or ord(char) == 127 for char in text):
        raise InputValidationError(
            "corrupted_input", "Input contains unsupported control characters"
        )
    return text


def encode_input(text: str, *, max_bytes: int = MAX_INPUT_BYTES) -> bytes:
    if len(text) > max_bytes:
        raise InputValidationError("input_too_large", f"Input exceeds the {max_bytes}-byte limit")
    try:
        content = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise InputValidationError("invalid_encoding", "Input must be valid UTF-8 text") from exc
    decode_input(content, max_bytes=max_bytes)
    return content


def detect_input(content: bytes, *, max_bytes: int = MAX_INPUT_BYTES) -> InputDetection:
    text = decode_input(content, max_bytes=max_bytes).lstrip("\ufeff").strip(" \t\r\n")
    lines = [line.strip(" \t\r") for line in re.split(r"\r\n|\r|\n", text) if line]
    first = next((line for line in lines if not line.startswith(";")), "")
    if first.startswith(">"):
        return InputDetection(
            detected_method="fasta",
            reason="FASTA header found; declare the molecule type",
        )
    if _ACCESSION.fullmatch(text):
        return InputDetection(
            detected_method="accession",
            reason="Accession-like identifier; requires exact resolution",
        )
    sequence = text.translate(_WHITESPACE).upper()
    candidates = tuple(
        molecule
        for molecule, alphabet in ALPHABETS.items()
        if text.isascii() and sequence and not set(sequence) - alphabet
    )
    if candidates:
        return InputDetection(
            detected_method="unknown" if candidates == ("protein",) else "pasted_sequence",
            candidate_molecule_types=candidates,
            reason="Compatible letters alone cannot distinguish a sequence from prose",
        )
    return InputDetection(
        detected_method="unknown",
        reason="Declare an input method; prose, gene symbols and unsupported formats are ambiguous",
    )


def parse_sequences(
    content: bytes,
    *,
    input_format: Literal["fasta", "pasted_sequence"],
    molecule_type: MoleculeType | None,
    rna_to_dna: bool = False,
    max_bytes: int = MAX_INPUT_BYTES,
    max_records: int = MAX_RECORDS,
) -> tuple[ParsedRecord, ...]:
    text = decode_input(content, max_bytes=max_bytes).lstrip("\ufeff")
    if input_format not in ("fasta", "pasted_sequence"):
        raise InputValidationError(
            "unsupported_format", "Only FASTA and pasted sequences are parsed"
        )
    if molecule_type is not None and molecule_type not in ALPHABETS:
        raise InputValidationError("invalid_molecule_type", "Declare DNA, RNA or protein")
    if rna_to_dna and molecule_type != "RNA":
        raise InputValidationError("invalid_conversion", "RNA conversion requires declared RNA")
    if max_records < 1:
        raise ValueError("max_records must be positive")

    drafts: list[tuple[str, str | None, str]] = []
    if input_format == "pasted_sequence":
        if any(line.strip().startswith((">", ";")) for line in text.splitlines()):
            raise InputValidationError(
                "format_mismatch", "FASTA headers/comments require FASTA intake"
            )
        drafts.append(("sequence_1", None, text))
    else:
        current_id: str | None = None
        description: str | None = None
        parts: list[str] = []
        # Preserve actual whitespace and split only supported ASCII line boundaries.
        # str.splitlines() would silently consume Unicode sequence separators.
        for source_line in re.findall(r"[^\r\n]*(?:\r\n|\r|\n|$)", text):
            line = source_line.strip(" \t\r\n")
            if not line or line.startswith(";"):
                continue
            if line.startswith(">"):
                if current_id is not None:
                    drafts.append((current_id, description, "".join(parts)))
                if len(drafts) >= max_records:
                    raise InputValidationError("too_many_records", "FASTA record limit exceeded")
                header = line[1:].strip().split(maxsplit=1)
                if not header:
                    raise InputValidationError(
                        "missing_identifier", "FASTA headers need an identifier"
                    )
                current_id = header[0]
                description = header[1] if len(header) == 2 else None
                parts = []
            elif current_id is None:
                raise InputValidationError("missing_header", "FASTA sequence must follow a header")
            else:
                parts.append(source_line)
        if current_id is not None:
            drafts.append((current_id, description, "".join(parts)))

    if not drafts:
        raise InputValidationError("empty_input", "No sequence records found")
    seen: set[str] = set()
    records: list[ParsedRecord] = []
    for record_id, description, raw in drafts:
        if record_id in seen:
            raise InputValidationError(
                "duplicate_identifier", "FASTA identifiers must be unique", record_id
            )
        seen.add(record_id)
        if not raw.isascii():
            raise InputValidationError(
                "invalid_alphabet",
                "Sequence letters and whitespace must be ASCII",
                record_id,
            )
        sequence = raw.translate(_WHITESPACE).upper()
        if not sequence:
            raise InputValidationError("empty_record", "Sequence record is empty", record_id)
        alphabet = ALPHABETS.get(molecule_type, frozenset().union(*ALPHABETS.values()))
        invalid = set(sequence) - alphabet
        if invalid:
            raise InputValidationError(
                "invalid_alphabet",
                f"Invalid {molecule_type or 'sequence'} characters: {sorted(invalid)}",
                record_id,
            )
        warnings: list[ProcessingNotice] = []
        if any(char.islower() for char in raw):
            warnings.append(
                ProcessingNotice(
                    code="case_normalized",
                    message="Sequence letters normalized to uppercase",
                    record_id=record_id,
                )
            )
        if any(char in " \t\r\n" for char in raw):
            warnings.append(
                ProcessingNotice(
                    code="whitespace_normalized",
                    message="Sequence whitespace removed",
                    record_id=record_id,
                )
            )
        if molecule_type is None:
            warnings.append(
                ProcessingNotice(
                    code="molecule_type_unresolved",
                    message="Choose DNA, RNA or protein explicitly",
                    record_id=record_id,
                )
            )
        if rna_to_dna:
            sequence = sequence.replace("U", "T")
            warnings.append(
                ProcessingNotice(
                    code="rna_to_dna",
                    message="RNA U-to-T conversion explicitly requested",
                    record_id=record_id,
                )
            )
        concrete = "ACGT" if molecule_type == "DNA" or rna_to_dna else "ACGU"
        ambiguous = "BXZJ" if molecule_type == "protein" else set(sequence) - set(concrete)
        if molecule_type is not None and set(sequence) & set(ambiguous):
            warnings.append(
                ProcessingNotice(
                    code="ambiguous_symbols",
                    message="Ambiguous bases/residues remain unresolved",
                    record_id=record_id,
                )
            )
        records.append(
            ParsedRecord(
                record_id=record_id,
                description=description,
                sequence=sequence,
                molecule_type="DNA" if rna_to_dna else molecule_type,
                warnings=tuple(warnings),
            )
        )
    return tuple(records)
