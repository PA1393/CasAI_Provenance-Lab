"""Execution attempt lifecycle, cancellation and retry lineage."""

import pytest
from pydantic import ValidationError

from app.modules.simulation import (
    EngineRegistry,
    EngineResult,
    PlanInput,
    SimulationStage,
    build_simulation_plan,
    cancel_attempt,
    create_execution_session,
    execute_plan,
    finish_attempt,
    retry_attempt,
    start_attempt,
)
from app.modules.simulation.attempts import ExecutionAttempt, ExecutionSession

RESEARCH_ID = "sha256:" + "1" * 64
GUIDE_ID = "sha256:" + "2" * 64


def _plan():
    return build_simulation_plan(
        inputs=(
            PlanInput(
                kind="confirmed_research_version",
                artifact_id=RESEARCH_ID,
                approval_state="confirmed",
            ),
            PlanInput(kind="guide_map", artifact_id=GUIDE_ID, approval_state="approved"),
        ),
        stages=(
            SimulationStage(
                stage_id="edit",
                engine="unavailable.engine",
                engine_version="1",
                operation="edit",
                requirement="required",
            ),
        ),
        status="approved",
    )


def _failed_session():
    plan = _plan()
    session = create_execution_session(plan)
    first = session.attempts[0]
    session = start_attempt(session, first.attempt_id)
    execution = execute_plan(plan, EngineRegistry())
    return plan, finish_attempt(session, first.attempt_id, execution)


def test_session_starts_with_deterministic_pending_attempt():
    plan = _plan()
    first = create_execution_session(plan)
    second = create_execution_session(plan)

    assert first == second
    assert first.session_id == second.session_id
    assert first.attempts[0].status == "pending"
    assert first.attempts[0].ordinal == 1
    assert first.attempts[0].retry_of is None


def test_attempt_must_start_before_it_finishes():
    plan = _plan()
    session = create_execution_session(plan)
    attempt = session.attempts[0]
    execution = execute_plan(plan, EngineRegistry())

    with pytest.raises(ValueError, match="latest running"):
        finish_attempt(session, attempt.attempt_id, execution)

    running = start_attempt(session, attempt.attempt_id)
    finished = finish_attempt(running, attempt.attempt_id, execution)
    assert finished.attempts[0].status == "failed"
    assert finished.attempts[0].execution == execution


def test_retry_creates_new_attempt_and_retains_failed_execution():
    _, failed = _failed_session()
    original = failed.attempts[0]
    retried = retry_attempt(failed, original.attempt_id)

    assert len(retried.attempts) == 2
    assert retried.attempts[0] == original
    assert retried.attempts[0].execution is not None
    assert retried.attempts[1].status == "pending"
    assert retried.attempts[1].retry_of == original.attempt_id
    assert retried.attempts[1].attempt_id != original.attempt_id


def test_cancellation_records_reason_and_preserves_prior_attempt():
    _, failed = _failed_session()
    retried = retry_attempt(failed, failed.attempts[0].attempt_id)
    second = retried.attempts[1]
    running = start_attempt(retried, second.attempt_id)
    cancelled = cancel_attempt(running, second.attempt_id, "researcher stopped run")

    assert cancelled.attempts[0] == failed.attempts[0]
    assert cancelled.attempts[1].status == "cancelled"
    assert cancelled.attempts[1].cancellation_reason == "researcher stopped run"


def test_completed_attempt_cannot_retry_or_cancel():
    class SuccessfulEngine:
        engine = "unavailable.engine"
        version = "1"
        operations = frozenset({"edit"})

        def execute(self, request):
            return EngineResult()

    plan = _plan()
    session = create_execution_session(plan)
    attempt = session.attempts[0]
    running = start_attempt(session, attempt.attempt_id)
    execution = execute_plan(plan, EngineRegistry((SuccessfulEngine(),)))
    completed = finish_attempt(running, attempt.attempt_id, execution)
    finished = completed.attempts[0]

    with pytest.raises(ValueError, match="may be retried"):
        retry_attempt(completed, finished.attempt_id)
    with pytest.raises(ValueError, match="pending or running"):
        cancel_attempt(completed, finished.attempt_id, "too late")


def test_draft_plan_cannot_create_execution_session():
    approved = _plan()
    values = approved.model_dump(round_trip=True)
    values["status"] = "draft"
    values["executable"] = False
    values.pop("plan_id")
    from app.modules.simulation.planning import canonical_identity

    draft = approved.__class__(plan_id=canonical_identity(values), **values)
    with pytest.raises(ValueError, match="approved executable"):
        create_execution_session(draft)


def test_attempt_rejects_forged_identity_and_mismatched_result():
    _, failed = _failed_session()
    values = failed.attempts[0].model_dump(round_trip=True)
    values["attempt_id"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="Attempt identity"):
        ExecutionAttempt.model_validate(values)

    values = failed.attempts[0].model_dump(round_trip=True)
    values["status"] = "partial"
    with pytest.raises(ValidationError, match="must match"):
        ExecutionAttempt.model_validate(values)


def test_only_latest_attempt_may_be_active():
    _, failed = _failed_session()
    retried = retry_attempt(failed, failed.attempts[0].attempt_id)
    second = retried.attempts[1]
    cancelled = cancel_attempt(retried, second.attempt_id, "try another configuration")
    third = retry_attempt(cancelled, failed.attempts[0].attempt_id)
    values = third.model_dump(round_trip=True)
    values["attempts"][1]["status"] = "running"
    values["attempts"][1]["cancellation_reason"] = None
    with pytest.raises(ValidationError, match="Only the latest"):
        ExecutionSession.model_validate(values)
