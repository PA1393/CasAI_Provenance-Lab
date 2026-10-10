from pydantic import BaseModel, Field

from app.schemas.contracts import CONTRACT_SCHEMA_VERSION, RunStage, RunStatus


class RunCreate(BaseModel):
    research_object_id: str
    prompt: str


class Run(BaseModel):
    schema_version: int = Field(default=CONTRACT_SCHEMA_VERSION, ge=1)
    run_version: int = Field(default=1, ge=1)
    plan_version: int = Field(default=1, ge=1)
    run_id: str
    research_object_id: str
    created_at: str
    prompt: str
    status: RunStatus
    started_at: str | None
    completed_at: str | None
    guide_rna: str | None = None
    current_stage: RunStage | None = None
    engine_version_id: str | None = None


class RunsResponse(BaseModel):
    items: list[Run]
