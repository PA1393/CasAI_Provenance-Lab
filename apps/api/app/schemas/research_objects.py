from pydantic import BaseModel


class ResearchObjectCreate(BaseModel):
    name: str
    input_filename: str
    input_file_type: str
    pdb_id: str
    target_region: list[int] | None = None
    # Raw FASTA upload text. Input-only — the service consumes it and stores the
    # sequence and the fields derived from it. Omit it and the research object is
    # created without a sequence, which the pipeline reports as an input failure.
    fasta_text: str | None = None


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
    # Full parsed sequence the base-edit pipeline runs against. Null for research
    # objects created without a FASTA upload.
    sequence: str | None = None


class ResearchObjectsResponse(BaseModel):
    items: list[ResearchObject]
