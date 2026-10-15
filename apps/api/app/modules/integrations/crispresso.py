from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from app.core.config import settings
from app.modules.integrations.base import (
    CommandRunner,
    ToolExecution,
    ToolExecutionError,
    detect_version,
    file_fingerprint,
    redact_command_values,
    run_command,
    text_fingerprint,
)


class Crispresso2Adapter:
    """Analyze real reads with CRISPResso2 and retain its quantification artifact."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        timeout: int | None = None,
        runner: CommandRunner = run_command,
    ) -> None:
        self.executable = executable or settings.crispresso_command
        self.timeout = timeout or settings.scientific_tool_timeout_seconds
        self.runner = runner

    def analyze(
        self,
        *,
        fastq_r1: Path,
        amplicon_sequence: str,
        guide_rna: str,
        fastq_r2: Path | None = None,
        name: str = "casai",
    ) -> ToolExecution:
        if not fastq_r1.is_file():
            raise ValueError(f"FASTQ R1 does not exist: {fastq_r1}")
        if fastq_r2 is not None and not fastq_r2.is_file():
            raise ValueError(f"FASTQ R2 does not exist: {fastq_r2}")

        with tempfile.TemporaryDirectory(prefix="casai-crispresso-") as directory:
            workdir = Path(directory)
            command = [
                self.executable,
                "--fastq_r1",
                str(fastq_r1.resolve()),
                "--amplicon_seq",
                amplicon_sequence.upper(),
                "--guide_seq",
                guide_rna.upper(),
                "--name",
                name,
                "--output_folder",
                str(workdir),
            ]
            if fastq_r2 is not None:
                command.extend(["--fastq_r2", str(fastq_r2.resolve())])
            completed = self.runner(command, cwd=workdir, timeout=self.timeout)
            quantification_path = _find_quantification(workdir)
            if quantification_path is None:
                raise ToolExecutionError.from_completed(
                    completed,
                    message="completed without a quantification-of-editing-frequency file",
                )
            quantification = _parse_quantification(quantification_path)
            return ToolExecution(
                tool="CRISPResso2",
                operation="read_quantification",
                version=detect_version(self.runner, [self.executable, "--version"]),
                command=redact_command_values(
                    completed.command, {"--amplicon_seq", "--guide_seq"}
                ),
                started_at=completed.started_at,
                completed_at=completed.completed_at,
                duration_ms=completed.duration_ms,
                inputs={
                    "fastq_r1": file_fingerprint(fastq_r1),
                    "fastq_r2": file_fingerprint(fastq_r2) if fastq_r2 else None,
                    "amplicon_sequence": text_fingerprint(amplicon_sequence.upper()),
                    "guide_rna": text_fingerprint(guide_rna.upper()),
                },
                outputs={"quantification": file_fingerprint(quantification_path)},
                result={"quantification": quantification},
                stdout=completed.stdout,
                stderr=completed.stderr,
            )


def _find_quantification(workdir: Path) -> Path | None:
    matches = list(workdir.rglob("*quantification_of_editing_frequency.txt"))
    return matches[0] if matches else None


def _parse_quantification(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return [dict(row) for row in csv.DictReader(stream, delimiter="\t")]
