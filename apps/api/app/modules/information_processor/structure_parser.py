"""Pure, bounded PDB and PDBx/mmCIF coordinate inspection."""

from __future__ import annotations

import math
import shlex
from collections.abc import Callable
from typing import Literal

from pydantic import Field

from app.modules.information_processor.contracts import (
    MAX_INPUT_BYTES,
    Contract,
    ProcessingNotice,
)
from app.modules.information_processor.parser import InputValidationError, decode_input
from app.modules.information_processor.structures import (
    AtomSite,
    StructureArtifact,
    StructureDraft,
)


class StructureLimits(Contract):
    max_input_bytes: int = Field(default=MAX_INPUT_BYTES, gt=0, strict=True)
    max_lines: int = Field(default=250_000, gt=0, strict=True)
    max_atoms: int = Field(default=100_000, gt=0, strict=True)


def _fail(code: str, message: str, line: int | None = None) -> None:
    record_id = f"line:{line}" if line is not None else None
    raise InputValidationError(code, message, record_id)


def _artifact(
    content: bytes,
    filename: str,
    declared_format: Literal["pdb", "mmcif"],
    limits: StructureLimits,
) -> tuple[StructureArtifact, list[str]]:
    text = decode_input(content, max_bytes=limits.max_input_bytes).lstrip("\ufeff")
    lines = text.splitlines()
    if len(lines) > limits.max_lines:
        _fail("too_many_lines", "Structure file exceeds the line-count budget")
    artifact = StructureArtifact(
        filename=filename,
        content=content,
        declared_format=declared_format,
    )
    return artifact, lines


def _number(value: str, name: str, line: int) -> float:
    try:
        parsed = float(value)
    except ValueError:
        _fail("invalid_coordinate", f"{name} must be a finite number", line)
    if not math.isfinite(parsed):
        _fail("invalid_coordinate", f"{name} must be a finite number", line)
    return parsed


def _integer(value: str, name: str, line: int) -> int:
    try:
        parsed = int(value)
    except ValueError:
        _fail("invalid_integer", f"{name} must be an integer", line)
    if parsed < 1:
        _fail("invalid_integer", f"{name} must be positive", line)
    return parsed


def _optional(value: str | None) -> str | None:
    return None if value is None or value in (".", "?") else value


def _required(value: str | None, name: str, line: int) -> str:
    parsed = _optional(value)
    if not parsed:
        _fail("missing_atom_field", f"{name} must be present", line)
    return parsed


def _element(value: str | None, line: int) -> str:
    parsed = _required(value, "element", line).upper()
    if not parsed.isascii() or not parsed.isalpha() or len(parsed) > 3:
        _fail("invalid_element", "Element must contain one to three ASCII letters", line)
    return parsed


def _occupancy(value: str | None, line: int) -> float | None:
    parsed = _optional(value)
    if parsed is None:
        return None
    number = _number(parsed, "occupancy", line)
    if not 0 <= number <= 1:
        _fail("invalid_occupancy", "Occupancy must be between 0 and 1", line)
    return number


def _atom_source(artifact: StructureArtifact, model: int, atom_id: str) -> str:
    return f"{artifact.checksum}#model:{model}/atom:{atom_id}"


def _draft(
    declared_format: Literal["pdb", "mmcif"],
    artifact: StructureArtifact,
    atoms: list[AtomSite],
    warnings: tuple[ProcessingNotice, ...] = (),
) -> StructureDraft:
    if not atoms:
        _fail("missing_coordinates", "Structure file contains no ATOM or HETATM coordinates")
    identities = [(atom.model_number, atom.atom_id) for atom in atoms]
    if len(identities) != len(set(identities)):
        _fail("duplicate_atom_id", "Atom identifiers must be unique within each model")
    return StructureDraft(
        declared_format=declared_format,
        artifact=artifact,
        atoms=tuple(atoms),
        chains=tuple(dict.fromkeys(atom.chain_id for atom in atoms)),
        model_numbers=tuple(dict.fromkeys(atom.model_number for atom in atoms)),
        warnings=warnings,
    )


