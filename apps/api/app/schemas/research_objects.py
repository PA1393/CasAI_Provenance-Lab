from pydantic import BaseModel


class ResearchObjectCreate(BaseModel):
    name: str
    input_filename: str
    input_file_type: str
    pdb_id: str
    target_region: list[int] | None = None


class ResearchObject(BaseModel):
    research_object_id: str
    created_at: str
    name: str
    input_filename: str
    input_file_type: str
    pdb_id: str
    mmcif_fetched_from: str | None = None
    mmcif_hash: str | None = None
    sequence_length: int | None = None
    gc_content: float | None = None
    avg_phred_score: float | None = None
    reads_passing_qc: int | None = None
    reads_total: int | None = None
    ro_hash: str
    status: str
    fasta_preview: str | None = None
    target_region: list[int] | None = None


class ResearchObjectsResponse(BaseModel):
    items: list[ResearchObject]
