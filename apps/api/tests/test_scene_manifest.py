"""Safe declarative molecular-scene manifest contracts."""

import pytest
from pydantic import ValidationError

from app.modules.scene_manifest import (
    Annotation,
    CameraState,
    CoordinateTransform,
    EvidenceSource,
    Measurement,
    MolecularAsset,
    MolecularSelection,
    SceneManifest,
    VisibilityState,
    build_scene_manifest,
)

CHECKSUM = "sha256:" + "1" * 64


def _asset(**updates):
    values = {
        "asset_id": "complex",
        "source_type": "workspace_artifact",
        "source_id": CHECKSUM,
        "format": "mmcif",
        "checksum": CHECKSUM,
        "structure_status": "predicted",
    }
    values.update(updates)
    return MolecularAsset(**values)


def _selections():
    return (
        MolecularSelection(
            selection_id="enzyme",
            asset_id="complex",
            role="protein",
            chain_id="A",
        ),
        MolecularSelection(
            selection_id="guide",
            asset_id="complex",
            role="guide",
            chain_id="G",
            nucleotide_positions=(1, 2, 3),
        ),
        MolecularSelection(
            selection_id="catalytic",
            asset_id="complex",
            role="catalytic_residue",
            chain_id="A",
            residue_numbers=(840,),
        ),
    )


def _scene():
    evidence = EvidenceSource(source_type="predicted", citation="model output v1")
    return build_scene_manifest(
        scene_status="predicted",
        assets=(_asset(),),
        selections=_selections(),
        annotations=(
            Annotation(
                annotation_id="active-site-note",
                selection_ids=("catalytic",),
                text="Predicted active-site location for explanatory review.",
                source=evidence,
                claim_type="predicted",
            ),
        ),
        measurements=(
            Measurement(
                measurement_id="active-to-guide",
                from_selection_id="catalytic",
                to_selection_id="guide",
                value=4.2,
                unit="angstrom",
                source=evidence,
                claim_type="predicted",
            ),
        ),
        transforms=(
            CoordinateTransform(
                asset_id="complex",
                matrix=(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1),
            ),
        ),
        cameras=(
            CameraState(
                camera_id="overview",
                position=(10, 10, 10),
                target=(0, 0, 0),
                up=(0, 1, 0),
            ),
        ),
        visibility_states=(
            VisibilityState(
                state_id="guide-focus",
                visible_selection_ids=("enzyme", "guide", "catalytic"),
            ),
        ),
    )


def test_scene_manifest_is_deterministic_and_explicit():
    first = _scene()
    second = _scene()

    assert first == second
    assert first.scene_id == second.scene_id
    assert first.scene_status == "predicted"
    assert first.measurements[0].unit == "angstrom"
    assert first.selections[1].coordinate_system == "1-based-inclusive"


@pytest.mark.parametrize(
    "source_id",
    [
        "https://untrusted.example/structure.cif",
        "javascript:alert(1)",
        "data:text/plain,atoms",
        "file:///tmp/private.pdb",
    ],
)
def test_asset_rejects_urls_and_active_locator_schemes(source_id):
    with pytest.raises(ValidationError, match="trusted identifiers"):
        _asset(source_type="database_record", source_id=source_id)


def test_workspace_asset_must_use_its_checksum_as_source():
    with pytest.raises(ValidationError, match="content checksum"):
        _asset(source_id="sha256:" + "2" * 64)


def test_generated_asset_cannot_be_labeled_experimentally_reported():
    with pytest.raises(ValidationError, match="cannot be experimentally reported"):
        _asset(
            source_type="generated",
            source_id="casai-prediction-1",
            structure_status="experimentally reported",
        )


def test_nucleic_and_protein_feature_selections_require_coordinates():
    with pytest.raises(ValidationError, match="nucleotide positions"):
        MolecularSelection(
            selection_id="guide",
            asset_id="complex",
            role="guide",
            chain_id="G",
        )
    with pytest.raises(ValidationError, match="residue numbers"):
        MolecularSelection(
            selection_id="domain",
            asset_id="complex",
            role="domain",
            chain_id="A",
        )


def test_selection_rejects_ambiguous_coordinate_order():
    with pytest.raises(ValidationError, match="unique and ascending"):
        MolecularSelection(
            selection_id="guide",
            asset_id="complex",
            role="guide",
            nucleotide_positions=(2, 1, 2),
        )

    with pytest.raises(ValidationError, match="unsupported characters"):
        MolecularSelection(
            selection_id="atoms",
            asset_id="complex",
            role="protein",
            atom_names=("CA;script",),
        )


def test_scene_rejects_unknown_cross_references():
    values = _scene().model_dump(round_trip=True)
    values["measurements"][0]["to_selection_id"] = "missing"
    values.pop("scene_id")
    from app.modules.scene_manifest.contracts import canonical_identity

    with pytest.raises(ValidationError, match="unknown selection"):
        SceneManifest(scene_id=canonical_identity(values), **values)


def test_claim_types_must_match_evidence_source():
    with pytest.raises(ValidationError, match="claim type"):
        Annotation(
            annotation_id="bad-claim",
            selection_ids=("enzyme",),
            text="Unsupported claim",
            source=EvidenceSource(source_type="predicted", citation="model"),
            claim_type="experimentally validated",
        )


def test_measurement_rejects_nonpositive_or_same_selection_distance():
    source = EvidenceSource(source_type="explanatory", citation="scene geometry")
    with pytest.raises(ValidationError):
        Measurement(
            measurement_id="zero-distance",
            from_selection_id="guide",
            to_selection_id="enzyme",
            value=0,
            unit="angstrom",
            source=source,
            claim_type="explanatory",
        )
    with pytest.raises(ValidationError, match="distinct"):
        Measurement(
            measurement_id="self-distance",
            from_selection_id="guide",
            to_selection_id="guide",
            value=1,
            unit="angstrom",
            source=source,
            claim_type="explanatory",
        )


def test_explanatory_scene_cannot_claim_trajectory():
    with pytest.raises(ValidationError, match="cannot claim a trajectory"):
        build_scene_manifest(
            scene_status="explanatory",
            assets=(_asset(),),
            selections=_selections(),
            trajectory_artifact_id="sha256:" + "3" * 64,
        )


def test_camera_and_transform_geometry_are_bounded():
    with pytest.raises(ValidationError, match="must differ"):
        CameraState(
            camera_id="bad",
            position=(0, 0, 0),
            target=(0, 0, 0),
            up=(0, 1, 0),
        )
    with pytest.raises(ValidationError, match="parallel"):
        CameraState(
            camera_id="parallel",
            position=(0, 0, 1),
            target=(0, 0, 0),
            up=(0, 0, 1),
        )
    with pytest.raises(ValidationError):
        CoordinateTransform(asset_id="complex", matrix=(1, 0, 0))
    with pytest.raises(ValidationError, match="collapse molecular geometry"):
        CoordinateTransform(
            asset_id="complex",
            matrix=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
        )
    with pytest.raises(ValidationError, match="affine homogeneous"):
        CoordinateTransform(
            asset_id="complex",
            matrix=(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0),
        )


def test_scene_rejects_forged_identity():
    values = _scene().model_dump(round_trip=True)
    values["scene_id"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="canonical manifest"):
        SceneManifest.model_validate(values)