def process_pdb(
    content: bytes,
    *,
    filename: str = "structure.pdb",
    limits: StructureLimits = StructureLimits(),
) -> StructureDraft:
    artifact, lines = _artifact(content, filename, "pdb", limits)
    atoms: list[AtomSite] = []
    current_model = 1
    explicit_model = False
    for line_number, line in enumerate(lines, start=1):
        record = line[:6].strip().upper()
        if record == "MODEL":
            if explicit_model and any(atom.model_number == current_model for atom in atoms):
                _fail("nested_model", "MODEL records cannot be nested", line_number)
            current_model = _integer(line[10:14].strip(), "MODEL number", line_number)
            explicit_model = True
            continue
        if record == "ENDMDL":
            explicit_model = False
            continue
        if record not in ("ATOM", "HETATM"):
            continue
        if len(atoms) >= limits.max_atoms:
            _fail("too_many_atoms", "Structure exceeds the atom-count budget", line_number)
        if len(line) < 78:
            _fail(
                "truncated_atom_record",
                "PDB ATOM/HETATM record is shorter than 78 columns",
                line_number,
            )
        atom_id = line[6:11].strip()
        atom_name = line[12:16].strip()
        residue_name = line[17:20].strip()
        residue_number = line[22:26].strip()
        element = line[76:78].strip().upper()
        if not all((atom_id, atom_name, residue_name, residue_number, element)):
            _fail("missing_atom_field", "PDB atom identity fields must be present", line_number)
        atoms.append(
            AtomSite(
                atom_id=atom_id,
                group=record,
                element=_element(element, line_number),
                atom_name=atom_name,
                alternate_id=_optional(line[16:17].strip()),
                residue_name=residue_name,
                chain_id=line[21:22].strip(),
                residue_number=residue_number,
                insertion_code=_optional(line[26:27].strip()),
                x=_number(line[30:38].strip(), "Cartn_x", line_number),
                y=_number(line[38:46].strip(), "Cartn_y", line_number),
                z=_number(line[46:54].strip(), "Cartn_z", line_number),
                occupancy=_occupancy(line[54:60].strip(), line_number),
                model_number=current_model,
                source=_atom_source(artifact, current_model, atom_id),
            )
        )
    return _draft("pdb", artifact, atoms)


def _column(
    indexes: dict[str, int],
    *names: str,
    required: bool = True,
) -> Callable[[list[str]], str | None]:
    index = next((indexes[name.lower()] for name in names if name.lower() in indexes), None)
    if index is None and required:
        _fail("missing_atom_site_column", f"Required atom_site column is missing: {names[0]}")
    return lambda row: row[index] if index is not None else None


def _atom_loop(lines: list[str]) -> tuple[list[str], list[tuple[int, list[str]]]]:
    cursor = 0
    while cursor < len(lines):
        if lines[cursor].strip().lower() != "loop_":
            cursor += 1
            continue
        cursor += 1
        columns = []
        while cursor < len(lines) and lines[cursor].lstrip().startswith("_"):
            columns.append(lines[cursor].strip())
            cursor += 1
        if not columns or not columns[0].lower().startswith("_atom_site."):
            continue
        if any(not name.lower().startswith("_atom_site.") for name in columns):
            _fail("mixed_loop_categories", "An mmCIF loop must contain one category", cursor)
        tokens: list[tuple[int, str]] = []
        while cursor < len(lines):
            stripped = lines[cursor].strip()
            lowered = stripped.lower()
            if not stripped or stripped.startswith("#"):
                cursor += 1
                if stripped.startswith("#") and tokens:
                    break
                continue
            if (
                lowered == "loop_"
                or stripped.startswith("_")
                or lowered.startswith(("data_", "save_"))
            ):
                break
            if lines[cursor].startswith(";"):
                _fail(
                    "unsupported_multiline_value",
                    "Multiline values are not supported in atom_site",
                    cursor + 1,
                )
            try:
                values = shlex.split(lines[cursor], comments=False, posix=True)
            except ValueError as exc:
                raise InputValidationError(
                    "invalid_mmcif_syntax",
                    f"Invalid quoted value at line {cursor + 1}",
                    f"line:{cursor + 1}",
                ) from exc
            tokens.extend((cursor + 1, value) for value in values)
            cursor += 1
        if len(tokens) % len(columns):
            line = tokens[-1][0] if tokens else cursor + 1
            _fail("invalid_atom_site_rows", "atom_site values do not match its columns", line)
        rows = []
        for offset in range(0, len(tokens), len(columns)):
            chunk = tokens[offset : offset + len(columns)]
            rows.append((chunk[0][0], [value for _, value in chunk]))
        return columns, rows
    _fail("missing_atom_site", "mmCIF file contains no atom_site loop")


