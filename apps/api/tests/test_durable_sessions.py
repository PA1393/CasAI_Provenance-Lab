import pytest

from app.modules.information_processor.workspace import LocalWorkspace, WorkspaceIntegrityError
from app.modules.simulation import (
    EngineRegistry,
    PlanInput,
    SimulationStage,
    build_simulation_plan,
    execute_plan,
)
from app.modules.simulation.durable import (
    DurableSession,
    create_durable_session,
    load_session,
    save_session,
    transition_session,
)


def plan():
    return build_simulation_plan(inputs=(
        PlanInput(kind="confirmed_research_version", artifact_id="sha256:" + "1" * 64,
                  approval_state="confirmed"),
        PlanInput(kind="guide_map", artifact_id="sha256:" + "2" * 64,
                  approval_state="approved"),
    ), stages=(SimulationStage(stage_id="edit", engine="unavailable.engine",
                              engine_version="1", operation="edit", requirement="required"),),
        status="approved")


def test_invocations_and_attempts_have_unique_identity():
    first, second = create_durable_session(plan()), create_durable_session(plan())
    assert first.plan_id == second.plan_id
    assert first.session_id != second.session_id
    assert first.attempts[0].attempt_id != second.attempts[0].attempt_id


def test_journal_survives_reopen_and_preserves_retry_cancel_history(tmp_path):
    root = tmp_path / "workspace"
    workspace = LocalWorkspace(root)
    initial = create_durable_session(plan())
    initial_id = save_session(workspace, initial)
    running = transition_session(initial, "start")
    running_id = save_session(workspace, running)
    failed = transition_session(running, "finish", execution=execute_plan(plan(), EngineRegistry()))
    failed_id = save_session(workspace, failed)
    retried = transition_session(failed, "retry")
    save_session(workspace, retried)
    cancelled = transition_session(retried, "cancel", reason="Researcher cancelled")
    cancelled_id = save_session(workspace, cancelled)
    reopened = LocalWorkspace(root)
    assert load_session(reopened, cancelled_id) == cancelled
    assert load_session(reopened, initial_id) == initial
    assert load_session(reopened, running_id) == running
    assert load_session(reopened, failed_id).attempts[0].execution.status == "failed"
    assert cancelled.attempts[1].retry_of == failed.attempts[0].attempt_id


def test_journal_rejects_tampering_paths_and_unsafe_transitions(tmp_path):
    workspace = LocalWorkspace(tmp_path / "workspace")
    initial = create_durable_session(plan())
    identity = save_session(workspace, initial)
    with pytest.raises(ValueError):
        transition_session(initial, "retry")
    with pytest.raises(ValueError):
        transition_session(initial, "cancel", reason=" ")
    values = initial.model_dump()
    values["attempts"][0]["attempt_id"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError):
        DurableSession.model_validate(values)
    with pytest.raises(WorkspaceIntegrityError):
        load_session(workspace, "../../escape")
    workspace.artifact_path(identity).write_text("{}")
    with pytest.raises(WorkspaceIntegrityError):
        load_session(workspace, identity)


def test_parent_must_be_persisted_before_transition(tmp_path):
    workspace = LocalWorkspace(tmp_path / "workspace")
    initial = create_durable_session(plan())
    with pytest.raises(WorkspaceIntegrityError):
        save_session(workspace, transition_session(initial, "start"))
