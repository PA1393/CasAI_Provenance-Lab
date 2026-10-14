"""Pure, bounded FASTQ inspection and header hints; no retrieval or alignment."""

from __future__ import annotations

import gzip
import io
import re
import zlib
from collections.abc import Iterator
from typing import Literal

from pydantic import Field

from app.modules.information_processor.contracts import (
    MAX_INPUT_BYTES,
    MAX_RECORDS,
    Contract,
    FieldValue,
    MissingField,
    ProcessingNotice,
)
from app.modules.information_processor.datasets import (
    DatasetArtifact,
    DatasetDraft,
    ReadRecord,
)
from app.modules.information_processor.parser import InputValidationError


class DatasetLimits(Contract):
    max_input_bytes: int = Field(default=MAX_INPUT_BYTES, gt=0, strict=True)
    max_decoded_bytes: int = Field(default=MAX_INPUT_BYTES, gt=0, strict=True)
    max_line_bytes: int = Field(default=200_000, gt=0, strict=True)
    max_lines: int = Field(default=10_000, gt=0, strict=True)
    max_records: int = Field(default=MAX_RECORDS, gt=0, strict=True)
    max_compression_ratio: int = Field(default=100, gt=0, strict=True)


class DatasetDetection(Contract):
    detected_format: Literal["fastq", "vcf", "unknown"]
    compression: Literal["none", "gzip"]
    requires_confirmation: Literal[True] = True


def _fail(code: str, message: str, line: int | None = None) -> None:
    raise InputValidationError(code, message, f"line:{line}" if line is not None else None)


def _artifact(content: bytes, filename: str, role, limits: DatasetLimits) -> DatasetArtifact:
    if len(content) > limits.max_input_bytes:
        _fail("input_too_large", "Original file exceeds the configured byte budget")
    if not content:
        _fail("empty_input", "File contains no bytes")
    compression = "gzip" if content.startswith(b"\x1f\x8b") else "none"
    if filename.lower().endswith(".gz") and compression != "gzip":
        _fail("compression_mismatch", "A .gz filename must contain gzip data")
    return DatasetArtifact(filename=filename, content=content, compression=compression, role=role)


def _lines(artifact: DatasetArtifact, limits: DatasetLimits) -> Iterator[tuple[int, str]]:
    """Bounded line decoding; never gzip.decompress() an unbounded whole file."""
    raw = io.BytesIO(artifact.content)
    stream = gzip.GzipFile(fileobj=raw) if artifact.compression == "gzip" else raw
    decoded = 0
    number = 0
    try:
        with stream:
            while line := stream.readline(limits.max_line_bytes + 1):
                number += 1
                if number > limits.max_lines:
                    _fail("too_many_lines", "File exceeds the line-count budget", number)
                decoded += len(line)
                if len(line) > limits.max_line_bytes:
                    _fail("line_too_large", "Line exceeds the configured byte budget", number)
                if decoded > limits.max_decoded_bytes:
                    _fail("decoded_input_too_large", "Decoded file exceeds its byte budget", number)
                if (
                    artifact.compression == "gzip"
                    and decoded > len(artifact.content) * limits.max_compression_ratio
                ):
                    _fail(
                        "compression_ratio_exceeded", "Compression expansion exceeds budget", number
                    )
                try:
                    text = line.decode("utf-8").removesuffix("\n").removesuffix("\r")
                except UnicodeDecodeError:
                    _fail("invalid_encoding", "Dataset text must be UTF-8", number)
                if any(ord(char) < 32 and char != "\t" or ord(char) == 127 for char in text):
                    _fail("corrupted_input", "Unsupported control character", number)
                yield number, text
    except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
        raise InputValidationError("invalid_compression", "Corrupt or truncated gzip file") from exc


def detect_dataset(
    content: bytes, *, filename: str = "input", limits: DatasetLimits = DatasetLimits()
) -> DatasetDetection:
    """Header suggestion only. Full adapter validation is still required."""
    artifact = _artifact(content, filename, "reads", limits)
    lines = _lines(artifact, limits)
    try:
        _, first = next(lines, (0, ""))
    finally:
        lines.close()
    detected = (
        "vcf"
        if first.startswith("##fileformat=VCFv")
        else ("fastq" if first.startswith("@") else "unknown")
    )
    return DatasetDetection(detected_format=detected, compression=artifact.compression)


def _value(value: str | None, source: str) -> FieldValue:
    value = value.strip() if value is not None else None
    return FieldValue(
        value=value or None, origin="user_supplied" if value else "unresolved", source=source
    )


def _gap(field: str, reason: str, action: str) -> MissingField:
    return MissingField(field=field, requirement="required", reason=reason, action=action)


