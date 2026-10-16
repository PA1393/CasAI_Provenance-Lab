from datetime import UTC, datetime, timedelta

import pytest

from app.modules.integrations.base import (
    CompletedCommand,
    ToolExecution,
    ToolExecutionError,
)
from app.modules.integrations.indelphi import InDelphiAdapter
from app.modules.provenance import service


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


def _execution() -> ToolExecution:
    now = datetime.now(UTC)
    return ToolExecution(
        tool="inDelphi",
        operation="repair_outcome_prediction",
        version="1.0",
        command=("/venv/indelphi/bin/python", "indelphi_worker.py"),
        started_at=now,
        completed_at=now,
        duration_ms=37,
        inputs={"sequence": {"sha256": "abc", "size_bytes": 120}},
        outputs={},
        result={"prediction_count": 3, "predictions": [{}, {}, {}]},
    )


def test_indelphi_uses_isolated_worker_and_hashes_sequence() -> None:
    observed_stdin = None

    def runner(command, *, cwd=None, timeout, stdin=None):
        nonlocal observed_stdin
        observed_stdin = stdin
        return _completed(
            command,
            stdout=(
                '{"version":"1.0","prediction_count":1,'
                '"predictions":[{"Category":"ins"}],"stats":{"Precision":0.8}}'
            ),
        )

    result = InDelphiAdapter(
        python="/venv/indelphi/bin/python",
        model_dir="/models/indelphi",
        runner=runner,
    ).predict(sequence="ACGT" * 30, cutsite=60, cell_type="mESC")

    assert '"model_dir": "/models/indelphi"' in observed_stdin
    assert result.command[0] == "/venv/indelphi/bin/python"
    assert result.version == "1.0"
    assert result.result["prediction_count"] == 1
    assert result.inputs["sequence"]["sha256"]
    assert "ACGT" not in str(result.inputs["sequence"])


def test_indelphi_rejects_non_json_worker_output() -> None:
    def runner(command, *, cwd=None, timeout, stdin=None):
        return _completed(command, stdout="not-json")

    with pytest.raises(ToolExecutionError, match="worker returned invalid JSON") as captured:
        InDelphiAdapter(runner=runner).predict(sequence="ACGT", cutsite=2)

    assert captured.value.tool == "inDelphi"


def test_execute_with_provenance_emits_success(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(service, "emit", lambda *args, **kwargs: events.append((args, kwargs)))

    result = service.execute_with_provenance(
        run_id="run-1",
        stage="score",
        operation=_execution,
    )

    assert result.tool == "inDelphi"
    args, kwargs = events[0]
    assert args[:3] == ("run-1", "score", "scientific_tool_completed")
    assert kwargs["duration_ms"] == 37
    assert kwargs["payload"]["tool_version"] == "1.0"
    assert kwargs["payload"]["result"] == {
        "prediction_count": 3,
        "predictions_count": 3,
    }


def test_execute_with_provenance_emits_failure_and_reraises(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(service, "emit", lambda *args, **kwargs: events.append((args, kwargs)))

    def fail():
        raise ToolExecutionError(
            tool="inDelphi",
            message="exited with status 1",
            command=("python", "indelphi_worker.py"),
            duration_ms=14,
            return_code=1,
            stderr="model load failed",
        )

    with pytest.raises(ToolExecutionError, match="exited with status 1"):
        service.execute_with_provenance(
            run_id="run-1",
            stage="simulate",
            operation=fail,
        )

    args, kwargs = events[0]
    assert args[:3] == ("run-1", "simulate", "scientific_tool_failed")
    assert kwargs["duration_ms"] == 14
    assert kwargs["payload"]["return_code"] == 1
    assert kwargs["payload"]["stderr"] == "model load failed"
