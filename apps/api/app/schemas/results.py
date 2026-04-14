from pydantic import BaseModel


class Result(BaseModel):
    result_id: str
    run_id: str
    summary: str
    status: str


class ResultsResponse(BaseModel):
    items: list[Result]
