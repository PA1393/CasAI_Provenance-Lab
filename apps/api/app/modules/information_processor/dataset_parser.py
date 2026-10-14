"""Pure, bounded FASTQ/VCF inspection. No retrieval, alignment, approval, or haplotypes."""

from __future__ import annotations

import gzip
import io
import json
import math
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
    checksum,
)
from app.modules.information_processor.datasets import (
    DatasetArtifact,
    DatasetDraft,
    ReadRecord,
    SampleCall,
    VariantRecord,
)
from app.modules.information_processor.parser import InputValidationError, parse_sequences


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


def _genotype(raw: str, alternative_count: int, line: int):
    if not re.fullmatch(r"(?:\.|[0-9]+)(?:[/|](?:\.|[0-9]+))*", raw, flags=re.ASCII):
        _fail("invalid_genotype", "Unsupported or malformed GT value", line)
    if "/" in raw and "|" in raw:
        _fail("unsupported_genotype", "Mixed-phase genotypes require a richer adapter", line)
    try:
        alleles = tuple(None if value == "." else int(value) for value in re.split(r"[/|]", raw))
    except ValueError:
        _fail("invalid_genotype", "GT integer exceeds supported parsing limits", line)
    if any(value is not None and value > alternative_count for value in alleles):
        _fail("invalid_genotype", "GT index exceeds the number of REF/ALT alleles", line)
    return alleles, "|" in raw if len(alleles) > 1 else None


