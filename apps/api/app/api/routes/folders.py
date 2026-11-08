"""Personal folders: DB row policies enforce ownership on every operation."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.db import get_supabase

router = APIRouter(prefix="/folders", tags=["folders"])


class FolderBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)


class PlacementBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["input", "run"]
    record_id: UUID
    folder_id: UUID | None = None


@router.get("")
def list_folders():
    return {"items": get_supabase().table("research_folders").select("*")
            .order("created_at").execute().data}


@router.post("", status_code=201)
def create_folder(body: FolderBody):
    return get_supabase().table("research_folders").insert({"name": body.name}).execute().data[0]


@router.post("/place")
def place_record(body: PlacementBody):
    client = get_supabase()
    if body.folder_id is not None:
        folders = (client.table("research_folders").select("folder_id")
                   .eq("folder_id", str(body.folder_id)).execute().data)
        if not folders:
            raise HTTPException(404, "Folder not found")
    table, column = ("research_objects", "research_object_id") if body.kind == "input" else (
        "runs", "run_id",
    )
    rows = (client.table(table).update({
        "folder_id": str(body.folder_id) if body.folder_id else None,
    }).eq(column, str(body.record_id)).execute().data)
    if not rows:
        raise HTTPException(404, "Record not found")
    return {"placed": True}
