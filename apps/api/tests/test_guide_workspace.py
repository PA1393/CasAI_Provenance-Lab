"""Guide maps and rankings remain bound to exact confirmed local research versions."""

import json

import pytest

from app.modules.guide_mapping import GuideMappingRequest, map_guides, rank_guides
from app.modules.guide_mapping.contracts import GuideMap, GuideRanking, canonical_identity
from app.modules.information_processor.confirmation import (
    ConfirmationRequest,
    confirm_research_draft,
)
from app.modules.information_processor.contracts import IntakeRequest
from app.modules.information_processor.processing import process_input
from app.modules.information_processor.workspace import (
    LocalWorkspace,
    WorkspaceIntegrityError,
)

GUIDE = "AAACACAAAAAAAAAAAAAA"
SEQUENCE = "TTTT" + GUIDE + "AGG" + "TTTT"


def _confirmed(workspace, *, sequence=SEQUENCE, record_id="target"):
    draft = process_input(
        IntakeRequest(
            input_method="fasta",
            content=f">{record_id}\n{sequence}\n",
            molecule_type="DNA",
        )
    )
    manifest = workspace.save_draft(draft)
    version = confirm_research_draft(
        workspace,
        ConfirmationRequest(
            source_draft_id=manifest.draft_id,
            expected_normalized_checksum=draft.normalized_checksum,
            expected_artifact_checksum=draft.original_artifact.checksum,
            actor_id="local-researcher",
            decision="approve",
            acknowledged_warning_codes=tuple(
                sorted({warning.code for warning in draft.warnings})
            ),
        ),
    )
    return version


def _mapping(version, *, sequence=SEQUENCE, record_id="target", window=(4, 8)):
    return map_guides(
        GuideMappingRequest(
            sequence=sequence,
            source_version_id=version.version_id,
            source_record_id=record_id,
            editor="CBE",
            edit_window=window,
        )
    )


def _reidentified(model, **updates):
    values = model.model_dump(round_trip=True)
    identity_field = "map_id" if isinstance(model, GuideMap) else "ranking_id"
    values.update(updates)
    values.pop(identity_field)
    values[identity_field] = canonical_identity(values)
    contract = GuideMap if isinstance(model, GuideMap) else GuideRanking
    return contract.model_validate(values)


def test_save_and_reopen_map_and_ranking_with_exact_confirmed_source(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    version = _confirmed(workspace)
    guide_map = _mapping(version)
    ranking = rank_guides(guide_map, SEQUENCE)

    workspace.save_guide_map(guide_map)
    workspace.save_guide_ranking(ranking)

    assert workspace.load_guide_map(guide_map.map_id) == guide_map
    assert workspace.load_guide_ranking(ranking.ranking_id) == ranking
    assert workspace.guide_map_path(guide_map.map_id).is_file()
    assert workspace.guide_ranking_path(ranking.ranking_id).is_file()


def test_repeated_map_and_ranking_saves_are_idempotent(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    version = _confirmed(workspace)
    guide_map = _mapping(version)
    ranking = rank_guides(guide_map, SEQUENCE)

    workspace.save_guide_map(guide_map)
    workspace.save_guide_map(guide_map)
    workspace.save_guide_ranking(ranking)
    workspace.save_guide_ranking(ranking)

    assert len(tuple((tmp_path / "guide-maps").glob("*.json"))) == 1
    assert len(tuple((tmp_path / "guide-rankings").glob("*.json"))) == 1


def test_map_must_reference_an_exact_dna_record_and_sequence(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    version = _confirmed(workspace)
    guide_map = _mapping(version)

    wrong_record = _reidentified(guide_map, source_record_id="absent")
    with pytest.raises(WorkspaceIntegrityError, match="absent or ambiguous"):
        workspace.save_guide_map(wrong_record)

    wrong_sequence = _reidentified(
        guide_map,
        target_sequence_checksum="sha256:" + "0" * 64,
    )
    with pytest.raises(WorkspaceIntegrityError, match="does not match"):
        workspace.save_guide_map(wrong_sequence)


def test_map_cannot_bind_a_protein_record_even_when_letters_look_like_dna(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    draft = process_input(
        IntakeRequest(
            input_method="pasted_sequence",
            content="ACGTACGTACGTACGTACGTAGG",
            molecule_type="protein",
        )
    )
    manifest = workspace.save_draft(draft)
    version = confirm_research_draft(
        workspace,
        ConfirmationRequest(
            source_draft_id=manifest.draft_id,
            expected_normalized_checksum=draft.normalized_checksum,
            expected_artifact_checksum=draft.original_artifact.checksum,
            actor_id="reviewer",
            decision="approve",
            acknowledged_warning_codes=tuple(
                sorted({warning.code for warning in draft.warnings})
            ),
        ),
    )
    sequence = draft.records[0].sequence.value
    guide_map = _mapping(version, sequence=sequence, record_id="sequence_1")

    with pytest.raises(WorkspaceIntegrityError, match="confirmed DNA"):
        workspace.save_guide_map(guide_map)


def test_ranking_must_reference_the_exact_stored_map(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    version = _confirmed(workspace)
    first = _mapping(version)
    second = _mapping(version, window=(3, 8))
    workspace.save_guide_map(first)
    workspace.save_guide_map(second)
    ranking = rank_guides(first, SEQUENCE)
    mismatched = _reidentified(ranking, guide_map_id=second.map_id)

    with pytest.raises(WorkspaceIntegrityError, match="does not match"):
        workspace.save_guide_ranking(mismatched)


def test_corrupt_stored_map_or_ranking_is_detected(tmp_path):
    workspace = LocalWorkspace(tmp_path)
    version = _confirmed(workspace)
    guide_map = _mapping(version)
    ranking = rank_guides(guide_map, SEQUENCE)
    workspace.save_guide_map(guide_map)
    workspace.save_guide_ranking(ranking)

    map_path = workspace.guide_map_path(guide_map.map_id)
    map_values = json.loads(map_path.read_text())
    map_values["target_length"] += 1
    map_path.write_text(json.dumps(map_values))
    with pytest.raises(WorkspaceIntegrityError, match="failed validation"):
        workspace.load_guide_map(guide_map.map_id)

    map_path.write_text(guide_map.model_dump_json(round_trip=True))
    ranking_path = workspace.guide_ranking_path(ranking.ranking_id)
    ranking_values = json.loads(ranking_path.read_text())
    ranking_values["method_version"] = "forged"
    ranking_path.write_text(json.dumps(ranking_values))
    with pytest.raises(WorkspaceIntegrityError, match="failed validation"):
        workspace.load_guide_ranking(ranking.ranking_id)
