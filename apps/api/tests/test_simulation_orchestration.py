"""Exact engine dispatch and required/optional execution behavior."""

from dataclasses import dataclass, field
from subprocess import CalledProcessError, TimeoutExpired

import pytest

from app.modules.simulation import (
    EngineExecutionError,
    EngineRegistry,
    EngineResult,
    ExecutionArtifact,
    PlanInput,
    SimulationStage,
    StageSetting,
    build_simulation_plan,
    execute_plan,
)

RESEARCH_ID = "sha256:" + "1" * 64
GUIDE_ID = "sha256:" + "2" * 64
RESULT_ID = "sha256:" + "3" * 64


@pytest.mark.parametrize("failure", [
    ValueError("private sequence"), TimeoutError("private path"),
    TimeoutExpired("private command", 1), CalledProcessError(1, "private command"),
])
@pytest.mark.parametrize("requirement", ["required", "optional"])
def test_unexpected_adapter_errors_preserve_prior_results_and_stage_semantics(failure, requirement):
    class UnexpectedEngine(FakeEngine):
        def execute(self, request):
            if request.operation == "break":
                raise failure
            return super().execute(request)

    engine = UnexpectedEngine("casai.sequence", "1", frozenset({"edit", "break", "score"}))
    execution = execute_plan(_plan(
        _stage("edit", "edit"), _stage("broken", "break", requirement=requirement),
        _stage("score", "score"),
    ), EngineRegistry((engine,)))
    assert execution.stages[0].artifacts[0].artifact_id == RESULT_ID
    assert execution.stages[1].error == f"engine execution failed: {type(failure).__name__}"
    assert "private" not in execution.model_dump_json()
    assert execution.stages[1].artifacts == ()
    assert execution.stages[2].status == ("skipped" if requirement == "required" else "succeeded")
    assert execution.status == ("failed" if requirement == "required" else "partial")


def test_invalid_adapter_result_is_recorded_as_failure():
    class InvalidEngine(FakeEngine):
        def execute(self, request):
            return {"artifacts": [{"invalid": "private"}]}

    engine = InvalidEngine("casai.sequence", "1", frozenset({"edit"}))
    outcome = execute_plan(_plan(_stage("edit", "edit")), EngineRegistry((engine,)))
    assert outcome.status == "failed"
    assert outcome.stages[0].error == "engine execution failed: ValidationError"


def test_process_control_exceptions_are_not_swallowed():
    class InterruptedEngine(FakeEngine):
        def execute(self, request):
            raise KeyboardInterrupt

    engine = InterruptedEngine("casai.sequence", "1", frozenset({"edit"}))
    with pytest.raises(KeyboardInterrupt):
        execute_plan(_plan(_stage("edit", "edit")), EngineRegistry((engine,)))


@dataclass
class FakeEngine:
    engine: str
    version: str
    operations: frozenset[str]
    fail_operations: frozenset[str] = frozenset()
    requests: list = field(default_factory=list)

    def execute(self, request):
        self.requests.append(request)
        if request.operation in self.fail_operations:
            raise EngineExecutionError(f"engine failed during {request.operation}")
        return EngineResult(
            artifacts=(
                ExecutionArtifact(
                    artifact_type=f"{request.stage_id}.result",
                    artifact_id=RESULT_ID,
                    claim_type="heuristic",
                ),
            )
        )


def _inputs():
    return (
        PlanInput(
            kind="confirmed_research_version",
            artifact_id=RESEARCH_ID,
            approval_state="confirmed",
        ),
        PlanInput(kind="guide_map", artifact_id=GUIDE_ID, approval_state="approved"),
    )


def _stage(stage_id, operation, requirement="required", depends_on=()):
    return SimulationStage(
        stage_id=stage_id,
        engine="casai.sequence",
        engine_version="1",
        operation=operation,
        requirement=requirement,
        depends_on=depends_on,
        settings=(StageSetting(name="editor", value="CBE"),),
    )


def _plan(*stages):
    return build_simulation_plan(
        inputs=_inputs(),
        stages=stages,
        status="approved",
    )


