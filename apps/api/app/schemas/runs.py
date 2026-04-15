# Defines what a "run" looks like when the API sends it back — the fields and their types.
# These field names are a starting point and will likely change as the run workflow gets built out.

from pydantic import BaseModel


class RunSummary(BaseModel):
    run_id: str
    research_object_id: str
    status: str
    mode: str


class RunsResponse(BaseModel):
    items: list[RunSummary]
