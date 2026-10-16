"""Explainable, component-wise heuristic ranking for mapped guide candidates."""

from __future__ import annotations

from app.modules.guide_mapping.contracts import (
    CandidateAssessment,
    GuideCandidate,
    GuideMap,
    GuideRanking,
    ScoreComponent,
    ScoreName,
    canonical_identity,
)
from app.modules.information_processor.contracts import checksum
from app.modules.simulation.nucleotides import IUPAC, revcomp
from app.modules.simulation.scoring import on_target_score

_BASIS: tuple[ScoreName, ...] = (
    "desired_coverage",
    "bystander_avoidance",
    "window_centrality",
    "local_specificity",
    "guide_composition",
)


def _round(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)


def _local_specificity(candidate: GuideCandidate, sequence: str) -> float:
    intended_start = (
        candidate.protospacer_start - 1
        if candidate.strand == "+"
        else len(sequence) - candidate.protospacer_end
    )
    weight_total = 0.0
    for strand, oriented in (("+", sequence), ("-", revcomp(sequence))):
        for start in range(len(oriented) - len(candidate.guide_rna) + 1):
            if strand == candidate.strand and start == intended_start:
                continue
            segment = oriented[start : start + len(candidate.guide_rna)]
            distance = sum(
                observed != expected
                for observed, expected in zip(segment, candidate.guide_rna, strict=True)
            )
            if distance <= 3:
                weight_total += (4 - distance) / 4
    risk = 1 - 0.5**weight_total
    return 1 - risk


def _components(
    candidate: GuideCandidate,
    desired_count: int,
    sequence: str,
) -> tuple[ScoreComponent, ...]:
    coverage = (
        len(candidate.desired_edit_positions) / desired_count if desired_count else 1.0
    )
    bystander = 1.0 / (1.0 + len(candidate.bystander_positions))
    low, high = candidate.edit_window
    center = (low + high) / 2
    relevant = [
        site.guide_position
        for site in candidate.edit_sites
        if site.desired or desired_count == 0
    ]
    if not relevant:
        centrality = 0.0
    elif low == high:
        centrality = 1.0
    else:
        maximum = max(center - low, high - center)
        centrality = 1.0 - sum(abs(position - center) for position in relevant) / (
            len(relevant) * maximum
        )
    composition = on_target_score(candidate.guide_rna)
    specificity = _local_specificity(candidate, sequence)
    values = {
        "desired_coverage": (
            coverage,
            "Fraction of explicitly requested substitutions mapped by this candidate",
            "A value of 1 without requested edits means coverage was not constrained",
        ),
        "bystander_avoidance": (
            bystander,
            "Inverse burden from other editable bases inside the declared window",
            "Potential edits are sequence-level possibilities, not measured editing outcomes",
        ),
        "window_centrality": (
            centrality,
            "Proximity of relevant editable bases to the center of the declared window",
            "Window position is a simple geometric heuristic, not an efficiency measurement",
        ),
        "local_specificity": (
            specificity,
            "Absence of other exact or close guide matches in the supplied target",
            "This is PAM-agnostic and not a genome-wide off-target analysis",
        ),
        "guide_composition": (
            composition,
            "Guide-intrinsic GC balance and homopolymer heuristic",
            "This is not a trained efficacy model or experimental measurement",
        ),
    }
    return tuple(
        ScoreComponent(
            name=name,
            value=_round(values[name][0]),
            explanation=values[name][1],
            limitation=values[name][2],
        )
        for name in _BASIS
    )


def rank_guides(guide_map: GuideMap, sequence: str) -> GuideRanking:
    """Rank every candidate lexicographically while preserving each heuristic component."""

    normalized = sequence.upper()
    if sequence != normalized or set(normalized) - set(IUPAC):
        raise ValueError("Ranking target must be uppercase DNA/IUPAC")
    if len(normalized) != guide_map.target_length or checksum(
        normalized.encode("ascii")
    ) != guide_map.target_sequence_checksum:
        raise ValueError("Ranking target does not match the guide map sequence identity")

    desired_count = len(guide_map.desired_edits)
    scored = [
        (candidate, _components(candidate, desired_count, normalized))
        for candidate in guide_map.candidates
    ]
    scored.sort(
        key=lambda item: (
            *(-component.value for component in item[1]),
            item[0].candidate_id,
        )
    )
    assessments = tuple(
        CandidateAssessment(
            candidate_id=candidate.candidate_id,
            rank=rank,
            components=components,
            ranking_basis=_BASIS,
        )
        for rank, (candidate, components) in enumerate(scored, start=1)
    )
    values = {
        "schema_version": "casai.guide-ranking.v1",
        "guide_map_id": guide_map.map_id,
        "target_sequence_checksum": guide_map.target_sequence_checksum,
        "method_version": "casai.guide-ranking.heuristic.v1",
        "mapped_candidate_ids": tuple(
            candidate.candidate_id for candidate in guide_map.candidates
        ),
        "assessments": assessments,
        "aggregate_score": None,
        "claim_type": "heuristic",
    }
    serializable = {
        key: tuple(item.model_dump(mode="json", round_trip=True) for item in value)
        if key == "assessments"
        else value
        for key, value in values.items()
    }
    return GuideRanking(ranking_id=canonical_identity(serializable), **values)
