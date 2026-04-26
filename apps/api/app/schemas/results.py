from pydantic import BaseModel


class Result(BaseModel):
    result_id: str
    run_id: str
    research_object_id: str | None = None
    edited_sequence: str | None = None
    edit_summary: str | None = None
    off_target_score: float | None = None
    confidence: float | None = None
    notes: str | None = None


class ResultsResponse(BaseModel):
    items: list[Result]
