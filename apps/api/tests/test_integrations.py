from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.modules.integrations.base import CompletedCommand, ToolExecution
from app.modules.integrations.cas_offinder import CasOffinderAdapter, _parse_output
from app.modules.integrations.crispor import CrisporAdapter
from app.modules.integrations.crispresso import _parse_quantification


def _completed(command, *, stdout="") -> CompletedCommand:
    started = datetime.now(UTC)
    return CompletedCommand(
        command=tuple(str(part) for part in command),
        returncode=0,
        stdout=stdout,
        stderr="",
        started_at=started,
        completed_at=started + timedelta(milliseconds=12),
        duration_ms=12,
    )


def test_crispor_builds_documented_cli_and_parses_artifacts() -> None:
    calls = []

    def runner(command, *, cwd=None, timeout, stdin=None):
        calls.append(tuple(command))
        if "--help" in command:
            return _completed(command, stdout="CRISPOR 5.2")
        Path(command[command.index("--offtargets") + 1]).write_text(
            "guideId\tmismatches\ns1\t1\n", encoding="utf-8"
        )
        Path(command[command.index("--offtargets") - 1]).write_text(
            "guideId\tguideSeq\ns1\tAAACAAAAAAAAAAAAAAAA\n", encoding="utf-8"
        )
        return _completed(command)

    result = CrisporAdapter(
        executable="crispor.py",
        genome_dir="/genomes",
        runner=runner,
    ).design(sequence="AAAC" * 10, genome="hg38")

    assert calls[0][:7] == (
        "crispor.py",
        "--pam",
        "NGG",
        "--mm",
        "4",
        "--genomeDir",
        "/genomes",
    )
    assert result.version == "CRISPOR 5.2"
    assert result.result["guide_count"] == 1
    assert result.result["off_target_count"] == 1
    assert result.inputs["sequence"]["size_bytes"] == 40
    assert "AAAC" not in str(result.inputs["sequence"])


def test_cas_offinder_parser_normalizes_numeric_columns(tmp_path: Path) -> None:
    output = tmp_path / "offtargets.tsv"
    output.write_text(
        "ACGTNNN\tchr1\t42\tACGTAGG\t+\t2\n",
        encoding="utf-8",
    )

    sites = _parse_output(output)

    assert sites == [
        {
            "query_sequence": "ACGTNNN",
            "sequence_name": "chr1",
            "location": 42,
            "target_sequence": "ACGTAGG",
            "strand": "+",
            "mismatches": 2,
        }
    ]


def test_cas_offinder_writes_pattern_query_and_command() -> None:
    observed_input = ""
    observed_command = ()

    def runner(command, *, cwd=None, timeout, stdin=None):
        nonlocal observed_input, observed_command
        if len(command) == 1:
            return _completed(command, stdout="Cas-OFFinder 2.4")
        observed_command = tuple(command)
        observed_input = Path(command[1]).read_text(encoding="utf-8")
        Path(command[3]).write_text("", encoding="utf-8")
        return _completed(command)

    result = CasOffinderAdapter(executable="cas-offinder", runner=runner).search(
        guide_rna="A" * 20,
        genome_path="/genomes/hg38",
        max_mismatches=3,
    )

    assert observed_command[2] == "C"
    assert observed_input.splitlines() == [
        "/genomes/hg38",
        "NNNNNNNNNNNNNNNNNNNNNGG",
        f"{'A' * 20}NNN 3",
    ]
    assert result.result["site_count"] == 0


def test_crispresso_quantification_parser_preserves_named_fields(tmp_path: Path) -> None:
    path = tmp_path / "CRISPResso_quantification_of_editing_frequency.txt"
    path.write_text(
        "Amplicon\tReads_aligned\tUnmodified%\tModified%\n"
        "Reference\t100\t72.5\t27.5\n",
        encoding="utf-8",
    )

    assert _parse_quantification(path) == [
        {
            "Amplicon": "Reference",
            "Reads_aligned": "100",
            "Unmodified%": "72.5",
            "Modified%": "27.5",
        }
    ]



def test_tool_execution_provenance_compacts_large_tables() -> None:
    now = datetime.now(UTC)
    execution = ToolExecution(
        tool="CRISPOR",
        operation="guide_design",
        version="5.2",
        command=("crispor.py",),
        started_at=now,
        completed_at=now,
        duration_ms=1,
        inputs={},
        outputs={},
        result={"guide_count": 2, "guides": [{"id": 1}, {"id": 2}]},
    )

    payload = execution.provenance_payload()

    assert payload["result"] == {"guide_count": 2, "guides_count": 2}


def test_invalid_cas_offinder_output_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "bad.tsv"
    output.write_text("too\tfew\tcolumns\n", encoding="utf-8")

    with pytest.raises(ValueError, match="expected 6 columns"):
        _parse_output(output)
