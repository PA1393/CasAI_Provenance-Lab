"""Typed, content-addressed plans for transparent computational workflows."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import Contract, checksum

ArtifactKind = Literal[
    "confirmed_research_version",
    "guide_map",
    "guide_ranking",
    "enzyme_map",
]
ApprovalState = Literal["draft", "confirmed", "approved", "rejected"]
StageRequirement = Literal["required", "optional"]
PlanStatus = Literal["draft", "approved", "rejected"]
JsonScalar = str | int | float | bool | None

_READY_INPUT_STATES: dict[str, frozenset[str]] = {
    "confirmed_research_version": frozenset({"confirmed"}),
    "guide_map": frozenset({"approved"}),
    "guide_ranking": frozenset({"approved"}),
    "enzyme_map": frozenset({"approved"}),
}


def canonical_identity(values: dict[str, object]) -> str:
    return checksum(
        json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )


class PlanInput(Contract):
    kind: ArtifactKind
    artifact_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_state: ApprovalState

    @model_validator(mode="after")
    def validate_state(self) -> PlanInput:
        if self.approval_state == "confirmed" and self.kind != "confirmed_research_version":
            raise ValueError("Only a research version uses the confirmed input state")
        if self.approval_state == "approved" and self.kind == "confirmed_research_version":
            raise ValueError("A research version must use the confirmed input state")
        return self

    @property
    def ready(self) -> bool:
        return self.approval_state in _READY_INPUT_STATES[self.kind]


class StageSetting(Contract):
    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    value: JsonScalar


class SimulationStage(Contract):
    stage_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    engine: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    engine_version: str = Field(min_length=1, max_length=128)
    operation: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    requirement: StageRequirement
    depends_on: tuple[str, ...] = ()
    settings: tuple[StageSetting, ...] = ()
    claim_type: Literal["explanatory"] = "explanatory"

    @model_validator(mode="after")
    def validate_stage(self) -> SimulationStage:
        if self.stage_id in self.depends_on:
            raise ValueError("A simulation stage cannot depend on itself")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError("Simulation stage dependencies must be unique")
        names = tuple(setting.name for setting in self.settings)
        if len(set(names)) != len(names):
            raise ValueError("Simulation stage setting names must be unique")
        return self


class SimulationPlan(Contract):
    schema_version: Literal["casai.simulation-plan.v1"] = "casai.simulation-plan.v1"
    plan_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: PlanStatus
    executable: bool = Field(strict=True)
    inputs: tuple[PlanInput, ...]
    stages: tuple[SimulationStage, ...]
    limitations: tuple[str, ...] = ()
    claim_type: Literal["explanatory"] = "explanatory"

    @model_validator(mode="after")
    def validate_plan(self) -> SimulationPlan:
        if not self.inputs:
            raise ValueError("A simulation plan requires at least one input")
        input_keys = tuple((item.kind, item.artifact_id) for item in self.inputs)
        if len(set(input_keys)) != len(input_keys):
            raise ValueError("Simulation plan inputs must be unique")
        kinds = {item.kind for item in self.inputs}
        if "confirmed_research_version" not in kinds or "guide_map" not in kinds:
            raise ValueError("A simulation plan requires confirmed research and guide inputs")

        if not self.stages:
            raise ValueError("A simulation plan requires at least one stage")
        seen: set[str] = set()
        for stage in self.stages:
            if stage.stage_id in seen:
                raise ValueError("Simulation stage identifiers must be unique")
            missing = set(stage.depends_on) - seen
            if missing:
                raise ValueError("Stage dependencies must reference earlier plan stages")
            seen.add(stage.stage_id)

        expected_executable = self.status == "approved" and all(
            item.ready for item in self.inputs
        )
        if self.executable != expected_executable:
            raise ValueError("Plan executability must derive from approval and input states")
        if self.status == "approved" and not self.executable:
            raise ValueError("An approved plan cannot contain unconfirmed or rejected inputs")

        identity = self.model_dump(round_trip=True, exclude={"plan_id"})
        if self.plan_id != canonical_identity(identity):
            raise ValueError("Plan identity must match canonical planning content")
        return self


def build_simulation_plan(
    *,
    inputs: tuple[PlanInput, ...],
    stages: tuple[SimulationStage, ...],
    status: PlanStatus = "draft",
    limitations: tuple[str, ...] = (),
) -> SimulationPlan:
    """Create a deterministic plan; approval never repairs unresolved inputs."""

    executable = status == "approved" and all(item.ready for item in inputs)
    values: dict[str, object] = {
        "schema_version": "casai.simulation-plan.v1",
        "status": status,
        "executable": executable,
        "inputs": [item.model_dump(mode="json") for item in inputs],
        "stages": [stage.model_dump(mode="json") for stage in stages],
        "limitations": list(limitations),
        "claim_type": "explanatory",
    }
    return SimulationPlan(plan_id=canonical_identity(values), **values)
