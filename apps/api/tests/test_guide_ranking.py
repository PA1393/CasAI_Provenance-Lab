"""Component-wise guide ranking remains deterministic and scientifically bounded."""

import pytest
from pydantic import ValidationError

from app.modules.guide_mapping import GuideMappingRequest, map_guides, rank_guides
from app.modules.guide_mapping.contracts import DesiredEdit, GuideRanking

GUIDE_ONE = "AAACAAAAAAAAAAAAAAAA"
GUIDE_TWO = "AAACACAAAAAAAAAAAAAA"


def _target(guide):
    return "TTTT" + guide + "AGG" + "TTTT"


def _component(assessment, name):
    return next(component for component in assessment.components if component.name == name)


def test_ranking_prioritizes_desired_coverage_before_other_heuristics():
    sequence = _target(GUIDE_ONE) + "AAAA" + _target(GUIDE_TWO)
    request = GuideMappingRequest(
        sequence=sequence,
        source_record_id="rank-target",
        editor="CBE",
        desired_edits=(DesiredEdit(position=8, reference="C", alternate="T"),),
    )
    guide_map = map_guides(request)
    ranking = rank_guides(guide_map, sequence)

    first = ranking.assessments[0]
    candidate = next(
        item for item in guide_map.candidates if item.candidate_id == first.candidate_id
    )
    assert candidate.covers_all_desired_edits is True
    assert _component(first, "desired_coverage").value == 1.0


def test_ranking_keeps_components_separate_and_has_no_aggregate_score():
    sequence = _target(GUIDE_TWO)
    guide_map = map_guides(
        GuideMappingRequest(
            sequence=sequence,
            source_record_id="transparent-target",
            editor="CBE",
            desired_edits=(DesiredEdit(position=8, reference="C", alternate="T"),),
        )
    )
    ranking = rank_guides(guide_map, sequence)
    assessment = ranking.assessments[0]

    assert ranking.aggregate_score is None
    assert {component.name for component in assessment.components} == {
        "desired_coverage",
        "bystander_avoidance",
        "window_centrality",
        "guide_composition",
        "local_specificity",
    }
    assert _component(assessment, "bystander_avoidance").value == 0.5
    assert "not a genome-wide" in _component(assessment, "local_specificity").limitation
    assert all(component.claim_type == "heuristic" for component in assessment.components)


def test_ranking_is_deterministic_and_assesses_every_candidate_once():
    sequence = _target(GUIDE_ONE) + "AAAA" + _target(GUIDE_TWO)
    guide_map = map_guides(
        GuideMappingRequest(
            sequence=sequence,
            source_record_id="deterministic-target",
            editor="CBE",
        )
    )
    first = rank_guides(guide_map, sequence)
    second = rank_guides(guide_map, sequence)

    assert first == second
    assert first.ranking_id == second.ranking_id
    assert len(first.assessments) == len(guide_map.candidates)
    assert [assessment.rank for assessment in first.assessments] == list(
        range(1, len(first.assessments) + 1)
    )
    assert {assessment.candidate_id for assessment in first.assessments} == {
        candidate.candidate_id for candidate in guide_map.candidates
    }


def test_local_specificity_penalizes_a_second_exact_guide_match():
    unique_sequence = _target(GUIDE_ONE)
    repeated_sequence = unique_sequence + "AAAA" + _target(GUIDE_ONE)
    unique_map = map_guides(
        GuideMappingRequest(
            sequence=unique_sequence,
            source_record_id="unique-target",
            editor="CBE",
        )
    )
    repeated_map = map_guides(
        GuideMappingRequest(
            sequence=repeated_sequence,
            source_record_id="repeated-target",
            editor="CBE",
        )
    )
    unique_candidate = next(
        item for item in unique_map.candidates if item.guide_rna == GUIDE_ONE
    )
    repeated_candidate = next(
        item for item in repeated_map.candidates if item.guide_rna == GUIDE_ONE
    )
    unique_assessment = next(
        item
        for item in rank_guides(unique_map, unique_sequence).assessments
        if item.candidate_id == unique_candidate.candidate_id
    )
    repeated_assessment = next(
        item
        for item in rank_guides(repeated_map, repeated_sequence).assessments
        if item.candidate_id == repeated_candidate.candidate_id
    )

    assert _component(repeated_assessment, "local_specificity").value < _component(
        unique_assessment, "local_specificity"
    ).value


def test_empty_map_produces_valid_empty_ranking():
    sequence = "A" * 60
    guide_map = map_guides(
        GuideMappingRequest(
            sequence=sequence,
            source_record_id="empty-target",
            editor="CBE",
        )
    )
    ranking = rank_guides(guide_map, sequence)
    assert ranking.assessments == ()
    assert ranking.mapped_candidate_ids == ()


def test_ranking_rejects_a_different_target_even_when_length_matches():
    sequence = _target(GUIDE_ONE)
    guide_map = map_guides(
        GuideMappingRequest(
            sequence=sequence,
            source_record_id="identity-target",
            editor="CBE",
        )
    )
    replacement = "A" + sequence[1:]
    with pytest.raises(ValueError, match="sequence identity"):
        rank_guides(guide_map, replacement)
    with pytest.raises(ValueError, match="uppercase DNA/IUPAC"):
        rank_guides(guide_map, sequence.lower())
    with pytest.raises(ValueError, match="uppercase DNA/IUPAC"):
        rank_guides(guide_map, "X" * len(sequence))


def test_ranking_contract_rejects_identity_and_candidate_coverage_forgery():
    sequence = _target(GUIDE_ONE)
    ranking = rank_guides(
        map_guides(
            GuideMappingRequest(
                sequence=sequence,
                source_record_id="forgery-target",
                editor="CBE",
            )
        ),
        sequence,
    )
    values = ranking.model_dump(round_trip=True)
    values["ranking_id"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="canonical scoring"):
        GuideRanking.model_validate(values)

    values = ranking.model_dump(round_trip=True)
    values["mapped_candidate_ids"] = ()
    with pytest.raises(ValidationError, match="every mapped candidate"):
        GuideRanking.model_validate(values)
