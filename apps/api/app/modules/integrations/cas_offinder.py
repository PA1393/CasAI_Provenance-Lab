from __future__ import annotations

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

_COLUMNS = (
    "query_sequence",
    "sequence_name",
    "location",
    "target_sequence",
    "strand",
    "mismatches",
)


class CasOffinderAdapter:
    """Run the production Cas-OFFinder 2 CLI and normalize its six-column output."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        device: str | None = None,
        timeout: int | None = None,
        runner: CommandRunner = run_command,
    ) -> None:
        self.executable = executable or settings.cas_offinder_command
        self.device = device or settings.cas_offinder_device
        self.timeout = timeout or settings.scientific_tool_timeout_seconds
        self.runner = runner

    def search(
        self,
        *,
        guide_rna: str,
        genome_path: str,
        pam: str = "NGG",
        max_mismatches: int = 4,
    ) -> ToolExecution:
        guide = guide_rna.upper()
        pattern = "N" * len(guide) + pam.upper()
        query = guide + "N" * len(pam)
        input_text = f"{genome_path}\n{pattern}\n{query} {max_mismatches}\n"
        with tempfile.TemporaryDirectory(prefix="casai-cas-offinder-") as directory:
            workdir = Path(directory)
            input_path = workdir / "input.txt"
            output_path = workdir / "offtargets.tsv"
            input_path.write_text(input_text, encoding="utf-8")
            completed = self.runner(
                [self.executable, str(input_path), self.device, str(output_path)],
                cwd=workdir,
                timeout=self.timeout,
            )
            if not output_path.exists():
                raise ToolExecutionError.from_completed(
                    completed, message="completed without creating offtargets.tsv"
                )
            try:
                sites = _parse_output(output_path)
            except ValueError as exc:
                raise ToolExecutionError.from_completed(
                    completed, message=f"produced invalid output: {exc}"
                ) from exc
            return ToolExecution(
                tool="Cas-OFFinder",
                operation="off_target_search",
                version=detect_version(self.runner, [self.executable]),
                command=completed.command,
                started_at=completed.started_at,
                completed_at=completed.completed_at,
                duration_ms=completed.duration_ms,
                inputs={
                    "guide_rna": text_fingerprint(guide),
                    "genome_path": genome_path,
                    "pam": pam,
                    "max_mismatches": max_mismatches,
                    "device": self.device,
                },
                outputs={"off_targets": file_fingerprint(output_path)},
                result={"site_count": len(sites), "sites": sites},
                stdout=completed.stdout,
                stderr=completed.stderr,
            )


def _parse_output(path: Path) -> list[dict]:
    sites: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        values = line.split("\t")
        if len(values) != len(_COLUMNS):
            raise ValueError(
                f"invalid Cas-OFFinder output at line {line_number}: "
                f"expected {len(_COLUMNS)} columns, got {len(values)}"
            )
        row = dict(zip(_COLUMNS, values, strict=True))
        row["location"] = int(row["location"])
        row["mismatches"] = int(row["mismatches"])
        sites.append(row)
    return sites
