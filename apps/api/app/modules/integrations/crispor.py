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
    run_command,
    text_fingerprint,
)


class CrisporAdapter:
    """Run CRISPOR's documented command-line interface and parse its TSV output."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        genome_dir: str | None = None,
        timeout: int | None = None,
        runner: CommandRunner = run_command,
    ) -> None:
        self.executable = executable or settings.crispor_command
        self.genome_dir = genome_dir if genome_dir is not None else settings.crispor_genome_dir
        self.timeout = timeout or settings.scientific_tool_timeout_seconds
        self.runner = runner

    def design(
        self,
        *,
        sequence: str,
        genome: str,
        pam: str = "NGG",
        max_mismatches: int = 4,
    ) -> ToolExecution:
        with tempfile.TemporaryDirectory(prefix="casai-crispor-") as directory:
            workdir = Path(directory)
            fasta_path = workdir / "target.fa"
            guide_path = workdir / "guides.tsv"
            off_target_path = workdir / "offtargets.tsv"
            fasta_path.write_text(f">target\n{sequence.upper()}\n", encoding="utf-8")

            command = [
                self.executable,
                "--pam",
                pam,
                "--mm",
                str(max_mismatches),
            ]
            if self.genome_dir:
                command.extend(["--genomeDir", self.genome_dir])
            command.extend(
                [genome, str(fasta_path), str(guide_path), "--offtargets", str(off_target_path)]
            )
            completed = self.runner(command, cwd=workdir, timeout=self.timeout)
            if not guide_path.exists():
                raise ToolExecutionError.from_completed(
                    completed, message="completed without creating guides.tsv"
                )

            guides = _read_tsv(guide_path)
            off_targets = _read_tsv(off_target_path) if off_target_path.exists() else []
            return ToolExecution(
                tool="CRISPOR",
                operation="guide_design",
                version=detect_version(
                    self.runner, [self.executable, "--help"]
                ),
                command=completed.command,
                started_at=completed.started_at,
                completed_at=completed.completed_at,
                duration_ms=completed.duration_ms,
                inputs={
                    "sequence": text_fingerprint(sequence.upper()),
                    "genome": genome,
                    "pam": pam,
                    "max_mismatches": max_mismatches,
                },
                outputs={
                    "guides": file_fingerprint(guide_path),
                    "off_targets": (
                        file_fingerprint(off_target_path) if off_target_path.exists() else None
                    ),
                },
                result={
                    "guide_count": len(guides),
                    "off_target_count": len(off_targets),
                    "guides": guides,
                    "off_targets": off_targets,
                },
                stdout=completed.stdout,
                stderr=completed.stderr,
            )


def _read_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return [dict(row) for row in csv.DictReader(stream, delimiter="\t")]
