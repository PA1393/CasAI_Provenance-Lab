"""V2 local execution journal. No public execution/approval authority is introduced.

Each invocation gets a server nonce; immutable revisions survive restarts without
reinterpreting v1 deterministic sessions as distinct invocations. Callers retain
revision IDs. A mutable latest pointer / distributed job queue is not provided.
"""

from __future__ import annotations

import secrets
from typing import Literal

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import Contract, checksum
from app.modules.information_processor.workspace import LocalWorkspace, WorkspaceIntegrityError
from app.modules.simulation.orchestration import PlanExecution
from app.modules.simulation.planning import SimulationPlan, canonical_identity

HASH = r"^sha256:[0-9a-f]{64}$"
TERMINAL = {"completed", "partial", "failed", "cancelled"}
RETRYABLE = {"partial", "failed", "cancelled"}
MAX_JOURNAL_BYTES = 4_000_000


class DurableAttempt(Contract):
    attempt_id: str = Field(pattern=HASH)
    ordinal: int = Field(ge=1, strict=True)
    retry_of: str | None = Field(default=None, pattern=HASH)
    status: Literal["pending", "running", "completed", "partial", "failed", "cancelled"]
    execution: PlanExecution | None = None
    cancellation_reason: str | None = Field(default=None, max_length=500)


class DurableSession(Contract):
    schema_version: Literal["casai.execution-session.v2"] = "casai.execution-session.v2"
    session_id: str = Field(pattern=HASH)
    plan_id: str = Field(pattern=HASH)
    invocation_nonce: str = Field(pattern=r"^[0-9a-f]{32}$")
    previous_revision: str | None = Field(default=None, pattern=HASH)
    attempts: tuple[DurableAttempt, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_lineage(self):
        if self.session_id != canonical_identity({
            "schema_version": self.schema_version, "plan_id": self.plan_id,
            "invocation_nonce": self.invocation_nonce,
        }):
            raise ValueError("Session identity must bind a unique invocation")
        previous = None
        for ordinal, attempt in enumerate(self.attempts, 1):
            parent = previous.attempt_id if previous else None
            expected = canonical_identity({"session_id": self.session_id,
                                           "ordinal": ordinal, "retry_of": parent})
            if (attempt.ordinal, attempt.retry_of, attempt.attempt_id) != (
                ordinal, parent, expected,
            ):
                raise ValueError("Attempt identity must bind its session and retry parent")
            if previous and previous.status not in RETRYABLE:
                raise ValueError("Only a retryable terminal attempt can have a successor")
            if ordinal < len(self.attempts) and attempt.status not in TERMINAL:
                raise ValueError("Only the latest attempt may be active")
            if attempt.status in {"completed", "partial", "failed"}:
                if (attempt.execution is None or attempt.execution.plan_id != self.plan_id
                        or attempt.execution.status != attempt.status):
                    raise ValueError("Finished attempt must contain its exact plan outcome")
            elif attempt.execution is not None:
                raise ValueError("Unfinished/cancelled attempts cannot publish an outcome")
            if (attempt.status == "cancelled") != bool(
                attempt.cancellation_reason and attempt.cancellation_reason.strip()
            ):
                raise ValueError("Only cancellation requires a nonempty reason")
            previous = attempt
        return self


def _pending(session_id: str, ordinal: int, retry_of: str | None) -> dict:
    return {"attempt_id": canonical_identity({"session_id": session_id,
            "ordinal": ordinal, "retry_of": retry_of}), "ordinal": ordinal,
            "retry_of": retry_of, "status": "pending"}


def create_durable_session(plan: SimulationPlan) -> DurableSession:
    if plan.status != "approved" or not plan.executable:
        raise ValueError("An approved executable plan is required")
    values = {"schema_version": "casai.execution-session.v2", "plan_id": plan.plan_id,
              "invocation_nonce": secrets.token_hex(16)}
    session_id = canonical_identity(values)
    return DurableSession(session_id=session_id, attempts=(_pending(session_id, 1, None),),
                          **values)


def revision_id(session: DurableSession) -> str:
    return checksum(session.model_dump_json().encode("utf-8"))


def transition_session(
    session: DurableSession, action: Literal["start", "finish", "cancel", "retry"],
    *, execution: PlanExecution | None = None, reason: str | None = None,
) -> DurableSession:
    values = session.model_dump(round_trip=True)
    attempts = list(values["attempts"])
    values["attempts"] = attempts
    latest = attempts[-1]
    status = latest["status"]
    if action == "start" and status == "pending" and execution is None and reason is None:
        latest["status"] = "running"
    elif action == "finish" and status == "running" and execution and reason is None:
        latest.update(status=execution.status, execution=execution.model_dump(round_trip=True))
    elif action == "cancel" and status in {"pending", "running"} and execution is None:
        latest.update(status="cancelled", cancellation_reason=reason)
    elif action == "retry" and status in RETRYABLE and execution is None and reason is None:
        attempts.append(_pending(session.session_id, len(attempts) + 1, latest["attempt_id"]))
    else:
        raise ValueError("Invalid execution-session transition")
    values["previous_revision"] = revision_id(session)
    return DurableSession.model_validate(values)


def save_session(workspace: LocalWorkspace, session: DurableSession) -> str:
    session = DurableSession.model_validate(session.model_dump(round_trip=True))
    if session.previous_revision:
        parent = load_session(workspace, session.previous_revision)
        latest = session.attempts[-1]
        allowed = []
        for action in ("start", "finish", "cancel", "retry"):
            try:
                allowed.append(transition_session(
                    parent, action,
                    execution=latest.execution if action == "finish" else None,
                    reason=latest.cancellation_reason if action == "cancel" else None,
                ))
            except ValueError:
                pass
        if session not in allowed:
            raise ValueError("Revision does not represent a valid transition from its parent")
    elif len(session.attempts) != 1 or session.attempts[0].status != "pending":
        raise ValueError("An initial journal revision must contain one pending attempt")
    content = session.model_dump_json().encode("utf-8")
    if len(content) > MAX_JOURNAL_BYTES:
        raise ValueError("Execution journal exceeds its byte budget")
    identity = checksum(content)
    workspace._store_artifact(identity, content)
    return identity


def load_session(workspace: LocalWorkspace, identity: str) -> DurableSession:
    path = workspace.artifact_path(identity)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JOURNAL_BYTES:
        raise WorkspaceIntegrityError("Execution journal is unavailable or unsafe")
    content = path.read_bytes()
    if checksum(content) != identity:
        raise WorkspaceIntegrityError("Execution journal checksum does not match")
    try:
        return DurableSession.model_validate_json(content)
    except ValueError as exc:
        raise WorkspaceIntegrityError("Execution journal failed contract checks") from exc
