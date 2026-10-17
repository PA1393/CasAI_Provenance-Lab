"""Content-addressed simulation-plan contracts and approval gates."""

import pytest
from pydantic import ValidationError

from app.modules.simulation import (
    PlanInput,
    SimulationPlan,
    SimulationStage,
    StageSetting,
    build_simulation_plan,
)
from app.modules.simulation.planning import canonical_identity

RESEARCH_ID = "sha256:" + "1" * 64
GUIDE_ID = "sha256:" + "2" * 64
ENZYME_ID = "sha256:" + "3" * 64


def _inputs(*, guide_state="approved"):
    return (
        PlanInput(
            kind="confirmed_research_version",
            artifact_id=RESEARCH_ID,
            approval_state="confirmed",
        ),
        PlanInput(kind="guide_map", artifact_id=GUIDE_ID, approval_state=guide_state),
        PlanInput(kind="enzyme_map", artifact_id=ENZYME_ID, approval_state="approved"),
    )


def _stages():
    return (
        SimulationStage(
            stage_id="sequence_edit",
            engine="casai.sequence-edit",
            engine_version="1",
            operation="apply_base_edit",
            requirement="required",
            settings=(
                StageSetting(name="editor", value="CBE"),
                StageSetting(name="window_start", value=4),
                StageSetting(name="window_end", value=8),
            ),
        ),
        SimulationStage(
            stage_id="score",
            engine="casai.guide-score",
            engine_version="1",
            operation="score_guide",
            requirement="optional",
            depends_on=("sequence_edit",),
        ),
    )


def test_draft_plan_is_deterministic_and_not_executable():
    first = build_simulation_plan(inputs=_inputs(), stages=_stages())
    second = build_simulation_plan(inputs=_inputs(), stages=_stages())

    assert first == second
    assert first.plan_id == second.plan_id
    assert first.status == "draft"
    assert first.executable is False


def test_approved_plan_with_ready_inputs_is_executable_and_has_new_identity():
    draft = build_simulation_plan(inputs=_inputs(), stages=_stages())
    approved = build_simulation_plan(inputs=_inputs(), stages=_stages(), status="approved")

    assert approved.executable is True
    assert approved.plan_id != draft.plan_id


def test_approval_rejects_unapproved_inputs():
    with pytest.raises(ValidationError, match="unconfirmed or rejected"):
        build_simulation_plan(
            inputs=_inputs(guide_state="draft"),
            stages=_stages(),
            status="approved",
        )


def test_plan_requires_confirmed_research_and_guide_inputs():
    with pytest.raises(ValidationError, match="confirmed research and guide"):
        build_simulation_plan(inputs=(_inputs()[0],), stages=_stages())


def test_plan_rejects_duplicate_inputs_and_stages():
    duplicate_input = _inputs() + (_inputs()[1],)
    with pytest.raises(ValidationError, match="inputs must be unique"):
        build_simulation_plan(inputs=duplicate_input, stages=_stages())

    duplicate_stage = _stages() + (_stages()[0],)
    with pytest.raises(ValidationError, match="identifiers must be unique"):
        build_simulation_plan(inputs=_inputs(), stages=duplicate_stage)


def test_stage_dependencies_must_be_unique_earlier_and_not_self_referential():
    with pytest.raises(ValidationError, match="earlier plan stages"):
        build_simulation_plan(
            inputs=_inputs(),
            stages=(
                SimulationStage(
                    stage_id="score",
                    engine="casai.guide-score",
                    engine_version="1",
                    operation="score_guide",
                    requirement="required",
                    depends_on=("sequence_edit",),
                ),
            ),
        )
    with pytest.raises(ValidationError, match="depend on itself"):
        SimulationStage(
            stage_id="score",
            engine="casai.guide-score",
            engine_version="1",
            operation="score_guide",
            requirement="required",
            depends_on=("score",),
        )


def test_stage_settings_are_typed_and_unique():
    with pytest.raises(ValidationError, match="setting names must be unique"):
        SimulationStage(
            stage_id="score",
            engine="casai.guide-score",
            engine_version="1",
            operation="score_guide",
            requirement="required",
            settings=(
                StageSetting(name="threshold", value=0.5),
                StageSetting(name="threshold", value=0.8),
            ),
        )


def test_input_states_follow_artifact_semantics():
    with pytest.raises(ValidationError, match="research version"):
        PlanInput(
            kind="confirmed_research_version",
            artifact_id=RESEARCH_ID,
            approval_state="approved",
        )
    with pytest.raises(ValidationError, match="Only a research version"):
        PlanInput(kind="guide_map", artifact_id=GUIDE_ID, approval_state="confirmed")


def test_plan_rejects_forged_identity_and_executable_flag():
    plan = build_simulation_plan(inputs=_inputs(), stages=_stages())
    values = plan.model_dump(round_trip=True)
    values["plan_id"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="canonical planning"):
        SimulationPlan.model_validate(values)

    values = plan.model_dump(round_trip=True)
    values["executable"] = True
    identity = values.copy()
    identity.pop("plan_id")
    values["plan_id"] = canonical_identity(identity)
    with pytest.raises(ValidationError, match="executability"):
        SimulationPlan.model_validate(values)
