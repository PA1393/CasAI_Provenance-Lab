"""Immutable local artifact and draft storage for the CasAI desktop workspace."""

from __future__ import annotations

import errno
import json
import os
import re
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import Contract, ResearchDraft, checksum
from app.modules.information_processor.datasets import DatasetDraft
from app.modules.information_processor.references import ReferenceDraft

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}", flags=re.ASCII)
_MARKER = "$artifact"
StoredDraft = ResearchDraft | DatasetDraft | ReferenceDraft

if TYPE_CHECKING:
    from app.modules.guide_mapping.contracts import GuideMap, GuideRanking
    from app.modules.information_processor.confirmation import ConfirmedResearchObject
    from app.modules.scene_manifest import SceneManifest
    from app.modules.simulation import SimulationPlan


class WorkspaceError(RuntimeError):
    """Base error for local workspace operations."""


class WorkspaceIntegrityError(WorkspaceError):
    """Stored bytes or manifests no longer match their immutable identity."""


class DraftNotFoundError(WorkspaceError):
    """Requested draft identity is absent from this workspace."""


class StoredArtifact(Contract):
    checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    byte_length: int = Field(ge=0, strict=True)


def _markers(value: Any) -> set[str]:
    if isinstance(value, dict):
        if set(value) == {_MARKER} and isinstance(value[_MARKER], str):
            return {value[_MARKER]}
        return set().union(*(_markers(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_markers(item) for item in value), set())
    return set()


def _manifest_identity(data: dict[str, Any]) -> str:
    return checksum(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )


class DraftManifest(Contract):
    schema_version: Literal["casai.workspace.draft.v1"] = "casai.workspace.draft.v1"
    draft_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    draft_kind: Literal["sequence", "dataset", "reference"]
    draft_schema_version: str
    normalized_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifacts: tuple[StoredArtifact, ...]
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_identity(self) -> DraftManifest:
        artifact_ids = tuple(artifact.checksum for artifact in self.artifacts)
        if len(set(artifact_ids)) != len(artifact_ids):
            raise ValueError("Stored artifact identities must be unique")
        if _markers(self.payload) != set(artifact_ids):
            raise ValueError("Draft artifact markers must match the artifact manifest")
        identity = self.model_dump(round_trip=True, exclude={"draft_id"})
        if self.draft_id != _manifest_identity(identity):
            raise ValueError("Draft identity must match its canonical manifest")
        return self


def _draft_parts(
    draft: StoredDraft,
) -> tuple[str, str, str, dict[str, Any], tuple[tuple[str, bytes], ...]]:
    payload = draft.model_dump(mode="json", round_trip=True)
    artifacts: list[tuple[str, bytes]] = []
    if isinstance(draft, ResearchDraft):
        kind = "sequence"
        normalized = draft.normalized_checksum
        source = draft.original_artifact
        payload["original_artifact"]["content"] = {_MARKER: source.checksum}
        artifacts.append((source.checksum, source.content))
    elif isinstance(draft, DatasetDraft):
        kind = "dataset"
        normalized = draft.normalized_checksum
        for stored, source in zip(payload["artifacts"], draft.artifacts, strict=True):
            stored["content"] = {_MARKER: source.checksum}
            artifacts.append((source.checksum, source.content))
    elif isinstance(draft, ReferenceDraft):
        kind = "reference"
        normalized = draft.sequence_checksum
        source = draft.artifact
        payload["artifact"]["content"] = {_MARKER: source.checksum}
        artifacts.append((source.checksum, source.content))
    else:
        raise TypeError("Unsupported draft type")
    unique = tuple(dict(artifacts).items())
    return kind, draft.schema_version, normalized, payload, unique


def _inflate(value: Any, artifacts: dict[str, bytes]) -> Any:
    if isinstance(value, dict):
        if set(value) == {_MARKER}:
            identity = value[_MARKER]
            try:
                return artifacts[identity]
            except KeyError as exc:
                raise WorkspaceIntegrityError("Manifest references an absent artifact") from exc
        return {key: _inflate(item, artifacts) for key, item in value.items()}
    if isinstance(value, list):
        return [_inflate(item, artifacts) for item in value]
    return value


class LocalWorkspace:
    """Content-addressed files and canonical draft manifests under one local root."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.artifact_root = self.root / "artifacts"
        self.artifacts = self.artifact_root / "sha256"
        self.drafts = self.root / "drafts"
        self.versions = self.root / "versions"
        self.guide_maps = self.root / "guide-maps"
        self.guide_rankings = self.root / "guide-rankings"
        self.scenes = self.root / "scene-manifests"
        self.simulation_plans = self.root / "simulation-plans"
        self._ensure_directory(self.root)
        self._ensure_directory(self.artifact_root)
        self._ensure_directory(self.artifacts)
        self._ensure_directory(self.drafts)
        self._ensure_directory(self.versions)
        self._ensure_directory(self.guide_maps)
        self._ensure_directory(self.guide_rankings)
        self._ensure_directory(self.scenes)
        self._ensure_directory(self.simulation_plans)

    def _ensure_directory(self, path: Path) -> None:
        if path.exists() and path.is_symlink():
            raise WorkspaceIntegrityError("Workspace directories cannot be symbolic links")
        if path != self.root and path.parent.exists() and (
            path.parent.is_symlink() or not path.parent.resolve().is_relative_to(self.root)
        ):
            raise WorkspaceIntegrityError("Workspace parent escapes its authorized root")
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir() or not path.resolve().is_relative_to(self.root):
            raise WorkspaceIntegrityError("Workspace path escapes its authorized root")

    @staticmethod
    def _hex(identity: str) -> str:
        if not _SHA256.fullmatch(identity):
            raise WorkspaceIntegrityError("Workspace identity must be a SHA-256 value")
        return identity.removeprefix("sha256:")

    def artifact_path(self, identity: str) -> Path:
        digest = self._hex(identity)
        self._ensure_directory(self.artifacts)
        directory = self.artifacts / digest[:2]
        self._ensure_directory(directory)
        return directory / digest

    def manifest_path(self, draft_id: str) -> Path:
        self._ensure_directory(self.drafts)
        return self.drafts / f"{self._hex(draft_id)}.json"

    def version_path(self, version_id: str) -> Path:
        self._ensure_directory(self.versions)
        return self.versions / f"{self._hex(version_id)}.json"

    def guide_map_path(self, map_id: str) -> Path:
        self._ensure_directory(self.guide_maps)
        return self.guide_maps / f"{self._hex(map_id)}.json"

    def guide_ranking_path(self, ranking_id: str) -> Path:
        self._ensure_directory(self.guide_rankings)
        return self.guide_rankings / f"{self._hex(ranking_id)}.json"

    def scene_manifest_path(self, scene_id: str) -> Path:
        self._ensure_directory(self.scenes)
        return self.scenes / f"{self._hex(scene_id)}.json"

    def simulation_plan_path(self, plan_id: str) -> Path:
        self._ensure_directory(self.simulation_plans)
        return self.simulation_plans / f"{self._hex(plan_id)}.json"

    @staticmethod
    def _atomic_create(path: Path, content: bytes) -> None:
        if path.exists():
            if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                raise WorkspaceIntegrityError("Immutable workspace object has conflicting bytes")
            return
        descriptor, temporary_name = tempfile.mkstemp(prefix=".casai-", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                    raise WorkspaceIntegrityError(
                        "Immutable workspace object has conflicting bytes"
                    )
            except OSError as exc:
                if exc.errno not in {
                    errno.EPERM, errno.EXDEV, errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP,
                }:
                    raise
                # FAT/exFAT and some shares do not support links. Exclusive creation
                # never overwrites a winner; failed/partial writes fail checksum checks.
                try:
                    exclusive = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                        raise WorkspaceIntegrityError(
                            "Immutable workspace object has conflicting bytes"
                        ) from None
                else:
                    with os.fdopen(exclusive, "wb") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
        finally:
            temporary.unlink(missing_ok=True)

    def _store_artifact(self, identity: str, content: bytes) -> StoredArtifact:
        if checksum(content) != identity:
            raise WorkspaceIntegrityError("Artifact bytes do not match their checksum")
        self._atomic_create(self.artifact_path(identity), content)
        return StoredArtifact(checksum=identity, byte_length=len(content))

    def save_draft(self, draft: StoredDraft) -> DraftManifest:
        kind, schema, normalized, payload, artifact_values = _draft_parts(draft)
        stored = tuple(
            self._store_artifact(identity, content) for identity, content in artifact_values
        )
        identity = {
            "schema_version": "casai.workspace.draft.v1",
            "draft_kind": kind,
            "draft_schema_version": schema,
            "normalized_checksum": normalized,
            "artifacts": [artifact.model_dump(round_trip=True) for artifact in stored],
            "payload": payload,
        }
        manifest = DraftManifest(draft_id=_manifest_identity(identity), **identity)
        manifest_bytes = manifest.model_dump_json(round_trip=True).encode("utf-8")
        self._atomic_create(self.manifest_path(manifest.draft_id), manifest_bytes)
        return manifest

    def _load_artifacts(self, manifest: DraftManifest) -> dict[str, bytes]:
        loaded = {}
        for artifact in manifest.artifacts:
            path = self.artifact_path(artifact.checksum)
            if path.is_symlink() or not path.is_file():
                raise WorkspaceIntegrityError("Draft artifact is missing")
            content = path.read_bytes()
            if len(content) != artifact.byte_length or checksum(content) != artifact.checksum:
                raise WorkspaceIntegrityError("Draft artifact failed its integrity check")
            loaded[artifact.checksum] = content
        return loaded

    def load_draft(self, draft_id: str) -> StoredDraft:
        path = self.manifest_path(draft_id)
        if path.is_symlink():
            raise WorkspaceIntegrityError("Draft manifest cannot be a symbolic link")
        if not path.is_file():
            raise DraftNotFoundError("Draft does not exist in this workspace")
        try:
            manifest = DraftManifest.model_validate_json(path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            raise WorkspaceIntegrityError("Draft manifest failed validation") from exc
        if manifest.draft_id != draft_id:
            raise WorkspaceIntegrityError("Draft path does not match its manifest identity")
        payload = _inflate(deepcopy(manifest.payload), self._load_artifacts(manifest))
        model = {
            "sequence": ResearchDraft,
            "dataset": DatasetDraft,
            "reference": ReferenceDraft,
        }[manifest.draft_kind]
        try:
            draft = model.model_validate(payload)
        except ValueError as exc:
            raise WorkspaceIntegrityError("Stored draft payload failed validation") from exc
        if draft.schema_version != manifest.draft_schema_version:
            raise WorkspaceIntegrityError("Stored draft schema version changed unexpectedly")
        actual_normalized = (
            draft.sequence_checksum
            if isinstance(draft, ReferenceDraft)
            else draft.normalized_checksum
        )
        if actual_normalized != manifest.normalized_checksum:
            raise WorkspaceIntegrityError("Stored draft normalized identity does not match")
        return draft

    def save_confirmed_version(self, version: ConfirmedResearchObject) -> None:
        from app.modules.information_processor.confirmation import (
            ConfirmationError,
            validate_confirmed_source,
        )

        draft = self.load_draft(version.source_draft_id)
        if not isinstance(draft, ResearchDraft):
            raise WorkspaceIntegrityError("Confirmed version does not reference a sequence draft")
        try:
            validate_confirmed_source(version, draft)
        except ConfirmationError as exc:
            raise WorkspaceIntegrityError(str(exc)) from exc
        content = version.model_dump_json(round_trip=True).encode("utf-8")
        self._atomic_create(self.version_path(version.version_id), content)

    def load_confirmed_version(self, version_id: str) -> ConfirmedResearchObject:
        from app.modules.information_processor.confirmation import (
            ConfirmationError,
            ConfirmedResearchObject,
            validate_confirmed_source,
        )

        path = self.version_path(version_id)
        if path.is_symlink():
            raise WorkspaceIntegrityError("Confirmed version cannot be a symbolic link")
        if not path.is_file():
            raise DraftNotFoundError("Confirmed version does not exist in this workspace")
        try:
            version = ConfirmedResearchObject.model_validate_json(path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            raise WorkspaceIntegrityError("Confirmed version failed validation") from exc
        if version.version_id != version_id:
            raise WorkspaceIntegrityError("Version path does not match its content identity")
        draft = self.load_draft(version.source_draft_id)
        if not isinstance(draft, ResearchDraft):
            raise WorkspaceIntegrityError("Confirmed version does not reference a sequence draft")
        try:
            validate_confirmed_source(version, draft)
        except ConfirmationError as exc:
            raise WorkspaceIntegrityError(str(exc)) from exc
        return version

    def _validate_guide_map_source(self, guide_map: GuideMap) -> None:
        version = self.load_confirmed_version(guide_map.source_version_id)
        matches = tuple(
            record
            for record in version.snapshot.records
            if record.record_id.value == guide_map.source_record_id
        )
        if len(matches) != 1:
            raise WorkspaceIntegrityError(
                "Guide map source record is absent or ambiguous in its confirmed version"
            )
        record = matches[0]
        if record.molecule_type.value != "DNA":
            raise WorkspaceIntegrityError("Guide mapping requires a confirmed DNA record")
        sequence = record.sequence.value
        if (
            len(sequence) != guide_map.target_length
            or checksum(sequence.encode("ascii")) != guide_map.target_sequence_checksum
        ):
            raise WorkspaceIntegrityError("Guide map target does not match its confirmed record")

    def save_guide_map(self, guide_map: GuideMap) -> None:
        from app.modules.guide_mapping.contracts import GuideMap

        try:
            guide_map = GuideMap.model_validate(guide_map.model_dump(round_trip=True))
        except ValueError as exc:
            raise WorkspaceIntegrityError("Guide map failed validation") from exc
        self._validate_guide_map_source(guide_map)
        content = guide_map.model_dump_json(round_trip=True).encode("utf-8")
        self._atomic_create(self.guide_map_path(guide_map.map_id), content)

    def load_guide_map(self, map_id: str) -> GuideMap:
        from app.modules.guide_mapping.contracts import GuideMap

        path = self.guide_map_path(map_id)
        if path.is_symlink():
            raise WorkspaceIntegrityError("Guide map cannot be a symbolic link")
        if not path.is_file():
            raise DraftNotFoundError("Guide map does not exist in this workspace")
        try:
            guide_map = GuideMap.model_validate_json(path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            raise WorkspaceIntegrityError("Guide map failed validation") from exc
        if guide_map.map_id != map_id:
            raise WorkspaceIntegrityError("Guide map path does not match its content identity")
        self._validate_guide_map_source(guide_map)
        return guide_map

    def _validate_guide_ranking_source(self, ranking: GuideRanking) -> None:
        guide_map = self.load_guide_map(ranking.guide_map_id)
        expected_candidates = tuple(
            candidate.candidate_id for candidate in guide_map.candidates
        )
        if (
            ranking.target_sequence_checksum != guide_map.target_sequence_checksum
            or ranking.mapped_candidate_ids != expected_candidates
        ):
            raise WorkspaceIntegrityError("Guide ranking does not match its stored guide map")

    def save_guide_ranking(self, ranking: GuideRanking) -> None:
        from app.modules.guide_mapping.contracts import GuideRanking

        try:
            ranking = GuideRanking.model_validate(ranking.model_dump(round_trip=True))
        except ValueError as exc:
            raise WorkspaceIntegrityError("Guide ranking failed validation") from exc
        self._validate_guide_ranking_source(ranking)
        content = ranking.model_dump_json(round_trip=True).encode("utf-8")
        self._atomic_create(self.guide_ranking_path(ranking.ranking_id), content)

    def load_guide_ranking(self, ranking_id: str) -> GuideRanking:
        from app.modules.guide_mapping.contracts import GuideRanking

        path = self.guide_ranking_path(ranking_id)
        if path.is_symlink():
            raise WorkspaceIntegrityError("Guide ranking cannot be a symbolic link")
        if not path.is_file():
            raise DraftNotFoundError("Guide ranking does not exist in this workspace")
        try:
            ranking = GuideRanking.model_validate_json(path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            raise WorkspaceIntegrityError("Guide ranking failed validation") from exc
        if ranking.ranking_id != ranking_id:
            raise WorkspaceIntegrityError("Guide ranking path does not match its content identity")
        self._validate_guide_ranking_source(ranking)
        return ranking

    def _validate_scene_assets(self, scene: SceneManifest) -> None:
        for asset in scene.assets:
            if asset.source_type != "workspace_artifact":
                continue
            path = self.artifact_path(asset.checksum)
            if path.is_symlink() or not path.is_file():
                raise WorkspaceIntegrityError("Scene workspace asset is missing")
            content = path.read_bytes()
            if checksum(content) != asset.checksum:
                raise WorkspaceIntegrityError("Scene workspace asset failed integrity checks")

    def save_scene_manifest(self, scene: SceneManifest) -> None:
        from app.modules.scene_manifest import SceneManifest

        try:
            scene = SceneManifest.model_validate(scene.model_dump(round_trip=True))
        except ValueError as exc:
            raise WorkspaceIntegrityError("Scene manifest failed validation") from exc
        self._validate_scene_assets(scene)
        content = scene.model_dump_json(round_trip=True).encode("utf-8")
        self._atomic_create(self.scene_manifest_path(scene.scene_id), content)

    def load_scene_manifest(self, scene_id: str) -> SceneManifest:
        from app.modules.scene_manifest import SceneManifest

        path = self.scene_manifest_path(scene_id)
        if path.is_symlink():
            raise WorkspaceIntegrityError("Scene manifest cannot be a symbolic link")
        if not path.is_file():
            raise DraftNotFoundError("Scene manifest does not exist in this workspace")
        try:
            scene = SceneManifest.model_validate_json(path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            raise WorkspaceIntegrityError("Scene manifest failed validation") from exc
        if scene.scene_id != scene_id:
            raise WorkspaceIntegrityError("Scene path does not match its content identity")
        self._validate_scene_assets(scene)
        return scene

    def _validate_simulation_plan_inputs(self, plan: SimulationPlan) -> None:
        research_ids = {
            item.artifact_id
            for item in plan.inputs
            if item.kind == "confirmed_research_version"
        }
        guide_ids = {
            item.artifact_id for item in plan.inputs if item.kind == "guide_map"
        }
        for version_id in research_ids:
            self.load_confirmed_version(version_id)
        for map_id in guide_ids:
            guide_map = self.load_guide_map(map_id)
            if guide_map.source_version_id not in research_ids:
                raise WorkspaceIntegrityError(
                    "Simulation guide map is not bound to a plan research version"
                )
        for item in plan.inputs:
            if item.kind != "guide_ranking":
                continue
            ranking = self.load_guide_ranking(item.artifact_id)
            if ranking.guide_map_id not in guide_ids:
                raise WorkspaceIntegrityError(
                    "Simulation guide ranking is not bound to a plan guide map"
                )

    def save_simulation_plan(self, plan: SimulationPlan) -> None:
        from app.modules.simulation import SimulationPlan

        try:
            plan = SimulationPlan.model_validate(plan.model_dump(round_trip=True))
        except ValueError as exc:
            raise WorkspaceIntegrityError("Simulation plan failed validation") from exc
        self._validate_simulation_plan_inputs(plan)
        content = plan.model_dump_json(round_trip=True).encode("utf-8")
        self._atomic_create(self.simulation_plan_path(plan.plan_id), content)

    def load_simulation_plan(self, plan_id: str) -> SimulationPlan:
        from app.modules.simulation import SimulationPlan

        path = self.simulation_plan_path(plan_id)
        if path.is_symlink():
            raise WorkspaceIntegrityError("Simulation plan cannot be a symbolic link")
        if not path.is_file():
            raise DraftNotFoundError("Simulation plan does not exist in this workspace")
        try:
            plan = SimulationPlan.model_validate_json(path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            raise WorkspaceIntegrityError("Simulation plan failed validation") from exc
        if plan.plan_id != plan_id:
            raise WorkspaceIntegrityError("Simulation plan path does not match its identity")
        self._validate_simulation_plan_inputs(plan)
        return plan
