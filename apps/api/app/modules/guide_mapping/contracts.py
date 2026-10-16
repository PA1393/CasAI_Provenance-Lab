"""Typed contracts for transparent CBE/ABE guide and target mapping."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, computed_field, model_validator

from app.modules.information_processor.contracts import Contract, checksum
from app.modules.simulation.nucleotides import IUPAC, pam_matches

EditorType = Literal["CBE", "ABE"]
Strand = Literal["+", "-"]


class DesiredEdit(Contract):
    position: int = Field(gt=0, strict=True)
    reference: Literal["A", "C", "G", "T"]
    alternate: Literal["A", "C", "G", "T"]

    @model_validator(mode="after")
    def validate_substitution(self) -> DesiredEdit:
        if self.reference == self.alternate:
            raise ValueError("Desired edit must change the reference base")
        return self


class GuideMappingRequest(Contract):
    sequence: str = Field(min_length=1)
    source_version_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_record_id: str = Field(min_length=1)
    editor: EditorType
    pam: str = Field(default="NGG", min_length=1, max_length=12)
    guide_length: int = Field(default=20, ge=15, le=30, strict=True)
    edit_window: tuple[int, int] = (4, 8)
    desired_edits: tuple[DesiredEdit, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> GuideMappingRequest:
        if self.sequence != self.sequence.upper() or set(self.sequence) - set(IUPAC):
            raise ValueError("Target sequence must be uppercase DNA/IUPAC")
        pam = self.pam.upper()
        if self.pam != pam or set(pam) - set(IUPAC):
            raise ValueError("PAM must use uppercase DNA/IUPAC symbols")
        low, high = self.edit_window
        if not 1 <= low <= high <= self.guide_length:
            raise ValueError("Edit window must use 1-based positions within the guide")
        positions = tuple(edit.position for edit in self.desired_edits)
        if len(set(positions)) != len(positions):
            raise ValueError("Desired edit positions must be unique")
        for edit in self.desired_edits:
            if edit.position > len(self.sequence):
                raise ValueError("Desired edit position exceeds the target sequence")
            if self.sequence[edit.position - 1] != edit.reference:
                raise ValueError("Desired edit reference must match the target sequence")
        return self

    @computed_field
    @property
    def sequence_checksum(self) -> str:
        return checksum(self.sequence.encode("ascii"))


class MappingIssue(Contract):
    code: str
    message: str
    position: int | None = Field(default=None, gt=0, strict=True)


class CandidateEdit(Contract):
    guide_position: int = Field(gt=0, strict=True)
    target_position: int = Field(gt=0, strict=True)
    reference: Literal["A", "C", "G", "T"]
    alternate: Literal["A", "C", "G", "T"]
    desired: bool = Field(strict=True)


class GuideCandidate(Contract):
    candidate_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    guide_rna: str
    strand: Strand
    pam_pattern: str
    pam_sequence: str
    protospacer_start: int = Field(gt=0, strict=True)
    protospacer_end: int = Field(gt=0, strict=True)
    pam_start: int = Field(gt=0, strict=True)
    pam_end: int = Field(gt=0, strict=True)
    coordinate_system: Literal["1-based-inclusive"] = "1-based-inclusive"
    edit_window: tuple[int, int]
    edit_sites: tuple[CandidateEdit, ...]
    desired_edit_positions: tuple[int, ...] = ()
    bystander_positions: tuple[int, ...] = ()
    covers_all_desired_edits: bool = Field(strict=True)
    claim_type: Literal["heuristic"] = "heuristic"

    @model_validator(mode="after")
    def validate_candidate(self) -> GuideCandidate:
        if self.protospacer_start > self.protospacer_end or self.pam_start > self.pam_end:
            raise ValueError("Mapped coordinate intervals must be ascending")
        guide_length = self.protospacer_end - self.protospacer_start + 1
        if len(self.guide_rna) != guide_length or set(self.guide_rna) - set("ACGT"):
            raise ValueError("Guide sequence must match its unambiguous mapped interval")
        if (
            len(self.pam_sequence) != self.pam_end - self.pam_start + 1
            or not pam_matches(self.pam_sequence, self.pam_pattern)
        ):
            raise ValueError("PAM sequence must match its pattern and mapped interval")
        adjacent = (
            self.pam_start == self.protospacer_end + 1
            if self.strand == "+"
            else self.pam_end + 1 == self.protospacer_start
        )
        if not adjacent:
            raise ValueError("PAM must be immediately 3-prime of the oriented protospacer")
        if not self.edit_sites:
            raise ValueError("A compatible guide requires an editable base in its window")
        low, high = self.edit_window
        for site in self.edit_sites:
            if not low <= site.guide_position <= high:
                raise ValueError("Candidate edit lies outside the declared edit window")
            expected_position = (
                self.protospacer_start + site.guide_position - 1
                if self.strand == "+"
                else self.protospacer_end - site.guide_position + 1
            )
            if site.target_position != expected_position:
                raise ValueError("Candidate edit coordinate does not match guide orientation")
        positions = tuple(site.target_position for site in self.edit_sites)
        desired = tuple(site.target_position for site in self.edit_sites if site.desired)
        bystanders = tuple(site.target_position for site in self.edit_sites if not site.desired)
        if self.desired_edit_positions != desired or self.bystander_positions != bystanders:
            raise ValueError("Desired and bystander positions must derive from edit sites")
        if len(set(positions)) != len(positions):
            raise ValueError("Candidate edit positions must be unique")
        identity = self.model_dump(round_trip=True, exclude={"candidate_id"})
        if self.candidate_id != canonical_identity(identity):
            raise ValueError("Candidate identity must match canonical mapping content")
        return self


def canonical_identity(values: dict[str, object]) -> str:
    return checksum(
        json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )


class GuideMap(Contract):
    schema_version: Literal["casai.guide-map.v1"] = "casai.guide-map.v1"
    map_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: Literal["draft"] = "draft"
    executable: Literal[False] = False
    source_version_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_record_id: str
    target_sequence_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_length: int = Field(gt=0, strict=True)
    editor: EditorType
    pam: str
    guide_length: int = Field(gt=0, strict=True)
    edit_window: tuple[int, int]
    desired_edits: tuple[DesiredEdit, ...]
    candidates: tuple[GuideCandidate, ...]
    issues: tuple[MappingIssue, ...] = ()
    claim_type: Literal["heuristic"] = "heuristic"

    @model_validator(mode="after")
    def validate_identity(self) -> GuideMap:
        candidate_ids = tuple(candidate.candidate_id for candidate in self.candidates)
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("Guide candidates must have unique identities")
        desired_positions = {edit.position for edit in self.desired_edits}
        for candidate in self.candidates:
            if (
                candidate.pam_pattern != self.pam
                or len(candidate.guide_rna) != self.guide_length
                or candidate.edit_window != self.edit_window
            ):
                raise ValueError("Guide candidate parameters must match their map")
            if not (
                1 <= candidate.protospacer_start <= candidate.protospacer_end <= self.target_length
                and 1 <= candidate.pam_start <= candidate.pam_end <= self.target_length
            ):
                raise ValueError("Guide candidate coordinates exceed the target sequence")
            mapped_desired = set(candidate.desired_edit_positions)
            if not mapped_desired <= desired_positions:
                raise ValueError("Candidate desired edits must come from the mapping request")
            expected_coverage = bool(desired_positions) and mapped_desired == desired_positions
            if candidate.covers_all_desired_edits != expected_coverage:
                raise ValueError("Candidate desired-edit coverage is inconsistent")
        identity = self.model_dump(round_trip=True, exclude={"map_id"})
        if self.map_id != canonical_identity(identity):
            raise ValueError("Guide map identity must match canonical mapping content")
        return self


ScoreName = Literal[
    "desired_coverage",
    "bystander_avoidance",
    "window_centrality",
    "guide_composition",
    "local_specificity",
]


class ScoreComponent(Contract):
    name: ScoreName
    value: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1)
    limitation: str = Field(min_length=1)
    claim_type: Literal["heuristic"] = "heuristic"


class CandidateAssessment(Contract):
    candidate_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    rank: int = Field(gt=0, strict=True)
    components: tuple[ScoreComponent, ...]
    ranking_basis: tuple[ScoreName, ...] = (
        "desired_coverage",
        "bystander_avoidance",
        "window_centrality",
        "local_specificity",
        "guide_composition",
    )

    @model_validator(mode="after")
    def validate_components(self) -> CandidateAssessment:
        names = tuple(component.name for component in self.components)
        if len(set(names)) != len(names) or set(names) != set(ScoreName.__args__):
            raise ValueError("Assessment must contain every score component exactly once")
        if names != self.ranking_basis:
            raise ValueError("Score components must follow the declared ranking basis")
        return self


class GuideRanking(Contract):
    schema_version: Literal["casai.guide-ranking.v1"] = "casai.guide-ranking.v1"
    ranking_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    guide_map_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_sequence_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    method_version: Literal["casai.guide-ranking.heuristic.v1"] = (
        "casai.guide-ranking.heuristic.v1"
    )
    mapped_candidate_ids: tuple[str, ...]
    assessments: tuple[CandidateAssessment, ...]
    aggregate_score: Literal[None] = None
    claim_type: Literal["heuristic"] = "heuristic"

    @model_validator(mode="after")
    def validate_ranking(self) -> GuideRanking:
        assessed = tuple(assessment.candidate_id for assessment in self.assessments)
        if len(set(self.mapped_candidate_ids)) != len(self.mapped_candidate_ids):
            raise ValueError("Mapped candidate identities must be unique")
        if set(assessed) != set(self.mapped_candidate_ids) or len(assessed) != len(
            self.mapped_candidate_ids
        ):
            raise ValueError("Ranking must assess every mapped candidate exactly once")
        if tuple(assessment.rank for assessment in self.assessments) != tuple(
            range(1, len(self.assessments) + 1)
        ):
            raise ValueError("Assessment ranks must be contiguous and ordered")
        identity = self.model_dump(round_trip=True, exclude={"ranking_id"})
        if self.ranking_id != canonical_identity(identity):
            raise ValueError("Guide ranking identity must match canonical scoring content")
        return self
