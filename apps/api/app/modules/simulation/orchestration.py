"""Exact engine dispatch and deterministic required/optional stage semantics."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import Contract
from app.modules.simulation.planning import (
    PlanInput,
    SimulationPlan,
    SimulationStage,
    StageSetting,
    canonical_identity,
)

ResultClaim = Literal["heuristic", "predicted", "explanatory"]


class ExecutionArtifact(Contract):
    artifact_type: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    artifact_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    claim_type: ResultClaim


class EngineResult(Contract):
    artifacts: tuple[ExecutionArtifact, ...] = ()
    notices: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> EngineResult:
        identities = tuple(artifact.artifact_id for artifact in self.artifacts)
        if len(set(identities)) != len(identities):
            raise ValueError("Engine result artifact identities must be unique")
        return self


class EngineRequest(Contract):
    plan_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    stage_id: str
    operation: str
    settings: tuple[StageSetting, ...]
    plan_inputs: tuple[PlanInput, ...]
    upstream_artifacts: tuple[ExecutionArtifact, ...]


class EngineAdapter(Protocol):
    engine: str
    version: str
    operations: frozenset[str]

    def execute(self, request: EngineRequest) -> EngineResult: ...


class EngineExecutionError(RuntimeError):
    """Expected engine or dispatch failure that can be recorded on a plan execution."""


class EngineRegistry:
    """Registry that resolves only an exact engine, version and operation."""

    def __init__(self, adapters: tuple[EngineAdapter, ...] = ()) -> None:
        self._adapters: dict[tuple[str, str], EngineAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: EngineAdapter) -> None:
        key = (adapter.engine, adapter.version)
        if key in self._adapters:
            raise ValueError(f"Engine {adapter.engine}@{adapter.version} is already registered")
        if not adapter.operations:
            raise ValueError("An engine adapter must declare at least one operation")
        self._adapters[key] = adapter

    def resolve(self, stage: SimulationStage) -> EngineAdapter:
        adapter = self._adapters.get((stage.engine, stage.engine_version))
        if adapter is None:
            raise EngineExecutionError(
                f"engine unavailable: {stage.engine}@{stage.engine_version}"
            )
        if stage.operation not in adapter.operations:
            raise EngineExecutionError(
                f"operation unavailable: {stage.engine}@{stage.engine_version} "
                f"does not provide {stage.operation}"
            )
        return adapter


class StageExecution(Contract):
    stage_id: str
    requirement: Literal["required", "optional"]
    status: Literal["succeeded", "failed", "skipped"]
    engine: str
    engine_version: str
    operation: str
    artifacts: tuple[ExecutionArtifact, ...] = ()
    notices: tuple[str, ...] = ()
    error: str | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> StageExecution:
        if self.status == "succeeded" and self.error is not None:
            raise ValueError("A successful stage cannot contain an error")
        if self.status != "succeeded" and not self.error:
            raise ValueError("A failed or skipped stage requires an explanation")
        if self.status != "succeeded" and self.artifacts:
            raise ValueError("A failed or skipped stage cannot publish artifacts")
        return self


class PlanExecution(Contract):
    schema_version: Literal["casai.plan-execution.v1"] = "casai.plan-execution.v1"
    execution_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: Literal["completed", "partial", "failed"]
    stages: tuple[StageExecution, ...]
    claim_type: Literal["explanatory"] = "explanatory"

    @model_validator(mode="after")
    def validate_execution(self) -> PlanExecution:
        if not self.stages:
            raise ValueError("A plan execution requires stage outcomes")
        expected = _execution_status(self.stages)
        if self.status != expected:
            raise ValueError("Execution status must derive from stage outcomes")
        identity = self.model_dump(round_trip=True, exclude={"execution_id"})
        if self.execution_id != canonical_identity(identity):
            raise ValueError("Execution identity must match canonical outcome content")
        return self


def execute_plan(plan: SimulationPlan, registry: EngineRegistry) -> PlanExecution:
    """Run an approved plan without substituting engines or hiding partial failures."""

    if plan.status != "approved" or not plan.executable:
        raise ValueError("Only an approved executable simulation plan may run")

    outcomes: list[StageExecution] = []
    outcomes_by_id: dict[str, StageExecution] = {}
    halted = False

    for stage in plan.stages:
        if halted:
            outcome = _not_run(stage, "not run after required-stage failure")
        else:
            unavailable = tuple(
                dependency
                for dependency in stage.depends_on
                if outcomes_by_id[dependency].status != "succeeded"
            )
            if unavailable:
                reason = "dependency unavailable: " + ", ".join(unavailable)
                outcome = (
                    _failed(stage, reason)
                    if stage.requirement == "required"
                    else _not_run(stage, reason)
                )
            else:
                upstream_artifacts = tuple(
                    artifact
                    for dependency in stage.depends_on
                    for artifact in outcomes_by_id[dependency].artifacts
                )
                outcome = _execute_stage(
                    plan,
                    stage,
                    upstream_artifacts,
                    registry,
                )

        outcomes.append(outcome)
        outcomes_by_id[stage.stage_id] = outcome
        if outcome.status == "failed" and stage.requirement == "required":
            halted = True

    values: dict[str, object] = {
        "schema_version": "casai.plan-execution.v1",
        "plan_id": plan.plan_id,
        "status": _execution_status(tuple(outcomes)),
        "stages": [outcome.model_dump(mode="json") for outcome in outcomes],
        "claim_type": "explanatory",
    }
    return PlanExecution(execution_id=canonical_identity(values), **values)


def _execute_stage(
    plan: SimulationPlan,
    stage: SimulationStage,
    artifacts: tuple[ExecutionArtifact, ...],
    registry: EngineRegistry,
) -> StageExecution:
    try:
        adapter = registry.resolve(stage)
        result = EngineResult.model_validate(
            adapter.execute(
                EngineRequest(
                    plan_id=plan.plan_id,
                    stage_id=stage.stage_id,
                    operation=stage.operation,
                    settings=stage.settings,
                    plan_inputs=plan.inputs,
                    upstream_artifacts=artifacts,
                )
            )
        )
    except EngineExecutionError as exc:
        return _failed(stage, str(exc))
    except Exception as exc:
        # Adapter diagnostics may contain researcher data, paths or subprocess output.
        # Record the failure category without leaking those details or losing earlier stages.
        return _failed(stage, f"engine execution failed: {type(exc).__name__}")
    return StageExecution(
        stage_id=stage.stage_id,
        requirement=stage.requirement,
        status="succeeded",
        engine=stage.engine,
        engine_version=stage.engine_version,
        operation=stage.operation,
        artifacts=result.artifacts,
        notices=result.notices,
    )


def _failed(stage: SimulationStage, error: str) -> StageExecution:
    return StageExecution(
        stage_id=stage.stage_id,
        requirement=stage.requirement,
        status="failed",
        engine=stage.engine,
        engine_version=stage.engine_version,
        operation=stage.operation,
        error=error,
    )


def _not_run(stage: SimulationStage, error: str) -> StageExecution:
    return StageExecution(
        stage_id=stage.stage_id,
        requirement=stage.requirement,
        status="skipped",
        engine=stage.engine,
        engine_version=stage.engine_version,
        operation=stage.operation,
        error=error,
    )


def _execution_status(
    stages: tuple[StageExecution, ...],
) -> Literal["completed", "partial", "failed"]:
    if any(stage.requirement == "required" and stage.status != "succeeded" for stage in stages):
        return "failed"
    if any(stage.status != "succeeded" for stage in stages):
        return "partial"
    return "completed"
