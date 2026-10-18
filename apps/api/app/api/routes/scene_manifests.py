"""Thin persistence boundary for safe declarative molecular scenes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import get_intake_workspace
from app.modules.information_processor.workspace import (
    DraftNotFoundError,
    LocalWorkspace,
    WorkspaceError,
)
from app.modules.scene_manifest import SceneManifest, build_scene_manifest
from app.schemas.scene_manifest import SceneManifestCreateBody

router = APIRouter(prefix="/scene-manifests", tags=["scene_manifests"])
SceneId = Annotated[str, Path(pattern=r"^sha256:[0-9a-f]{64}$")]


@router.post("", response_model=SceneManifest, status_code=201)
def create_scene_manifest(
    body: SceneManifestCreateBody,
    workspace: LocalWorkspace = Depends(get_intake_workspace),
) -> SceneManifest:
    try:
        scene = build_scene_manifest(
            scene_status=body.scene_status,
            assets=body.assets,
            selections=body.selections,
            annotations=body.annotations,
            measurements=body.measurements,
            transforms=body.transforms,
            cameras=body.cameras,
            visibility_states=body.visibility_states,
            trajectory_artifact_id=body.trajectory_artifact_id,
        )
        workspace.save_scene_manifest(scene)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WorkspaceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return scene


@router.get("/{scene_id}", response_model=SceneManifest)
def get_scene_manifest(
    scene_id: SceneId,
    workspace: LocalWorkspace = Depends(get_intake_workspace),
) -> SceneManifest:
    try:
        return workspace.load_scene_manifest(scene_id)
    except DraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene manifest not found") from exc
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=409,
            detail="Scene manifest failed integrity checks",
        ) from exc
