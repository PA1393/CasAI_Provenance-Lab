from pydantic import BaseModel, Field

from app.schemas.contracts import CONTRACT_SCHEMA_VERSION, ActorType, ProvenanceStage


class ProvenanceEvent(BaseModel):
    schema_version: int = Field(default=CONTRACT_SCHEMA_VERSION, ge=1)
    event_id: str
    run_id: str
    event_type: str
    message: str
    payload: dict | None = None
    occurred_at: str
    stage: ProvenanceStage
    duration_ms: int | None = None
    actor_type: ActorType = ActorType.SYSTEM
    actor_ref: str | None = None


class ProvenanceResponse(BaseModel):
    items: list[ProvenanceEvent]
