from pydantic import BaseModel


class ProvenanceEvent(BaseModel):
    event_id: str
    run_id: str
    event_type: str
    message: str
    payload: dict | None = None
    occurred_at: str
    stage: str #which stage this event belongs to
    duration_ms: int | None = None 

class ProvenanceResponse(BaseModel):
    items: list[ProvenanceEvent]
