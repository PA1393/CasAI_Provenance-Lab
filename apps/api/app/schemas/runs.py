from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    research_object_id: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1, max_length=2000)
    execution_mode: Literal["assisted", "demo_cbe", "demo_abe"] = "assisted"


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
