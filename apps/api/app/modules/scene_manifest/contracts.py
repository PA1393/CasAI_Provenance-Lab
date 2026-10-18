"""Safe declarative contracts for backend-owned molecular scenes."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import ClaimType, Contract, checksum

SelectionRole = Literal[
    "protein",
    "dna",
    "rna",
    "guide",
    "pam",
    "domain",
    "catalytic_residue",
    "mutation",
    "target_base",
    "interaction_region",
]
StructureStatus = Literal["experimentally reported", "predicted", "explanatory"]


def canonical_identity(values: dict[str, object]) -> str:
    return checksum(
        json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )


class EvidenceSource(Contract):
    source_type: Literal[
        "user-supplied",
        "database-retrieved",
        "AI-inferred",
        "heuristic",
        "predicted",
        "explanatory",
        "experimentally reported",
        "experimentally validated",
        "unresolved",
    ]
    citation: str = Field(min_length=1, max_length=512)


class MolecularAsset(Contract):
    asset_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    source_type: Literal["workspace_artifact", "database_record", "generated"]
    source_id: str = Field(min_length=1, max_length=256)
    format: Literal["pdb", "mmcif"]
    checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    structure_status: StructureStatus

    @model_validator(mode="after")
    def reject_external_locator(self) -> MolecularAsset:
        lowered = self.source_id.lower()
        if "://" in lowered or lowered.startswith(("javascript:", "data:", "file:")):
            raise ValueError("Scene assets must use trusted identifiers, not URLs")
        if self.source_type == "workspace_artifact" and self.source_id != self.checksum:
            raise ValueError("Workspace asset source must equal its content checksum")
        if (
            self.source_type == "generated"
            and self.structure_status == "experimentally reported"
        ):
            raise ValueError("A generated asset cannot be experimentally reported")
        return self


class MolecularSelection(Contract):
    selection_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    asset_id: str
    role: SelectionRole
    chain_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,16}$")
    residue_numbers: tuple[int, ...] = ()
    nucleotide_positions: tuple[int, ...] = ()
    atom_names: tuple[str, ...] = ()
    coordinate_system: Literal["1-based-inclusive"] = "1-based-inclusive"

    @model_validator(mode="after")
    def validate_selection(self) -> MolecularSelection:
        if not (
            self.chain_id
            or self.residue_numbers
            or self.nucleotide_positions
            or self.atom_names
        ):
            raise ValueError("A molecular selection requires an explicit selector")
        for values, label in (
            (self.residue_numbers, "Residue"),
            (self.nucleotide_positions, "Nucleotide"),
        ):
            if any(value <= 0 for value in values):
                raise ValueError(f"{label} coordinates must be positive")
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"{label} coordinates must be unique and ascending")
        if len(set(self.atom_names)) != len(self.atom_names):
            raise ValueError("Atom names must be unique")
        if any(not re.fullmatch(r"[A-Za-z0-9'+*]{1,8}", name) for name in self.atom_names):
            raise ValueError("Atom names contain unsupported characters")
        if self.role in {"dna", "rna", "guide", "pam", "target_base"}:
            if not self.nucleotide_positions:
                raise ValueError("Nucleic-acid selections require nucleotide positions")
        if self.role in {"domain", "catalytic_residue", "mutation"}:
            if not self.residue_numbers:
                raise ValueError("Protein feature selections require residue numbers")
        return self


class Annotation(Contract):
    annotation_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    selection_ids: tuple[str, ...]
    text: str = Field(min_length=1, max_length=2_000)
    source: EvidenceSource
    claim_type: ClaimType

    @model_validator(mode="after")
    def validate_annotation(self) -> Annotation:
        if not self.selection_ids or len(set(self.selection_ids)) != len(self.selection_ids):
            raise ValueError("Annotation selections must be nonempty and unique")
        if self.claim_type != self.source.source_type:
            raise ValueError("Annotation claim type must match its evidence source")
        return self


class Measurement(Contract):
    measurement_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    kind: Literal["distance"] = "distance"
    from_selection_id: str
    to_selection_id: str
    value: float = Field(gt=0)
    unit: Literal["angstrom", "nanometer"]
    source: EvidenceSource
    claim_type: ClaimType

    @model_validator(mode="after")
    def validate_measurement(self) -> Measurement:
        if self.from_selection_id == self.to_selection_id:
            raise ValueError("A distance measurement requires two distinct selections")
        if self.claim_type != self.source.source_type:
            raise ValueError("Measurement claim type must match its evidence source")
        return self


class CoordinateTransform(Contract):
    asset_id: str
    matrix: tuple[
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
    ]

    @model_validator(mode="after")
    def validate_affine_transform(self) -> CoordinateTransform:
        if self.matrix[12:] != (0.0, 0.0, 0.0, 1.0):
            raise ValueError("Coordinate transforms must use an affine homogeneous matrix")
        a, b, c, _, d, e, f, _, g, h, i, *_ = self.matrix
        determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
        if abs(determinant) < 1e-12:
            raise ValueError("Coordinate transform cannot collapse molecular geometry")
        return self


class CameraState(Contract):
    camera_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    up: tuple[float, float, float]

    @model_validator(mode="after")
    def validate_camera(self) -> CameraState:
        if self.position == self.target:
            raise ValueError("Camera position and target must differ")
        if self.up == (0.0, 0.0, 0.0):
            raise ValueError("Camera up vector cannot be zero")
        direction = tuple(target - position for target, position in zip(self.target, self.position))
        cross = (
            direction[1] * self.up[2] - direction[2] * self.up[1],
            direction[2] * self.up[0] - direction[0] * self.up[2],
            direction[0] * self.up[1] - direction[1] * self.up[0],
        )
        if all(abs(value) < 1e-12 for value in cross):
            raise ValueError("Camera up vector cannot be parallel to its viewing direction")
        return self


class VisibilityState(Contract):
    state_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    visible_selection_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_visibility(self) -> VisibilityState:
        if len(set(self.visible_selection_ids)) != len(self.visible_selection_ids):
            raise ValueError("Visible selection identities must be unique")
        return self


class SceneManifest(Contract):
    schema_version: Literal["casai.scene-manifest.v1"] = "casai.scene-manifest.v1"
    scene_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scene_status: Literal["explanatory", "predicted"]
    assets: tuple[MolecularAsset, ...]
    selections: tuple[MolecularSelection, ...]
    annotations: tuple[Annotation, ...] = ()
    measurements: tuple[Measurement, ...] = ()
    transforms: tuple[CoordinateTransform, ...] = ()
    cameras: tuple[CameraState, ...] = ()
    visibility_states: tuple[VisibilityState, ...] = ()
    trajectory_artifact_id: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )

    @model_validator(mode="after")
    def validate_scene(self) -> SceneManifest:
        asset_ids = _unique_ids(self.assets, "asset_id", "Scene asset")
        selection_ids = _unique_ids(self.selections, "selection_id", "Scene selection")
        _unique_ids(self.annotations, "annotation_id", "Scene annotation")
        _unique_ids(self.measurements, "measurement_id", "Scene measurement")
        _unique_ids(self.cameras, "camera_id", "Scene camera")
        _unique_ids(self.visibility_states, "state_id", "Scene visibility state")

        if not asset_ids or not selection_ids:
            raise ValueError("A scene requires assets and explicit selections")
        if any(selection.asset_id not in asset_ids for selection in self.selections):
            raise ValueError("Every selection must reference a scene asset")
        for annotation in self.annotations:
            if not set(annotation.selection_ids) <= selection_ids:
                raise ValueError("Annotation references an unknown selection")
        for measurement in self.measurements:
            if {
                measurement.from_selection_id,
                measurement.to_selection_id,
            } - selection_ids:
                raise ValueError("Measurement references an unknown selection")
        transform_assets = tuple(transform.asset_id for transform in self.transforms)
        if len(set(transform_assets)) != len(transform_assets):
            raise ValueError("Each asset may have at most one coordinate transform")
        if set(transform_assets) - asset_ids:
            raise ValueError("Coordinate transform references an unknown asset")
        for state in self.visibility_states:
            if set(state.visible_selection_ids) - selection_ids:
                raise ValueError("Visibility state references an unknown selection")

        if self.scene_status == "explanatory" and self.trajectory_artifact_id is not None:
            raise ValueError("An explanatory scene cannot claim a trajectory artifact")
        identity = self.model_dump(round_trip=True, exclude={"scene_id"})
        if self.scene_id != canonical_identity(identity):
            raise ValueError("Scene identity must match canonical manifest content")
        return self


def _unique_ids(items: tuple[object, ...], attribute: str, label: str) -> set[str]:
    identities = tuple(getattr(item, attribute) for item in items)
    if len(set(identities)) != len(identities):
        raise ValueError(f"{label} identities must be unique")
    return set(identities)


def build_scene_manifest(
    *,
    scene_status: Literal["explanatory", "predicted"],
    assets: tuple[MolecularAsset, ...],
    selections: tuple[MolecularSelection, ...],
    annotations: tuple[Annotation, ...] = (),
    measurements: tuple[Measurement, ...] = (),
    transforms: tuple[CoordinateTransform, ...] = (),
    cameras: tuple[CameraState, ...] = (),
    visibility_states: tuple[VisibilityState, ...] = (),
    trajectory_artifact_id: str | None = None,
) -> SceneManifest:
    values: dict[str, object] = {
        "schema_version": "casai.scene-manifest.v1",
        "scene_status": scene_status,
        "assets": [asset.model_dump(mode="json") for asset in assets],
        "selections": [selection.model_dump(mode="json") for selection in selections],
        "annotations": [annotation.model_dump(mode="json") for annotation in annotations],
        "measurements": [measurement.model_dump(mode="json") for measurement in measurements],
        "transforms": [transform.model_dump(mode="json") for transform in transforms],
        "cameras": [camera.model_dump(mode="json") for camera in cameras],
        "visibility_states": [state.model_dump(mode="json") for state in visibility_states],
        "trajectory_artifact_id": trajectory_artifact_id,
    }
    return SceneManifest(scene_id=canonical_identity(values), **values)
