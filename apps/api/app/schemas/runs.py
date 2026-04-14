from pydantic import BaseModel


class RunSummary(BaseModel):
    run_id: str
    research_object_id: str
    status: str
    mode: str


class RunsResponse(BaseModel):
    items: list[RunSummary]