def process_mmcif(
    content: bytes,
    *,
    filename: str = "structure.cif",
    limits: StructureLimits = StructureLimits(),
) -> StructureDraft:
    artifact, lines = _artifact(content, filename, "mmcif", limits)
    columns, rows = _atom_loop(lines)
    indexes = {name.lower(): index for index, name in enumerate(columns)}
    group = _column(indexes, "_atom_site.group_PDB")
    atom_id = _column(indexes, "_atom_site.id")
    element = _column(indexes, "_atom_site.type_symbol")
    atom_name = _column(indexes, "_atom_site.auth_atom_id", "_atom_site.label_atom_id")
    residue_name = _column(indexes, "_atom_site.auth_comp_id", "_atom_site.label_comp_id")
    chain_id = _column(indexes, "_atom_site.auth_asym_id", "_atom_site.label_asym_id")
    residue_number = _column(indexes, "_atom_site.auth_seq_id", "_atom_site.label_seq_id")
    x_value = _column(indexes, "_atom_site.Cartn_x")
    y_value = _column(indexes, "_atom_site.Cartn_y")
    z_value = _column(indexes, "_atom_site.Cartn_z")
    occupancy_value = _column(indexes, "_atom_site.occupancy", required=False)
    model_value = _column(indexes, "_atom_site.pdbx_PDB_model_num", required=False)
    alternate_id = _column(indexes, "_atom_site.label_alt_id", required=False)
    insertion_code = _column(indexes, "_atom_site.pdbx_PDB_ins_code", required=False)
    atoms = []
    for line_number, row in rows:
        if len(atoms) >= limits.max_atoms:
            _fail("too_many_atoms", "Structure exceeds the atom-count budget", line_number)
        group_name = (group(row) or "").upper()
        if group_name not in ("ATOM", "HETATM"):
            _fail("invalid_atom_group", "atom_site.group_PDB must be ATOM or HETATM", line_number)
        identifier = _required(atom_id(row), "atom_site.id", line_number)
        model_text = _optional(model_value(row))
        model = _integer(model_text, "model number", line_number) if model_text else 1
        occupancy_text = _optional(occupancy_value(row))
        atoms.append(
            AtomSite(
                atom_id=identifier,
                group=group_name,
                element=_element(element(row), line_number),
                atom_name=_required(atom_name(row), "atom name", line_number),
                alternate_id=_optional(alternate_id(row)),
                residue_name=_required(residue_name(row), "residue name", line_number),
                chain_id=_optional(chain_id(row)) or "",
                residue_number=_required(residue_number(row), "residue number", line_number),
                insertion_code=_optional(insertion_code(row)),
                x=_number(x_value(row) or "", "Cartn_x", line_number),
                y=_number(y_value(row) or "", "Cartn_y", line_number),
                z=_number(z_value(row) or "", "Cartn_z", line_number),
                occupancy=_occupancy(occupancy_text, line_number),
                model_number=model,
                source=_atom_source(artifact, model, identifier),
            )
        )
    return _draft(
        "mmcif",
        artifact,
        atoms,
        warnings=(
            ProcessingNotice(
                code="bounded_mmcif_profile",
                message="Only the atom_site coordinate category was inspected",
            ),
        ),
    )
