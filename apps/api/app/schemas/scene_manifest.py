"""Bounded API request for backend-owned molecular scene manifests."""

from typing import Literal

from pydantic import Field

from app.modules.information_processor.contracts import Contract
from app.modules.scene_manifest import (
    Annotation,
    CameraState,
    CoordinateTransform,
    Measurement,
    MolecularAsset,
    MolecularSelection,
    VisibilityState,
)


class SceneManifestCreateBody(Contract):
    scene_status: Literal["explanatory", "predicted"]
    assets: tuple[MolecularAsset, ...] = Field(max_length=32)
    selections: tuple[MolecularSelection, ...] = Field(max_length=500)
    annotations: tuple[Annotation, ...] = Field(default=(), max_length=500)
    measurements: tuple[Measurement, ...] = Field(default=(), max_length=500)
    transforms: tuple[CoordinateTransform, ...] = Field(default=(), max_length=32)
    cameras: tuple[CameraState, ...] = Field(default=(), max_length=64)
    visibility_states: tuple[VisibilityState, ...] = Field(default=(), max_length=128)
    trajectory_artifact_id: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
