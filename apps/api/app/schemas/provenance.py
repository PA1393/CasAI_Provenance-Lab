# Defines what a single provenance event looks like when the API sends it back — the fields and their types.
# The list of possible event types isn't decided yet; this is just a starting point.

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
