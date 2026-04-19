# Handles GET /api/v1/runs/{run_id}/provenance — returns the event history for a specific run. Data is fake/mock for now.
# Data shape is in schemas/provenance.py; the data itself comes from modules/provenance/service.py.

from fastapi import APIRouter

from app.modules.provenance.service import list_provenance_events
from app.schemas.provenance import ProvenanceEvent, ProvenanceResponse

router = APIRouter(tags=["provenance"])


@router.get("/runs/{run_id}/provenance", response_model=ProvenanceResponse)
def get_provenance(run_id: str) -> ProvenanceResponse:
    return ProvenanceResponse(
        items=[ProvenanceEvent(**event) for event in list_provenance_events(run_id)]
    )