def process_vcf(
    content: bytes,
    *,
    filename: str = "variants.vcf",
    sample_id: str | None = None,
    reference_assembly: str | None = None,
    reference_content: bytes | None = None,
    limits: DatasetLimits = DatasetLimits(),
) -> DatasetDraft:
    """Inspect VCF 4.2–4.5 literal alleles; preserve INFO/FORMAT without interpreting them."""
    artifact = _artifact(content, filename, "variants", limits)
    lines = iter(_lines(artifact, limits))
    variants = []
    metadata = []
    artifact_hash = artifact.checksum
    normalization_notices = []
    try:
        _, first = next(lines, (0, ""))
        if first not in {f"##fileformat=VCFv4.{version}" for version in range(2, 6)}:
            _fail("unsupported_vcf_version", "Declare a supported VCF 4.2–4.5 fileformat header", 1)
        version = first.split("=", 1)[1]
        metadata.append(first)
        for number, line in lines:
            if line.startswith("##"):
                metadata.append(line)
                continue
            header = line.split("\t")
            if header[:8] != ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]:
                _fail(
                    "invalid_vcf_header", "VCF needs its eight fixed tab-delimited columns", number
                )
            if len(header) == 9 or (len(header) > 8 and header[8] != "FORMAT"):
                _fail(
                    "invalid_vcf_header", "FORMAT must be followed by named sample columns", number
                )
            samples = tuple(header[9:])
            if any(not name or any(char.isspace() for char in name) for name in samples):
                _fail(
                    "invalid_vcf_header", "Sample names must be nonempty without whitespace", number
                )
            if len(set(samples)) != len(samples):
                _fail("invalid_vcf_header", "Sample names must be unique", number)
            break
        else:
            _fail("invalid_vcf_header", "Missing #CHROM header")
        for number, line in lines:
            if len(variants) >= limits.max_records:
                _fail("too_many_records", "Variant count exceeds inspection budget", number)
            fields = line.split("\t")
            if len(fields) != len(header) or any(not field for field in fields):
                _fail("invalid_vcf_record", "VCF row does not match its column header", number)
            chrom, pos, ids, ref, alt, qual, filters, info = fields[:8]
            if any(char.isspace() for char in chrom) or chrom.startswith("#"):
                _fail("invalid_contig", "Invalid CHROM identifier", number)
            if not re.fullmatch(r"[0-9]+", pos, flags=re.ASCII):
                _fail("invalid_position", "Only positive 1-based positions are supported", number)
            try:
                position = int(pos)
            except ValueError:
                _fail("invalid_position", "POS integer exceeds supported parsing limits", number)
            if position < 1:
                _fail("invalid_position", "Only positive 1-based positions are supported", number)
            if any(char.islower() for char in ref + alt):
                normalization_notices.append(
                    ProcessingNotice(
                        code="case_normalized",
                        message="VCF alleles normalized to uppercase",
                        record_id=f"line:{number}",
                    )
                )
            alternatives = tuple(alt.upper().split(",")) if alt != "." else ()
            ref = ref.upper()
            if any(not allele or set(allele) - set("ACGTN") for allele in (ref, *alternatives)):
                _fail(
                    "unsupported_allele",
                    "Symbolic, breakend and non-literal alleles are unsupported",
                    number,
                )
            if len(set(alternatives)) != len(alternatives) or ref in alternatives:
                _fail("invalid_alleles", "ALT alleles must be distinct and differ from REF", number)
            if qual != "." and not re.fullmatch(
                r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", qual, re.ASCII
            ):
                _fail(
                    "invalid_variant_quality", "QUAL must be a VCF numeric value or missing", number
                )
            try:
                quality = None if qual == "." else float(qual)
            except ValueError:
                _fail("invalid_variant_quality", "QUAL must be numeric or missing", number)
            if quality is not None and (not math.isfinite(quality) or quality < 0):
                _fail("invalid_variant_quality", "QUAL must be finite and nonnegative", number)
            filter_values = None if filters == "." else tuple(filters.split(";"))
            if filter_values is not None and (
                any(not value or any(char.isspace() for char in value) for value in filter_values)
                or len(set(filter_values)) != len(filter_values)
                or ("PASS" in filter_values and len(filter_values) > 1)
            ):
                _fail("invalid_filter", "FILTER must be missing, PASS, or named filters", number)
            keys = tuple(fields[8].split(":")) if samples else ()
            if keys and (any(not key or key == "." for key in keys) or len(set(keys)) != len(keys)):
                _fail("invalid_format", "FORMAT keys must be nonempty and unique", number)
            if "GT" in keys and keys[0] != "GT":
                _fail("invalid_format", "GT must be the first FORMAT key", number)
            calls = []
            for name, raw in zip(samples, fields[9:], strict=True):
                values = tuple(raw.split(":"))
                if len(values) > len(keys) or any(not value for value in values):
                    _fail("invalid_sample", "Sample values do not match FORMAT", number)
                values += (".",) * (len(keys) - len(values))
                genotype, phased = (
                    _genotype(values[0], len(alternatives), number)
                    if "GT" in keys
                    else (None, None)
                )
                calls.append(
                    SampleCall(sample=name, values=values, genotype=genotype, phased=phased)
                )
            variants.append(
                VariantRecord(
                    contig=chrom,
                    position=position,
                    identifiers=tuple(ids.split(";")) if ids != "." else (),
                    reference=ref,
                    alternatives=alternatives,
                    quality=quality,
                    filters=filter_values,
                    info=info,
                    format_keys=keys,
                    samples=tuple(calls),
                    source=f"{artifact_hash}#line:{number}",
                )
            )
    finally:
        lines.close()
    artifacts = [artifact]
    assembly = _value(
        reference_assembly, "researcher reference assembly label; not independently verified"
    )
    sample = _value(sample_id, "researcher sample selection")
    if sample.value is not None and samples and sample.value not in samples:
        _fail("sample_not_found", "Selected sample is absent from the VCF header")
    missing = []
    reference_digest = None
    if assembly.value is None:
        missing.append(
            _gap("reference_assembly", "Assembly is unresolved", "Select an exact assembly")
        )
    if samples and sample.value is None:
        missing.append(
            _gap("sample_id", "No sample selected", "Select a sample from the VCF header")
        )
    if reference_content is None:
        missing.append(
            _gap("reference_record", "REF has not been checked", "Attach the exact reference FASTA")
        )
    else:
        reference_artifact = _artifact(reference_content, "reference.fasta", "reference", limits)
        if reference_artifact.compression != "none":
            _fail(
                "unsupported_reference_compression",
                "Reference FASTA must be uncompressed in this adapter",
            )
        parsed = parse_sequences(
            reference_content,
            input_format="fasta",
            molecule_type="DNA",
            max_bytes=min(limits.max_input_bytes, limits.max_decoded_bytes),
            max_records=limits.max_records,
        )
        reference = {record.record_id: record.sequence for record in parsed}
        reference_digest = checksum(
            json.dumps(
                reference,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        for variant in variants:
            sequence = reference.get(variant.contig)
            if sequence is None:
                _fail("reference_contig_missing", f"Reference lacks contig {variant.contig}")
            start = variant.position - 1
            if sequence[start : start + len(variant.reference)] != variant.reference:
                _fail(
                    "reference_mismatch",
                    f"REF does not match supplied sequence at {variant.contig}:{variant.position}",
                )
        artifacts.append(reference_artifact)
    warnings = [
        *normalization_notices,
        ProcessingNotice(
            code="variants_not_haplotype",
            message="Variants are not a reconstructed genome or editing efficacy result",
        ),
        ProcessingNotice(
            code="vcf_inspection_only",
            message="INFO/FORMAT metadata retained; tag types/cardinality are not interpreted",
        ),
    ]
    if not variants:
        warnings.append(
            ProcessingNotice(
                code="no_variants", message="Valid VCF header contains no variant records"
            )
        )
    return DatasetDraft(
        declared_format="vcf",
        data_role="variants",
        format_version=version,
        artifacts=tuple(artifacts),
        sample_id=sample,
        quality_encoding=_value(None, "FASTQ quality encoding is not applicable"),
        reference_assembly=assembly,
        reference_checked=reference_content is not None,
        reference_sequence_checksum=reference_digest,
        variants=tuple(variants),
        sample_names=samples,
        metadata_lines=tuple(metadata),
        missing_fields=tuple(missing),
        warnings=tuple(warnings),
    )
