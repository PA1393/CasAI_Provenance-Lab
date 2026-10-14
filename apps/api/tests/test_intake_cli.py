"""Local CLI tests; source files stay unchanged and no providers are called."""

import gzip
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.modules.information_processor.cli import _read, main
from app.modules.information_processor.contracts import checksum
from app.modules.information_processor.dataset_parser import DatasetLimits
from app.modules.information_processor.parser import InputValidationError

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "test-fixtures/intake"
API = REPO / "apps/api"


def test_cli_paired_fixture_summary_preserves_sources_without_payloads(capsys):
    left, right = FIXTURES / "reads-r1.fastq", FIXTURES / "reads-r2.fastq"
    originals = (left.read_bytes(), right.read_bytes())
    assert (
        main(
            [
                "--format",
                "fastq",
                "--input",
                str(left),
                "--mate",
                str(right),
                "--sample",
                "synthetic_sample",
                "--quality-encoding",
                "phred33",
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["output_kind"] == "inspection_summary"
    assert summary["record_count"] == 2
    assert summary["executable"] is False
    assert summary["missing_fields"] == []
    assert [a["role"] for a in summary["artifacts"]] == ["reads", "mate_reads"]
    assert [a["checksum"] for a in summary["artifacts"]] == [checksum(data) for data in originals]
    assert "reads" not in summary and "variants" not in summary
    assert all("content" not in a for a in summary["artifacts"])
    assert (left.read_bytes(), right.read_bytes()) == originals


def test_cli_vcf_fixture_ref_check_and_unconfirmed_selection(capsys):
    variant, reference = FIXTURES / "variants.vcf", FIXTURES / "reference.fasta"
    originals = (variant.read_bytes(), reference.read_bytes())
    assert (
        main(
            [
                "--format",
                "vcf",
                "--input",
                str(variant),
                "--reference",
                str(reference),
                "--assembly",
                "synthetic_demo",
                "--sample",
                "synthetic_sample",
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["record_count"] == 1
    assert summary["reference_checked"] is True
    assert summary["reference_assembly"]["confirmed"] is False
    assert summary["executable"] is False
    assert summary["missing_fields"] == []
    assert "variants" not in summary
    assert [a["checksum"] for a in summary["artifacts"]] == [checksum(data) for data in originals]
    assert (variant.read_bytes(), reference.read_bytes()) == originals


def test_cli_unknown_metadata_returns_draft_not_approval(capsys):
    assert main(["--format", "fastq", "--input", str(FIXTURES / "reads-r1.fastq")]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert {f["field"] for f in summary["missing_fields"]} == {"sample_id", "quality_encoding"}
    assert summary["executable"] is False


def test_cli_gzip_fixture_preserves_original_compression_identity(tmp_path, capsys):
    path = tmp_path / "reads.fastq.gz"
    original = gzip.compress((FIXTURES / "reads-r1.fastq").read_bytes(), mtime=0)
    path.write_bytes(original)
    assert main(["--format", "fastq", "--input", str(path)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["artifacts"][0]["compression"] == "gzip"
    assert summary["artifacts"][0]["checksum"] == checksum(original)
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "format_name, content, code",
    [
        ("fastq", b"not FASTQ", "invalid_fastq_header"),
        ("vcf", b"not VCF", "unsupported_vcf_version"),
        ("fastq", b"", "empty_input"),
    ],
)
def test_cli_rejections_are_structured_and_leave_sources_unchanged(
    format_name,
    content,
    code,
    tmp_path,
    capsys,
):
    path = tmp_path / "input"
    path.write_bytes(content)
    assert main(["--format", format_name, "--input", str(path)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "rejected"
    assert result["issue"]["code"] == code
    assert path.read_bytes() == content


def test_cli_ref_mismatch_returns_structured_error(tmp_path, capsys):
    path = tmp_path / "wrong.fasta"
    original = b">synthetic_contig\nAAGTACGT\n"
    path.write_bytes(original)
    assert (
        main(
            [
                "--format",
                "vcf",
                "--input",
                str(FIXTURES / "variants.vcf"),
                "--reference",
                str(path),
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["issue"]["code"] == "reference_mismatch"
    assert path.read_bytes() == original


@pytest.mark.parametrize("file_kind", ["absent", "directory"])
def test_cli_file_access_errors_do_not_leak_paths_or_tracebacks(file_kind, tmp_path, capsys):
    path = tmp_path / file_kind
    if file_kind == "directory":
        path.mkdir()
    assert main(["--format", "vcf", "--input", str(path)]) == 2
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["issue"]["code"] == "file_access_error"
    assert str(path) not in captured.out
    assert "Traceback" not in captured.out + captured.err


@pytest.mark.parametrize(
    "arguments",
    [
        ["--format", "vcf", "--input", "unused", "--mate", "unused"],
        ["--format", "vcf", "--input", "unused", "--quality-encoding", "phred33"],
        ["--format", "fastq", "--input", "unused", "--reference", "unused"],
        ["--format", "fastq", "--input", "unused", "--assembly", "unused"],
        ["--format", "fastq", "--input", "unused", "--quality-encoding", "phred64"],
    ],
)
def test_cli_inapplicable_options_reject_before_file_access(arguments, capsys):
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage:" in captured.err


def test_local_reader_enforces_exact_byte_budget(tmp_path):
    path = tmp_path / "input"
    path.write_bytes(b"ACGT")
    assert _read(path, DatasetLimits(max_input_bytes=4)) == b"ACGT"
    with pytest.raises(InputValidationError) as error:
        _read(path, DatasetLimits(max_input_bytes=3))
    assert error.value.issue.code == "input_too_large"
    assert path.read_bytes() == b"ACGT"


@pytest.mark.parametrize("format_name", ["fastq", "vcf"])
def test_actual_python_module_entrypoint(format_name):
    input_name = "reads-r1.fastq" if format_name == "fastq" else "variants.vcf"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.modules.information_processor.cli",
            "--format",
            format_name,
            "--input",
            str(FIXTURES / input_name),
        ],
        cwd=API,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["record_count"] == 1
    assert summary["output_kind"] == "inspection_summary"
    assert summary["executable"] is False


def test_actual_python_module_entrypoint_returns_nonzero_for_bad_data(tmp_path):
    path = tmp_path / "bad.vcf"
    path.write_bytes(b"bad")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.modules.information_processor.cli",
            "--format",
            "vcf",
            "--input",
            str(path),
        ],
        cwd=API,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["issue"]["code"] == "unsupported_vcf_version"
    assert "Traceback" not in result.stderr