def _fastq_records(
    artifact: DatasetArtifact, limits: DatasetLimits, mate
) -> tuple[ReadRecord, ...]:
    lines = iter(_lines(artifact, limits))
    records = []
    artifact_hash = artifact.checksum
    try:
        for number, header in lines:
            if len(records) >= limits.max_records:
                _fail("too_many_records", "Read count exceeds inspection budget", number)
            if not header.startswith("@") or not header[1:].strip():
                _fail("invalid_fastq_header", "FASTQ records need an @ identifier", number)
            tokens = header[1:].split(maxsplit=1)
            identifier = tokens[0]
            sequence_parts = []
            for seq_number, line in lines:
                if line.startswith("+"):
                    if line[1:] and line[1:] not in (identifier, header[1:]):
                        _fail(
                            "fastq_identifier_mismatch", "Repeated + identifier differs", seq_number
                        )
                    break
                if not line or not line.isascii() or set(line.upper()) - set("ACGTNRYSWKMBDHV"):
                    _fail(
                        "invalid_alphabet",
                        "FASTQ DNA sequence contains unsupported symbols",
                        seq_number,
                    )
                sequence_parts.append(line)
            else:
                _fail("truncated_fastq", "Read has no + separator", number)
            sequence = "".join(sequence_parts).upper()
            if not sequence:
                _fail("empty_record", "FASTQ sequence is empty", number)
            quality_parts = []
            quality_length = 0
            while quality_length < len(sequence):
                entry = next(lines, None)
                if entry is None:
                    _fail("truncated_fastq", "Read quality data is incomplete", number)
                quality_number, quality = entry
                if not quality or any(not 33 <= ord(char) <= 126 for char in quality):
                    _fail(
                        "invalid_quality", "Quality must be printable ASCII 33–126", quality_number
                    )
                quality_parts.append(quality)
                quality_length += len(quality)
            if quality_length != len(sequence):
                _fail("quality_length_mismatch", "Sequence and quality lengths differ", number)
            records.append(
                ReadRecord(
                    record_id=identifier,
                    description=tokens[1] if len(tokens) == 2 else None,
                    sequence=sequence,
                    qualities="".join(quality_parts),
                    mate=mate,
                    source=f"{artifact_hash}#record:{len(records) + 1}",
                    warnings=(
                        ProcessingNotice(
                            code="case_normalized",
                            message="Read bases normalized to uppercase",
                            record_id=identifier,
                        ),
                    )
                    if any(char.islower() for part in sequence_parts for char in part)
                    else (),
                )
            )
    finally:
        lines.close()
    if not records:
        _fail("empty_input", "No FASTQ reads found")
    return tuple(records)


def _pair_identity(record: ReadRecord, expected: int) -> str:
    identifier = record.record_id
    if identifier.endswith(("/1", "/2")):
        if identifier[-1] != str(expected):
            _fail("mate_direction_mismatch", "Read identifier contradicts selected mate file")
        identifier = identifier[:-2]
    if record.description and re.match(r"[12]:", record.description):
        if record.description[0] != str(expected):
            _fail("mate_direction_mismatch", "Read description contradicts selected mate file")
    return identifier


def process_fastq(
    content: bytes,
    *,
    filename: str = "reads.fastq",
    sample_id: str | None = None,
    quality_encoding: Literal["phred33"] | None = None,
    mate_content: bytes | None = None,
    mate_filename: str = "mate.fastq",
    limits: DatasetLimits = DatasetLimits(),
) -> DatasetDraft:
    """Preserve single/paired reads. Quality encoding is declared, never inferred."""
    if quality_encoding not in (None, "phred33"):
        _fail("unsupported_quality_encoding", "Only explicitly declared Phred+33 is supported")
    first = _artifact(content, filename, "reads", limits)
    artifacts = [first]
    reads = _fastq_records(first, limits, 1 if mate_content is not None else None)
    if mate_content is not None:
        second = _artifact(mate_content, mate_filename, "mate_reads", limits)
        mates = _fastq_records(second, limits, 2)
        if len(reads) != len(mates):
            _fail("mate_count_mismatch", "Mate files contain different read counts")
        for left, right in zip(reads, mates, strict=True):
            if _pair_identity(left, 1) != _pair_identity(right, 2):
                _fail("mate_identifier_mismatch", "Mate identifiers/order do not match")
        artifacts.append(second)
        reads = tuple(record for pair in zip(reads, mates, strict=True) for record in pair)
    sample = _value(sample_id, "researcher sample metadata")
    encoding = _value(quality_encoding, "declared FASTQ quality policy")
    missing = []
    if sample.value is None:
        missing.append(_gap("sample_id", "Sample identity is unresolved", "Assign a sample ID"))
    if encoding.value is None:
        missing.append(
            _gap(
                "quality_encoding",
                "Quality dialect cannot be safely guessed",
                "Declare Phred+33, or convert another dialect with a documented external tool",
            )
        )
    return DatasetDraft(
        declared_format="fastq",
        data_role="reads",
        format_version="fastq-inspection-v1",
        artifacts=tuple(artifacts),
        sample_id=sample,
        quality_encoding=encoding,
        reference_assembly=_value(None, "reads do not identify an assembly"),
        reads=reads,
        missing_fields=tuple(missing),
        warnings=tuple(warning for record in reads for warning in record.warnings)
        + (
            ProcessingNotice(
                code="reads_not_reference",
                message="Raw reads are not an assembled reference or editing result",
            ),
        ),
    )
