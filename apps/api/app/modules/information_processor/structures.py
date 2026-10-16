"""Immutable, non-executable contracts for bounded coordinate-file inspection."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import ConfigDict, Field, computed_field, model_validator

from app.modules.information_processor.contracts import (
    Contract,
    ProcessingNotice,
    checksum,
)


class StructureArtifact(Contract):
    """Exact user-supplied structure bytes; filename is a label, never a path."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )
    filename: str = Field(min_length=1)
    content: bytes
    declared_format: Literal["pdb", "mmcif"]
    claim_type: Literal["user-supplied"] = "user-supplied"

    @computed_field
    @property
    def checksum(self) -> str:
        return checksum(self.content)

    @computed_field
    @property
    def byte_length(self) -> int:
        return len(self.content)


class AtomSite(Contract):
    atom_id: str = Field(min_length=1)
    group: Literal["ATOM", "HETATM"]
    element: str = Field(pattern=r"^[A-Z]{1,3}$")
    atom_name: str = Field(min_length=1)
    alternate_id: str | None = None
    residue_name: str = Field(min_length=1)
    chain_id: str
    residue_number: str = Field(min_length=1)
    insertion_code: str | None = None
    x: float
    y: float
    z: float
    occupancy: float | None = Field(default=None, ge=0, le=1)
    model_number: int = Field(default=1, ge=1, strict=True)
    coordinate_units: Literal["angstrom"] = "angstrom"
    origin: Literal["file_extracted"] = "file_extracted"
    source: str = Field(min_length=1)


class StructureDraft(Contract):
    schema_version: Literal["casai.structure.v1"] = "casai.structure.v1"
    parser_version: Literal["1"] = "1"
    status: Literal["draft"] = "draft"
    executable: Literal[False] = False
    declared_format: Literal["pdb", "mmcif"]
    representation: Literal["coordinate-file"] = "coordinate-file"
    artifact: StructureArtifact
    atoms: tuple[AtomSite, ...]
    chains: tuple[str, ...]
    model_numbers: tuple[int, ...]
    warnings: tuple[ProcessingNotice, ...] = ()

    @model_validator(mode="after")
    def validate_structure(self) -> StructureDraft:
        if self.declared_format != self.artifact.declared_format:
            raise ValueError("Structure format must match its retained artifact")
        if not self.atoms:
            raise ValueError("A structure draft requires at least one coordinate atom")
        identities = [(atom.model_number, atom.atom_id) for atom in self.atoms]
        if len(identities) != len(set(identities)):
            raise ValueError("Atom identifiers must be unique within each model")
        if self.chains != tuple(dict.fromkeys(atom.chain_id for atom in self.atoms)):
            raise ValueError("Chains must match atom order without duplicates")
        if self.model_numbers != tuple(dict.fromkeys(atom.model_number for atom in self.atoms)):
            raise ValueError("Model numbers must match atom order without duplicates")
        if any(not atom.source.startswith(self.artifact.checksum + "#") for atom in self.atoms):
            raise ValueError("Every atom must reference the retained structure artifact")
        return self

    @computed_field
    @property
    def normalized_checksum(self) -> str:
        atoms = []
        for atom in self.atoms:
            values = atom.model_dump(round_trip=True)
            values.pop("source")
            values.pop("origin")
            atoms.append(values)
        payload = {
            "schema_version": self.schema_version,
            "parser_version": self.parser_version,
            "declared_format": self.declared_format,
            "atoms": atoms,
        }
        return checksum(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
