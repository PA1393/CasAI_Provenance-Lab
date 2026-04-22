from pydantic import BaseModel


class RunCreate(BaseModel):
    research_object_id: str
    prompt: str


class Run(BaseModel):
    run_id: str
    research_object_id: str
    created_at: str
    prompt: str
    status: str
    started_at: str | None
    completed_at: str | None


class RunsResponse(BaseModel):
    items: list[Run]
