"""Thin API boundary for immutable draft simulation plans."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import get_intake_workspace
from app.modules.information_processor.workspace import (
    DraftNotFoundError,
    LocalWorkspace,
    WorkspaceError,
)
from app.modules.simulation import PlanInput, SimulationPlan, build_simulation_plan
from app.schemas.simulation_plans import SimulationPlanCreateBody

router = APIRouter(prefix="/simulation-plans", tags=["simulation_plans"])
PlanId = Annotated[str, Path(pattern=r"^sha256:[0-9a-f]{64}$")]


@router.post("", response_model=SimulationPlan, status_code=201)
def create_simulation_plan(
    body: SimulationPlanCreateBody,
    workspace: LocalWorkspace = Depends(get_intake_workspace),
) -> SimulationPlan:
    try:
        workspace.load_confirmed_version(body.confirmed_version_id)
        guide_map = workspace.load_guide_map(body.guide_map_id)
        if guide_map.source_version_id != body.confirmed_version_id:
            raise HTTPException(
                status_code=422,
                detail="Guide map is not bound to the confirmed research version",
            )
        inputs = [
            PlanInput(
                kind="confirmed_research_version",
                artifact_id=body.confirmed_version_id,
                approval_state="confirmed",
            ),
            PlanInput(
                kind="guide_map",
                artifact_id=body.guide_map_id,
                approval_state="draft",
            ),
        ]
        if body.guide_ranking_id:
            ranking = workspace.load_guide_ranking(body.guide_ranking_id)
            if ranking.guide_map_id != body.guide_map_id:
                raise HTTPException(
                    status_code=422,
                    detail="Guide ranking is not bound to the selected guide map",
                )
            inputs.append(
                PlanInput(
                    kind="guide_ranking",
                    artifact_id=body.guide_ranking_id,
                    approval_state="draft",
                )
            )
        plan = build_simulation_plan(
            inputs=tuple(inputs),
            stages=body.stages,
            status="draft",
            limitations=body.limitations,
        )
        workspace.save_simulation_plan(plan)
    except DraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Simulation plan input not found") from exc
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=409,
            detail="Simulation plan input failed integrity checks",
        ) from exc
    return plan


@router.get("/{plan_id}", response_model=SimulationPlan)
def get_simulation_plan(
    plan_id: PlanId,
    workspace: LocalWorkspace = Depends(get_intake_workspace),
) -> SimulationPlan:
    try:
        return workspace.load_simulation_plan(plan_id)
    except DraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Simulation plan not found") from exc
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=409,
            detail="Simulation plan failed integrity checks",
        ) from exc
