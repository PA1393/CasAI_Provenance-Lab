from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.modules.integrations.base import (
    CommandRunner,
    ToolExecution,
    ToolExecutionError,
    run_command,
    text_fingerprint,
)

_WORKER = Path(__file__).with_name("indelphi_worker.py")


class InDelphiAdapter:
    """Run inDelphi in its own interpreter to isolate its legacy dependencies."""

    def __init__(
        self,
        *,
        python: str | None = None,
        model_dir: str | None = None,
        timeout: int | None = None,
        runner: CommandRunner = run_command,
    ) -> None:
        self.python = python or settings.indelphi_python
        self.model_dir = model_dir if model_dir is not None else settings.indelphi_model_dir
        self.timeout = timeout or settings.scientific_tool_timeout_seconds
        self.runner = runner

    def predict(
        self,
        *,
        sequence: str,
        cutsite: int,
        cell_type: str = "mESC",
    ) -> ToolExecution:
        request = {
            "sequence": sequence.upper(),
            "cutsite": cutsite,
            "cell_type": cell_type,
            "model_dir": self.model_dir,
        }
        try:
            completed = self.runner(
                [self.python, str(_WORKER)],
                timeout=self.timeout,
                stdin=json.dumps(request),
            )
        except ToolExecutionError as exc:
            raise ToolExecutionError(
                tool="inDelphi",
                message=exc.message,
                command=exc.command,
                duration_ms=exc.duration_ms,
                return_code=exc.return_code,
                stdout=exc.stdout,
                stderr=exc.stderr,
            ) from exc
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ToolExecutionError(
                tool="inDelphi",
                message="worker returned invalid JSON",
                command=completed.command,
                duration_ms=completed.duration_ms,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            ) from exc
        if not isinstance(result, dict):
            raise ToolExecutionError(
                tool="inDelphi",
                message="worker returned a non-object JSON payload",
                command=completed.command,
                duration_ms=completed.duration_ms,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        return ToolExecution(
            tool="inDelphi",
            operation="repair_outcome_prediction",
            version=result.pop("version", None),
            command=completed.command,
            started_at=completed.started_at,
            completed_at=completed.completed_at,
            duration_ms=completed.duration_ms,
            inputs={
                "sequence": text_fingerprint(sequence.upper()),
                "cutsite": cutsite,
                "cell_type": cell_type,
            },
            outputs={},
            result=result,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
