"""Thin API boundary for persisted guide mapping from confirmed DNA records."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_intake_workspace
from app.modules.guide_mapping import GuideMappingRequest, map_guides, rank_guides
from app.modules.information_processor.workspace import (
    DraftNotFoundError,
    LocalWorkspace,
    WorkspaceError,
)
from app.schemas.guide_mapping import (
    GuideMapCreateBody,
    GuideMapCreateResponse,
    RankedGuideCandidateSummary,
)

router = APIRouter(prefix="/guide-maps", tags=["guide_mapping"])


def _response(guide_map, ranking) -> GuideMapCreateResponse:
    assessments = {
        assessment.candidate_id: assessment for assessment in ranking.assessments
    }
    ranked_candidates = sorted(
        guide_map.candidates,
        key=lambda candidate: assessments[candidate.candidate_id].rank,
    )
    return GuideMapCreateResponse(
        map_id=guide_map.map_id,
        ranking_id=ranking.ranking_id,
        status=guide_map.status,
        executable=guide_map.executable,
        source_version_id=guide_map.source_version_id,
        source_record_id=guide_map.source_record_id,
        target_sequence_checksum=guide_map.target_sequence_checksum,
        target_length=guide_map.target_length,
        editor=guide_map.editor,
        pam=guide_map.pam,
        guide_length=guide_map.guide_length,
        edit_window=guide_map.edit_window,
        desired_edits=guide_map.desired_edits,
        candidates=tuple(
            RankedGuideCandidateSummary(
                candidate_id=candidate.candidate_id,
                rank=assessments[candidate.candidate_id].rank,
                guide_rna=candidate.guide_rna,
                strand=candidate.strand,
                pam_pattern=candidate.pam_pattern,
                pam_sequence=candidate.pam_sequence,
                protospacer_start=candidate.protospacer_start,
                protospacer_end=candidate.protospacer_end,
                pam_start=candidate.pam_start,
                pam_end=candidate.pam_end,
                coordinate_system=candidate.coordinate_system,
                edit_window=candidate.edit_window,
                edit_sites=candidate.edit_sites,
                desired_edit_positions=candidate.desired_edit_positions,
                bystander_positions=candidate.bystander_positions,
                covers_all_desired_edits=candidate.covers_all_desired_edits,
                components=assessments[candidate.candidate_id].components,
            )
            for candidate in ranked_candidates
        ),
        issues=guide_map.issues,
        claim_type=guide_map.claim_type,
    )


@router.post("", response_model=GuideMapCreateResponse, status_code=201)
def create_guide_map(
    body: GuideMapCreateBody,
    workspace: LocalWorkspace = Depends(get_intake_workspace),
) -> GuideMapCreateResponse:
    try:
        version = workspace.load_confirmed_version(body.source_version_id)
    except DraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Confirmed research version not found") from exc
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=409, detail="Confirmed research version failed integrity checks"
        ) from exc

    matches = tuple(
        record
        for record in version.snapshot.records
        if record.record_id.value == body.source_record_id
    )
    if len(matches) != 1:
        raise HTTPException(
            status_code=422,
            detail="Source record is absent or ambiguous in the confirmed version",
        )
    record = matches[0]
    if record.molecule_type.value != "DNA":
        raise HTTPException(status_code=422, detail="Guide mapping requires confirmed DNA")

    sequence = record.sequence.value
    try:
        guide_map = map_guides(
            GuideMappingRequest(
                sequence=sequence,
                source_version_id=version.version_id,
                source_record_id=body.source_record_id,
                editor=body.editor,
                pam=body.pam,
                guide_length=body.guide_length,
                edit_window=body.edit_window,
                desired_edits=body.desired_edits,
            )
        )
        ranking = rank_guides(guide_map, sequence)
        workspace.save_guide_map(guide_map)
        workspace.save_guide_ranking(ranking)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WorkspaceError as exc:
        raise HTTPException(status_code=409, detail="Guide mapping could not be stored") from exc
    return _response(guide_map, ranking)
