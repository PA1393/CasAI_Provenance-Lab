from typing import Literal

from pydantic import BaseModel, computed_field

StageStatus = Literal["pending", "running", "completed", "failed", "unknown"]

# Explicit API vocabulary; event names are not status suffix conventions.
EVENT_STAGE_STATUS: dict[str, StageStatus] = {
    "input_received": "pending",
    "input_validated": "completed",
    "input_invalid": "failed",
    "intent_resolved": "running",
    "analysis_failed": "failed",
    "schema_invalid": "failed",
    "schema_validated": "completed",
    "simulation_executed": "completed",
    "edit_scored": "completed",
    "results_packaged": "completed",
    "scientific_tool_failed": "failed",
    "scientific_tool_completed": "completed",
}


class ProvenanceEvent(BaseModel):
    event_id: str
    run_id: str
    event_type: str
    message: str
    payload: dict | None = None
    occurred_at: str
    stage: str
    duration_ms: int | None = None

    @computed_field
    @property
    def stage_status(self) -> StageStatus:
        return EVENT_STAGE_STATUS.get(self.event_type, "unknown")


class ProvenanceResponse(BaseModel):
    items: list[ProvenanceEvent]
