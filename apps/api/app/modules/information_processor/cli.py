"""Inspect a bounded local dataset; never uploads data or writes source files."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from app.modules.information_processor.dataset_parser import (
    DatasetLimits,
    process_fastq,
    process_vcf,
)
from app.modules.information_processor.parser import InputValidationError


def _read(path: Path, limits: DatasetLimits) -> bytes:
    with path.open("rb") as stream:
        content = stream.read(limits.max_input_bytes + 1)
    if len(content) > limits.max_input_bytes:
        raise InputValidationError(
            "input_too_large", "File exceeds the local inspection byte budget"
        )
    return content


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", required=True, choices=("fastq", "vcf"))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--sample")
    parser.add_argument("--quality-encoding", choices=("phred33",))
    parser.add_argument("--mate", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--assembly")
    args = parser.parse_args(argv)
    if args.format == "fastq" and (args.reference is not None or args.assembly is not None):
        parser.error("--reference and --assembly apply only to VCF inspection")
    if args.format == "vcf" and (args.mate is not None or args.quality_encoding is not None):
        parser.error("--mate and --quality-encoding apply only to FASTQ inspection")
    limits = DatasetLimits()
    try:
        content = _read(args.input, limits)
        if args.format == "fastq":
            draft = process_fastq(
                content,
                filename=args.input.name,
                sample_id=args.sample,
                quality_encoding=args.quality_encoding,
                mate_content=_read(args.mate, limits) if args.mate is not None else None,
                mate_filename=args.mate.name if args.mate is not None else "mate.fastq",
                limits=limits,
            )
        else:
            draft = process_vcf(
                content,
                filename=args.input.name,
                sample_id=args.sample,
                reference_assembly=args.assembly,
                reference_content=_read(args.reference, limits)
                if args.reference is not None
                else None,
                limits=limits,
            )
    except InputValidationError as exc:
        print(json.dumps({"status": "rejected", "issue": exc.issue.model_dump()}))
        return 2
    except OSError:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "issue": {
                        "code": "file_access_error",
                        "message": "Could not read a selected local file",
                    },
                }
            )
        )
        return 2
    # Summary intentionally excludes sequence/genotype payloads and original bytes.
    # Full immutable data remains available through the Python adapter return value.
    summary = draft.model_dump(mode="json", exclude={"artifacts", "reads", "variants"})
    summary["artifacts"] = [
        artifact.model_dump(mode="json", exclude={"content"}) for artifact in draft.artifacts
    ]
    summary["output_kind"] = "inspection_summary"
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
