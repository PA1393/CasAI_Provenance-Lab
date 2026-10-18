"""Immutable execution-attempt lineage with explicit retry and cancellation rules."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import Contract
from app.modules.simulation.orchestration import PlanExecution
from app.modules.simulation.planning import SimulationPlan, canonical_identity

AttemptStatus = Literal[
    "pending",
    "running",
    "completed",
    "partial",
    "failed",
    "cancelled",
]
_TERMINAL = frozenset({"completed", "partial", "failed", "cancelled"})
_RETRYABLE = frozenset({"partial", "failed", "cancelled"})


def _attempt_identity(plan_id: str, ordinal: int, retry_of: str | None) -> str:
    return canonical_identity(
        {"plan_id": plan_id, "ordinal": ordinal, "retry_of": retry_of}
    )


class ExecutionAttempt(Contract):
    attempt_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ordinal: int = Field(gt=0, strict=True)
    retry_of: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    status: AttemptStatus
    execution: PlanExecution | None = None
    cancellation_reason: str | None = None

    @model_validator(mode="after")
    def validate_attempt(self) -> ExecutionAttempt:
        if self.attempt_id != _attempt_identity(self.plan_id, self.ordinal, self.retry_of):
            raise ValueError("Attempt identity must match its plan and retry lineage")
        if self.retry_of == self.attempt_id:
            raise ValueError("An execution attempt cannot retry itself")
        if self.status in {"completed", "partial", "failed"}:
            if self.execution is None or self.execution.status != self.status:
                raise ValueError("Finished attempt status must match its execution")
        elif self.execution is not None:
            raise ValueError("Only a finished attempt may contain an execution")
        if self.status == "cancelled":
            if not self.cancellation_reason or not self.cancellation_reason.strip():
                raise ValueError("A cancelled attempt requires a reason")
        elif self.cancellation_reason is not None:
            raise ValueError("Only a cancelled attempt may contain a cancellation reason")
        return self


class ExecutionSession(Contract):
    schema_version: Literal["casai.execution-session.v1"] = "casai.execution-session.v1"
    session_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    attempts: tuple[ExecutionAttempt, ...]

    @model_validator(mode="after")
    def validate_session(self) -> ExecutionSession:
        if not self.attempts:
            raise ValueError("An execution session requires an attempt")
        if self.session_id != canonical_identity(
            {"schema_version": self.schema_version, "plan_id": self.plan_id}
        ):
            raise ValueError("Session identity must match its plan")
        ids = tuple(attempt.attempt_id for attempt in self.attempts)
        if len(set(ids)) != len(ids):
            raise ValueError("Execution attempt identities must be unique")
        if tuple(attempt.ordinal for attempt in self.attempts) != tuple(
            range(1, len(self.attempts) + 1)
        ):
            raise ValueError("Execution attempt ordinals must be contiguous")

        prior: dict[str, ExecutionAttempt] = {}
        for attempt in self.attempts:
            if attempt.plan_id != self.plan_id:
                raise ValueError("Every execution attempt must reference the session plan")
            if attempt.ordinal == 1 and attempt.retry_of is not None:
                raise ValueError("The first execution attempt cannot be a retry")
            if attempt.ordinal > 1:
                parent = prior.get(attempt.retry_of or "")
                if parent is None or parent.status not in _RETRYABLE:
                    raise ValueError("A retry must reference an earlier retryable attempt")
            prior[attempt.attempt_id] = attempt

        active = [attempt for attempt in self.attempts if attempt.status not in _TERMINAL]
        if len(active) > 1 or (active and active[0] != self.attempts[-1]):
            raise ValueError("Only the latest execution attempt may be active")
        return self


def create_execution_session(plan: SimulationPlan) -> ExecutionSession:
    if plan.status != "approved" or not plan.executable:
        raise ValueError("Only an approved executable plan may create a session")
    session_values = {
        "schema_version": "casai.execution-session.v1",
        "plan_id": plan.plan_id,
    }
    attempt = _new_attempt(plan.plan_id, ordinal=1, retry_of=None)
    return ExecutionSession(
        session_id=canonical_identity(session_values),
        attempts=(attempt,),
        **session_values,
    )


def start_attempt(session: ExecutionSession, attempt_id: str) -> ExecutionSession:
    attempt = _find_attempt(session, attempt_id)
    if attempt != session.attempts[-1] or attempt.status != "pending":
        raise ValueError("Only the latest pending attempt may start")
    return _replace_attempt(session, _copy_attempt(attempt, status="running"))


def finish_attempt(
    session: ExecutionSession,
    attempt_id: str,
    execution: PlanExecution,
) -> ExecutionSession:
    attempt = _find_attempt(session, attempt_id)
    if attempt != session.attempts[-1] or attempt.status != "running":
        raise ValueError("Only the latest running attempt may finish")
    if execution.plan_id != session.plan_id:
        raise ValueError("Execution result must reference the session plan")
    return _replace_attempt(
        session,
        _copy_attempt(attempt, status=execution.status, execution=execution),
    )


def cancel_attempt(
    session: ExecutionSession,
    attempt_id: str,
    reason: str,
) -> ExecutionSession:
    attempt = _find_attempt(session, attempt_id)
    if attempt != session.attempts[-1] or attempt.status not in {"pending", "running"}:
        raise ValueError("Only the latest pending or running attempt may be cancelled")
    if not reason.strip():
        raise ValueError("Cancellation requires a reason")
    return _replace_attempt(
        session,
        _copy_attempt(attempt, status="cancelled", cancellation_reason=reason.strip()),
    )


def retry_attempt(session: ExecutionSession, attempt_id: str) -> ExecutionSession:
    attempt = _find_attempt(session, attempt_id)
    if attempt.status not in _RETRYABLE:
        raise ValueError("Only a partial, failed or cancelled attempt may be retried")
    if any(item.status not in _TERMINAL for item in session.attempts):
        raise ValueError("An active attempt must finish before another retry")
    retry = _new_attempt(
        session.plan_id,
        ordinal=len(session.attempts) + 1,
        retry_of=attempt.attempt_id,
    )
    return ExecutionSession.model_validate(
        {**session.model_dump(round_trip=True), "attempts": (*session.attempts, retry)}
    )


def _new_attempt(plan_id: str, ordinal: int, retry_of: str | None) -> ExecutionAttempt:
    return ExecutionAttempt(
        attempt_id=_attempt_identity(plan_id, ordinal, retry_of),
        plan_id=plan_id,
        ordinal=ordinal,
        retry_of=retry_of,
        status="pending",
    )


def _find_attempt(session: ExecutionSession, attempt_id: str) -> ExecutionAttempt:
    match = next((item for item in session.attempts if item.attempt_id == attempt_id), None)
    if match is None:
        raise ValueError("Execution attempt not found in session")
    return match


def _replace_attempt(
    session: ExecutionSession,
    replacement: ExecutionAttempt,
) -> ExecutionSession:
    attempts = tuple(
        replacement if attempt.attempt_id == replacement.attempt_id else attempt
        for attempt in session.attempts
    )
    return ExecutionSession.model_validate(
        {**session.model_dump(round_trip=True), "attempts": attempts}
    )


def _copy_attempt(attempt: ExecutionAttempt, **updates: object) -> ExecutionAttempt:
    return ExecutionAttempt.model_validate(
        {**attempt.model_dump(round_trip=True), **updates}
    )
