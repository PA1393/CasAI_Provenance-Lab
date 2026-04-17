# Defines what a "result" looks like when the API sends it back — the fields and their types.
# The summary field is a temporary placeholder; the real shape depends on what the simulation actually outputs.

from pydantic import BaseModel


class Result(BaseModel):
    result_id: str
    run_id: str
    summary: str
    status: str


class ResultsResponse(BaseModel):
    items: list[Result]
