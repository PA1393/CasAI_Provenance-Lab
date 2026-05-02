from pydantic import BaseModel
from typing import Literal

class RunCreate(BaseModel):
    research_object_id: str
    prompt: str


class Run(BaseModel):
    run_id: str
    research_object_id: str
    created_at: str
    prompt: str
    status: Literal["queued", "running", "completed", "failed"]
    started_at: str | None
    completed_at: str | None
    guide_rna: str | None = None
    current_stage: str | None = None


class RunsResponse(BaseModel):
    items: list[Run]
