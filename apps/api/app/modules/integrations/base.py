from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Protocol, Sequence

_CAPTURE_LIMIT = 20_000


@dataclass(frozen=True)
class CompletedCommand:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int


class CommandRunner(Protocol):
    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: int,
        stdin: str | None = None,
    ) -> CompletedCommand: ...


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: int,
    stdin: str | None = None,
) -> CompletedCommand:
    """Run an external tool without a shell and retain bounded diagnostic output."""
    args = tuple(str(part) for part in command)
    started_at = datetime.now(UTC)
    started_clock = perf_counter()
    try:
        process = subprocess.run(
            args,
            cwd=cwd,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolExecutionError(
            tool=args[0],
            message=f"executable not found: {args[0]}",
            command=args,
        ) from exc
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((perf_counter() - started_clock) * 1000)
        raise ToolExecutionError(
            tool=args[0],
            message=f"timed out after {timeout} seconds",
            command=args,
            duration_ms=duration_ms,
            stdout=_bounded(exc.stdout),
            stderr=_bounded(exc.stderr),
        ) from exc

    completed_at = datetime.now(UTC)
    completed = CompletedCommand(
        command=args,
        returncode=process.returncode,
        stdout=_bounded(process.stdout),
        stderr=_bounded(process.stderr),
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=round((perf_counter() - started_clock) * 1000),
    )
    if completed.returncode:
        raise ToolExecutionError.from_completed(
            completed,
            message=f"exited with status {completed.returncode}",
        )
    return completed


@dataclass(frozen=True)
class ToolExecution:
    tool: str
    operation: str
    version: str | None
    command: tuple[str, ...]
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    inputs: dict
    outputs: dict
    result: dict
    stdout: str = field(repr=False, default="")
    stderr: str = field(repr=False, default="")

    def provenance_payload(self) -> dict:
        return {
            "tool": self.tool,
            "operation": self.operation,
            "tool_version": self.version,
            "command": list(self.command),
            "inputs": self.inputs,
            "outputs": self.outputs,
            "result": _provenance_summary(self.result),
            "return_code": 0,
            "stderr": self.stderr or None,
        }


class ToolExecutionError(RuntimeError):
    def __init__(
        self,
        *,
        tool: str,
        message: str,
        command: Sequence[str] = (),
        duration_ms: int | None = None,
        return_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        super().__init__(f"{tool}: {message}")
        self.tool = tool
        self.message = message
        self.command = tuple(command)
        self.duration_ms = duration_ms
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr

    @classmethod
    def from_completed(
        cls, completed: CompletedCommand, *, message: str
    ) -> ToolExecutionError:
        return cls(
            tool=completed.command[0],
            message=message,
            command=completed.command,
            duration_ms=completed.duration_ms,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def provenance_payload(self) -> dict:
        return {
            "tool": self.tool,
            "command": list(self.command),
            "return_code": self.return_code,
            "error": self.message,
            "stderr": self.stderr or None,
        }


def file_fingerprint(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def text_fingerprint(value: str) -> dict:
    encoded = value.encode()
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "size_bytes": len(encoded)}


def detect_version(
    runner: CommandRunner,
    command: Sequence[str],
    *,
    timeout: int = 15,
) -> str | None:
    try:
        completed = runner(command, timeout=timeout)
    except ToolExecutionError as exc:
        text = (exc.stdout or exc.stderr).strip()
        return text.splitlines()[0][:_CAPTURE_LIMIT] if text else None
    text = (completed.stdout or completed.stderr).strip()
    return text.splitlines()[0][:_CAPTURE_LIMIT] if text else None


def redact_command_values(command: Sequence[str], flags: set[str]) -> tuple[str, ...]:
    redacted: list[str] = []
    hide_next = False
    for part in command:
        if hide_next:
            redacted.append("<redacted>")
            hide_next = False
            continue
        redacted.append(str(part))
        hide_next = part in flags
    return tuple(redacted)


def _bounded(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    if len(value) <= _CAPTURE_LIMIT:
        return value
    return value[:_CAPTURE_LIMIT] + "\n...[truncated]"


def _provenance_summary(result: dict) -> dict:
    """Keep provenance queryable without copying potentially huge result tables."""
    summary: dict = {}
    for key, value in result.items():
        if isinstance(value, list):
            summary[f"{key}_count"] = len(value)
        elif isinstance(value, dict):
            summary[key] = {
                nested_key: nested_value
                for nested_key, nested_value in value.items()
                if not isinstance(nested_value, (list, dict))
            }
        else:
            summary[key] = value
    return summary
