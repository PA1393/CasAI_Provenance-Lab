"""Transparent guide/target mapping across strands and edit constraints."""

import pytest
from pydantic import ValidationError

from app.modules.guide_mapping import GuideMappingRequest, map_guides
from app.modules.guide_mapping.contracts import (
    DesiredEdit,
    GuideCandidate,
    GuideMap,
    canonical_identity,
)
from app.modules.simulation.nucleotides import revcomp

GUIDE_C = "AAACACAAAAAAAAAAAAAA"
GUIDE_A = "GGGAGGGGGGGGGGGGGGGG"
SOURCE_VERSION = "sha256:" + "1" * 64


def _target(guide, pam="AGG"):
    return "TTTT" + guide + pam + "TTTT"


def test_cbe_maps_forward_coordinates_desired_edit_and_bystander():
    request = GuideMappingRequest(
        sequence=_target(GUIDE_C),
        source_version_id=SOURCE_VERSION,
        source_record_id="target-1",
        editor="CBE",
        desired_edits=(DesiredEdit(position=8, reference="C", alternate="T"),),
    )
    result = map_guides(request)

    candidate = next(item for item in result.candidates if item.guide_rna == GUIDE_C)
    assert (candidate.protospacer_start, candidate.protospacer_end) == (5, 24)
    assert (candidate.pam_start, candidate.pam_end) == (25, 27)
    assert candidate.desired_edit_positions == (8,)
    assert candidate.bystander_positions == (10,)
    assert candidate.covers_all_desired_edits is True
    changes = [
        (site.guide_position, site.reference, site.alternate)
        for site in candidate.edit_sites
    ]
    assert changes == [
        (4, "C", "T"),
        (6, "C", "T"),
    ]


def test_cbe_maps_reverse_strand_to_forward_coordinates_and_changes():
    sequence = revcomp(_target(GUIDE_C))
    request = GuideMappingRequest(
        sequence=sequence,
        source_version_id=SOURCE_VERSION,
        source_record_id="target-reverse",
        editor="CBE",
        desired_edits=(DesiredEdit(position=24, reference="G", alternate="A"),),
    )
    result = map_guides(request)

    candidate = next(item for item in result.candidates if item.strand == "-")
    assert (candidate.protospacer_start, candidate.protospacer_end) == (8, 27)
    assert (candidate.pam_start, candidate.pam_end) == (5, 7)
    assert candidate.desired_edit_positions == (24,)
    assert candidate.bystander_positions == (22,)
    assert candidate.edit_sites[0].reference == "G"
    assert candidate.edit_sites[0].alternate == "A"


def test_abe_maps_expected_change_and_window():
    result = map_guides(
        GuideMappingRequest(
            sequence=_target(GUIDE_A, pam="TGG"),
            source_version_id=SOURCE_VERSION,
            source_record_id="abe-target",
            editor="ABE",
            desired_edits=(DesiredEdit(position=8, reference="A", alternate="G"),),
        )
    )
    candidate = next(item for item in result.candidates if item.guide_rna == GUIDE_A)
    assert candidate.desired_edit_positions == (8,)
    assert candidate.edit_sites[0].guide_position == 4


def test_incompatible_desired_edit_is_explicit_and_not_claimed_as_covered():
    result = map_guides(
        GuideMappingRequest(
            sequence=_target(GUIDE_C),
            source_version_id=SOURCE_VERSION,
            source_record_id="target-1",
            editor="CBE",
            desired_edits=(DesiredEdit(position=8, reference="C", alternate="G"),),
        )
    )
    assert "incompatible_desired_edit" in {issue.code for issue in result.issues}
    assert not any(candidate.covers_all_desired_edits for candidate in result.candidates)


def test_desired_edit_outside_all_windows_is_reported():
    sequence = "C" + _target(GUIDE_C)
    result = map_guides(
        GuideMappingRequest(
            sequence=sequence,
            source_version_id=SOURCE_VERSION,
            source_record_id="boundary-target",
            editor="CBE",
            desired_edits=(DesiredEdit(position=1, reference="C", alternate="T"),),
        )
    )
    issue = next(item for item in result.issues if item.code == "desired_edit_unmapped")
    assert issue.position == 1


def test_no_pam_or_no_editable_base_returns_non_executable_map_with_issue():
    no_pam = map_guides(
        GuideMappingRequest(
            sequence="A" * 60,
            source_version_id=SOURCE_VERSION,
            source_record_id="no-pam",
            editor="CBE",
        )
    )
    no_editable = map_guides(
        GuideMappingRequest(
            sequence="GGGCCC" * 10,
            source_version_id=SOURCE_VERSION,
            source_record_id="no-abe",
            editor="ABE",
        )
    )

    for result in (no_pam, no_editable):
        assert result.candidates == ()
        assert result.executable is False
        assert "no_compatible_guide" in {issue.code for issue in result.issues}


