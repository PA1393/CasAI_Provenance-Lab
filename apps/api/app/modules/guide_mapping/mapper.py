"""Pure CBE/ABE PAM discovery with explicit strand and edit coordinates."""

from __future__ import annotations

from app.modules.guide_mapping.contracts import (
    CandidateEdit,
    GuideCandidate,
    GuideMap,
    GuideMappingRequest,
    MappingIssue,
    Strand,
    canonical_identity,
)
from app.modules.simulation.nucleotides import pam_matches, revcomp

_ACGT = frozenset("ACGT")
_EDITOR_CHANGES = {
    "CBE": {"+": ("C", "T"), "-": ("G", "A")},
    "ABE": {"+": ("A", "G"), "-": ("T", "C")},
}
_EDITOR_BASE = {"CBE": "C", "ABE": "A"}


def _forward_position(length: int, strand: Strand, strand_index: int) -> int:
    return strand_index + 1 if strand == "+" else length - strand_index


def _forward_interval(
    length: int,
    strand: Strand,
    start: int,
    stop: int,
) -> tuple[int, int]:
    positions = (
        _forward_position(length, strand, start),
        _forward_position(length, strand, stop - 1),
    )
    return min(positions), max(positions)


def _candidate(
    request: GuideMappingRequest,
    strand: Strand,
    strand_sequence: str,
    start: int,
) -> GuideCandidate | None:
    length = len(request.sequence)
    stop = start + request.guide_length
    guide = strand_sequence[start:stop]
    pam_sequence = strand_sequence[stop : stop + len(request.pam)]
    if set(guide) - _ACGT or not pam_matches(pam_sequence, request.pam):
        return None

    desired = {
        (edit.position, edit.reference, edit.alternate) for edit in request.desired_edits
    }
    reference, alternate = _EDITOR_CHANGES[request.editor][strand]
    editor_base = _EDITOR_BASE[request.editor]
    low, high = request.edit_window
    edit_sites = []
    for guide_position in range(low, high + 1):
        if guide[guide_position - 1] != editor_base:
            continue
        target_position = _forward_position(
            length,
            strand,
            start + guide_position - 1,
        )
        is_desired = (target_position, reference, alternate) in desired
        edit_sites.append(
            CandidateEdit(
                guide_position=guide_position,
                target_position=target_position,
                reference=reference,
                alternate=alternate,
                desired=is_desired,
            )
        )
    if not edit_sites:
        return None

    desired_positions = tuple(site.target_position for site in edit_sites if site.desired)
    bystander_positions = tuple(site.target_position for site in edit_sites if not site.desired)
    requested_positions = {edit.position for edit in request.desired_edits}
    protospacer_start, protospacer_end = _forward_interval(length, strand, start, stop)
    pam_start, pam_end = _forward_interval(length, strand, stop, stop + len(request.pam))
    values = {
        "guide_rna": guide,
        "strand": strand,
        "pam_pattern": request.pam,
        "pam_sequence": pam_sequence,
        "protospacer_start": protospacer_start,
        "protospacer_end": protospacer_end,
        "pam_start": pam_start,
        "pam_end": pam_end,
        "coordinate_system": "1-based-inclusive",
        "edit_window": request.edit_window,
        "edit_sites": tuple(edit_sites),
        "desired_edit_positions": desired_positions,
        "bystander_positions": bystander_positions,
        "covers_all_desired_edits": bool(requested_positions)
        and requested_positions == set(desired_positions),
        "claim_type": "heuristic",
    }
    serializable = {
        key: tuple(item.model_dump(mode="json", round_trip=True) for item in value)
        if key == "edit_sites"
        else value
        for key, value in values.items()
    }
    return GuideCandidate(candidate_id=canonical_identity(serializable), **values)


def _compatibility_issues(request: GuideMappingRequest) -> list[MappingIssue]:
    compatible_changes = set(_EDITOR_CHANGES[request.editor].values())
    return [
        MappingIssue(
            code="incompatible_desired_edit",
            message=(
                f"{request.editor} supports strand-aware changes "
                f"{sorted(compatible_changes)}, not {edit.reference}>{edit.alternate}"
            ),
            position=edit.position,
        )
        for edit in request.desired_edits
        if (edit.reference, edit.alternate) not in compatible_changes
    ]


def map_guides(request: GuideMappingRequest) -> GuideMap:
    """Enumerate every full-length, PAM-adjacent, editor-compatible guide candidate."""

    candidates = []
    sequence = request.sequence
    span = request.guide_length + len(request.pam)
    for strand, strand_sequence in (("+", sequence), ("-", revcomp(sequence))):
        for start in range(max(0, len(sequence) - span + 1)):
            candidate = _candidate(request, strand, strand_sequence, start)
            if candidate is not None:
                candidates.append(candidate)

    issues = _compatibility_issues(request)
    compatible_desired = {
        edit.position
        for edit in request.desired_edits
        if (edit.reference, edit.alternate) in set(_EDITOR_CHANGES[request.editor].values())
    }
    mapped_desired = {
        position for candidate in candidates for position in candidate.desired_edit_positions
    }
    issues.extend(
        MappingIssue(
            code="desired_edit_unmapped",
            message="No enumerated guide maps this desired edit inside its edit window",
            position=position,
        )
        for position in sorted(compatible_desired - mapped_desired)
    )
    if not candidates:
        issues.append(
            MappingIssue(
                code="no_compatible_guide",
                message=(
                    "No full-length guide has both a matching PAM and an editable base "
                    "inside the declared window"
                ),
            )
        )

    values = {
        "schema_version": "casai.guide-map.v1",
        "status": "draft",
        "executable": False,
        "source_record_id": request.source_record_id,
        "target_sequence_checksum": request.sequence_checksum,
        "target_length": len(sequence),
        "editor": request.editor,
        "pam": request.pam,
        "guide_length": request.guide_length,
        "edit_window": request.edit_window,
        "desired_edits": request.desired_edits,
        "candidates": tuple(candidates),
        "issues": tuple(issues),
        "claim_type": "heuristic",
    }
    serializable = {
        key: tuple(item.model_dump(mode="json", round_trip=True) for item in value)
        if key in {"desired_edits", "candidates", "issues"}
        else value
        for key, value in values.items()
    }
    return GuideMap(map_id=canonical_identity(serializable), **values)
