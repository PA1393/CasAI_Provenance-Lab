from pydantic import BaseModel


class ProvenanceEvent(BaseModel):
    event_id: str
    run_id: str
    event_type: str
    timestamp: str
    # Sequence number within the run's event log
    sequence: int


class ProvenanceResponse(BaseModel):
    items: list[ProvenanceEvent]