def test_ambiguous_bases_are_retained_but_not_used_in_candidate_guide():
    sequence = "TTTT" + "AAACANAAAAAAAAAAAAAA" + "AGG" + _target(GUIDE_C)
    result = map_guides(
        GuideMappingRequest(
            sequence=sequence,
            source_version_id=SOURCE_VERSION,
            source_record_id="ambiguous-target",
            editor="CBE",
        )
    )
    assert result.candidates
    assert all(set(candidate.guide_rna) <= set("ACGT") for candidate in result.candidates)
    assert all("N" not in candidate.guide_rna for candidate in result.candidates)


def test_mapping_enumerates_multiple_sites_in_deterministic_strand_order():
    sequence = _target(GUIDE_C) + "AAAA" + _target(GUIDE_C)
    request = GuideMappingRequest(
        sequence=sequence,
        source_version_id=SOURCE_VERSION,
        source_record_id="multi-target",
        editor="CBE",
    )
    first = map_guides(request)
    second = map_guides(request)

    assert first == second
    assert first.map_id == second.map_id
    assert len([candidate for candidate in first.candidates if candidate.strand == "+"]) == 2
    forward_starts = [
        candidate.protospacer_start
        for candidate in first.candidates
        if candidate.strand == "+"
    ]
    assert forward_starts == [
        5,
        40,
    ]


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"sequence": "acgt"}, "uppercase"),
        ({"sequence": "ACGU"}, "DNA/IUPAC"),
        ({"pam": "ngg"}, "uppercase"),
        ({"edit_window": (0, 8)}, "1-based"),
        ({"edit_window": (4, 21)}, "1-based"),
    ],
)
def test_request_rejects_invalid_sequence_pam_and_window(changes, message):
    values = {
        "sequence": _target(GUIDE_C),
        "source_version_id": SOURCE_VERSION,
        "source_record_id": "target",
        "editor": "CBE",
    }
    values.update(changes)
    with pytest.raises(ValidationError, match=message):
        GuideMappingRequest(**values)


def test_request_rejects_reference_mismatch_duplicate_or_out_of_bounds_desired_edits():
    sequence = _target(GUIDE_C)
    with pytest.raises(ValidationError, match="reference"):
        GuideMappingRequest(
            sequence=sequence,
            source_version_id=SOURCE_VERSION,
            source_record_id="target",
            editor="CBE",
            desired_edits=(DesiredEdit(position=1, reference="A", alternate="G"),),
        )
    duplicate = DesiredEdit(position=8, reference="C", alternate="T")
    with pytest.raises(ValidationError, match="unique"):
        GuideMappingRequest(
            sequence=sequence,
            source_version_id=SOURCE_VERSION,
            source_record_id="target",
            editor="CBE",
            desired_edits=(duplicate, duplicate),
        )
    with pytest.raises(ValidationError, match="exceeds"):
        GuideMappingRequest(
            sequence=sequence,
            source_version_id=SOURCE_VERSION,
            source_record_id="target",
            editor="CBE",
            desired_edits=(
                DesiredEdit(position=len(sequence) + 1, reference="A", alternate="G"),
            ),
        )


def test_map_and_candidate_identity_reject_forgery():
    result = map_guides(
        GuideMappingRequest(
            sequence=_target(GUIDE_C),
            source_version_id=SOURCE_VERSION,
            source_record_id="target",
            editor="CBE",
        )
    )
    values = result.model_dump(round_trip=True)
    values["map_id"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="canonical mapping"):
        GuideMap.model_validate(values)

    candidate_values = result.candidates[0].model_dump(round_trip=True)
    candidate_values["guide_rna"] = "N" * len(candidate_values["guide_rna"])
    with pytest.raises(ValidationError, match="unambiguous"):
        GuideCandidate.model_validate(candidate_values)

    map_values = result.model_dump(round_trip=True)
    map_values["candidates"][0]["covers_all_desired_edits"] = True
    candidate_identity = map_values["candidates"][0].copy()
    candidate_identity.pop("candidate_id")
    map_values["candidates"][0]["candidate_id"] = canonical_identity(candidate_identity)
    map_identity = map_values.copy()
    map_identity.pop("map_id")
    map_values["map_id"] = canonical_identity(map_identity)
    with pytest.raises(ValidationError, match="coverage"):
        GuideMap.model_validate(map_values)
