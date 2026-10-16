"""Immutable local artifact and draft storage for the CasAI desktop workspace."""

from __future__ import annotations

import json
import os
import re
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import Contract, ResearchDraft, checksum
from app.modules.information_processor.datasets import DatasetDraft
from app.modules.information_processor.references import ReferenceDraft

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}", flags=re.ASCII)
_MARKER = "$artifact"
StoredDraft = ResearchDraft | DatasetDraft | ReferenceDraft


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
        self._ensure_directory(self.root)
        self._ensure_directory(self.artifact_root)
        self._ensure_directory(self.artifacts)
        self._ensure_directory(self.drafts)

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
                if not path.is_file() or path.read_bytes() != content:
                    raise WorkspaceIntegrityError(
                        "Immutable workspace object has conflicting bytes"
                    )
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
