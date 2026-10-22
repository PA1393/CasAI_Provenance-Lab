"""Public guide-map API contracts; full confirmed target sequences remain internal."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.modules.guide_mapping.contracts import (
    CandidateEdit,
    DesiredEdit,
    EditorType,
    MappingIssue,
    ScoreComponent,
    Strand,
)
from app.modules.information_processor.contracts import Contract


class GuideMapCreateBody(Contract):
    source_version_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_record_id: str = Field(min_length=1)
    editor: EditorType
    pam: str = Field(default="NGG", min_length=1, max_length=12)
    guide_length: int = Field(default=20, ge=15, le=30, strict=True)
    edit_window: tuple[int, int] = (4, 8)
    desired_edits: tuple[DesiredEdit, ...] = ()


class RankedGuideCandidateSummary(Contract):
    candidate_id: str
    rank: int = Field(gt=0, strict=True)
    guide_rna: str
    strand: Strand
    pam_pattern: str
    pam_sequence: str
    protospacer_start: int
    protospacer_end: int
    pam_start: int
    pam_end: int
    coordinate_system: Literal["1-based-inclusive"]
    edit_window: tuple[int, int]
    edit_sites: tuple[CandidateEdit, ...]
    desired_edit_positions: tuple[int, ...]
    bystander_positions: tuple[int, ...]
    covers_all_desired_edits: bool
    components: tuple[ScoreComponent, ...]


class GuideMapCreateResponse(Contract):
    map_id: str
    ranking_id: str
    status: Literal["draft"]
    executable: Literal[False]
    source_version_id: str
    source_record_id: str
    target_sequence_checksum: str
    target_length: int
    editor: EditorType
    pam: str
    guide_length: int
    edit_window: tuple[int, int]
    desired_edits: tuple[DesiredEdit, ...]
    candidates: tuple[RankedGuideCandidateSummary, ...]
    issues: tuple[MappingIssue, ...]
    claim_type: Literal["heuristic"]