def test_exact_registered_engine_executes_and_passes_prior_artifacts():
    engine = FakeEngine(
        engine="casai.sequence",
        version="1",
        operations=frozenset({"edit", "score"}),
    )
    execution = execute_plan(
        _plan(_stage("edit", "edit"), _stage("score", "score", depends_on=("edit",))),
        EngineRegistry((engine,)),
    )

    assert execution.status == "completed"
    assert [item.status for item in execution.stages] == ["succeeded", "succeeded"]
    assert engine.requests[0].upstream_artifacts == ()
    assert engine.requests[0].plan_inputs == _inputs()
    assert engine.requests[1].upstream_artifacts[0].artifact_id == RESULT_ID


def test_unavailable_required_engine_fails_and_stops_later_stages():
    execution = execute_plan(
        _plan(_stage("edit", "edit"), _stage("score", "score")),
        EngineRegistry(),
    )

    assert execution.status == "failed"
    assert execution.stages[0].status == "failed"
    assert "engine unavailable" in execution.stages[0].error
    assert execution.stages[1].status == "skipped"


def test_registry_never_substitutes_version_or_operation():
    engine = FakeEngine(
        engine="casai.sequence",
        version="2",
        operations=frozenset({"other"}),
    )
    registry = EngineRegistry((engine,))

    with pytest.raises(EngineExecutionError, match="engine unavailable"):
        registry.resolve(_stage("edit", "edit"))

    matching_version = FakeEngine(
        engine="casai.sequence",
        version="1",
        operations=frozenset({"other"}),
    )
    with pytest.raises(EngineExecutionError, match="operation unavailable"):
        EngineRegistry((matching_version,)).resolve(_stage("edit", "edit"))


def test_optional_failure_is_partial_and_independent_work_continues():
    engine = FakeEngine(
        engine="casai.sequence",
        version="1",
        operations=frozenset({"annotate", "edit"}),
        fail_operations=frozenset({"annotate"}),
    )
    execution = execute_plan(
        _plan(
            _stage("annotation", "annotate", requirement="optional"),
            _stage("edit", "edit"),
        ),
        EngineRegistry((engine,)),
    )

    assert execution.status == "partial"
    assert [item.status for item in execution.stages] == ["failed", "succeeded"]
    assert [request.operation for request in engine.requests] == ["annotate", "edit"]


def test_failed_dependency_skips_optional_dependent_stage():
    engine = FakeEngine(
        engine="casai.sequence",
        version="1",
        operations=frozenset({"annotate", "render"}),
        fail_operations=frozenset({"annotate"}),
    )
    execution = execute_plan(
        _plan(
            _stage("annotation", "annotate", requirement="optional"),
            _stage(
                "render",
                "render",
                requirement="optional",
                depends_on=("annotation",),
            ),
        ),
        EngineRegistry((engine,)),
    )

    assert execution.status == "partial"
    assert execution.stages[1].status == "skipped"
    assert execution.stages[1].error == "dependency unavailable: annotation"


def test_failed_dependency_fails_required_dependent_and_halts():
    engine = FakeEngine(
        engine="casai.sequence",
        version="1",
        operations=frozenset({"annotate", "edit", "score"}),
        fail_operations=frozenset({"annotate"}),
    )
    execution = execute_plan(
        _plan(
            _stage("annotation", "annotate", requirement="optional"),
            _stage("edit", "edit", depends_on=("annotation",)),
            _stage("score", "score"),
        ),
        EngineRegistry((engine,)),
    )

    assert execution.status == "failed"
    assert [item.status for item in execution.stages] == ["failed", "failed", "skipped"]
    assert [request.operation for request in engine.requests] == ["annotate"]


def test_draft_plan_cannot_execute():
    plan = build_simulation_plan(inputs=_inputs(), stages=(_stage("edit", "edit"),))
    with pytest.raises(ValueError, match="approved executable"):
        execute_plan(plan, EngineRegistry())


def test_duplicate_registration_and_empty_operation_set_are_rejected():
    engine = FakeEngine("casai.sequence", "1", frozenset({"edit"}))
    registry = EngineRegistry((engine,))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(engine)

    with pytest.raises(ValueError, match="at least one operation"):
        EngineRegistry((FakeEngine("empty", "1", frozenset()),))


def test_execution_identity_is_deterministic():
    engine = FakeEngine("casai.sequence", "1", frozenset({"edit"}))
    plan = _plan(_stage("edit", "edit"))

    first = execute_plan(plan, EngineRegistry((engine,)))
    second = execute_plan(plan, EngineRegistry((engine,)))

    assert first == second
    assert first.execution_id == second.execution_id
