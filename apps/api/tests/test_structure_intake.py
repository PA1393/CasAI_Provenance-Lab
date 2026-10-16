"""Offline PDB/mmCIF inspection tests; no retrieval, rendering, or simulation."""

import pytest
from pydantic import ValidationError

from app.modules.information_processor.intake import (
    IntakeInspection,
    MmcifInspectionRequest,
    PdbInspectionRequest,
    inspect_input,
)
from app.modules.information_processor.structure_parser import StructureLimits
from app.modules.information_processor.structures import StructureDraft


def _pdb_atom(
    serial: int,
    atom: str,
    residue: str,
    chain: str,
    residue_number: int,
    x: float,
    y: float,
    z: float,
    element: str,
    *,
    group: str = "ATOM",
    occupancy: float = 1.0,
) -> str:
    return (
        f"{group:<6}{serial:>5} {atom:^4} {residue:>3} {chain:1}{residue_number:>4}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}{occupancy:6.2f}{20.0:6.2f}          {element:>2}"
    )


PDB = (
    "MODEL        1\n"
    + _pdb_atom(1, "N", "ALA", "A", 1, 1.0, 2.0, 3.0, "N")
    + "\n"
    + _pdb_atom(2, "CA", "ALA", "A", 1, 2.0, 3.0, 4.0, "C")
    + "\nENDMDL\n"
)

MMCIF = """data_demo
#
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.auth_atom_id
_atom_site.auth_comp_id
_atom_site.auth_asym_id
_atom_site.auth_seq_id
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.occupancy
_atom_site.pdbx_PDB_model_num
ATOM 1 N N ALA A 1 1.000 2.000 3.000 1.00 1
HETATM 2 O O HOH B 2 4.000 5.000 6.000 0.50 1
#
"""


def test_pdb_dispatch_preserves_bytes_and_normalizes_coordinates() -> None:
    result = inspect_input(PdbInspectionRequest(content=PDB.encode(), filename="demo.pdb"))

    assert result.outcome == "accepted"
    assert isinstance(result.draft, StructureDraft)
    assert result.draft.artifact.content == PDB.encode()
    assert result.draft.artifact.filename == "demo.pdb"
    assert result.draft.executable is False
    assert result.draft.chains == ("A",)
    assert result.draft.model_numbers == (1,)
    assert result.draft.atoms[1].atom_name == "CA"
    assert result.draft.atoms[1].coordinate_units == "angstrom"


def test_mmcif_dispatch_reads_atom_site_and_labels_bounded_profile() -> None:
    result = inspect_input(MmcifInspectionRequest(content=MMCIF.encode()))

    assert result.outcome == "accepted"
    assert isinstance(result.draft, StructureDraft)
    assert result.draft.chains == ("A", "B")
    assert [atom.group for atom in result.draft.atoms] == ["ATOM", "HETATM"]
    assert result.draft.atoms[1].occupancy == 0.5
    assert result.draft.warnings[0].code == "bounded_mmcif_profile"


def test_structure_identity_ignores_line_endings_but_artifact_hash_does_not() -> None:
    lf = inspect_input(PdbInspectionRequest(content=PDB.encode()))
    crlf = inspect_input(PdbInspectionRequest(content=PDB.replace("\n", "\r\n").encode()))

    assert isinstance(lf.draft, StructureDraft)
    assert isinstance(crlf.draft, StructureDraft)
    assert lf.draft.normalized_checksum == crlf.draft.normalized_checksum
    assert lf.draft.artifact.checksum != crlf.draft.artifact.checksum


def test_missing_mmcif_coordinate_column_returns_structured_rejection() -> None:
    broken = (
        MMCIF.replace("_atom_site.Cartn_z\n", "")
        .replace(" 3.000 1.00", " 1.00")
        .replace(" 6.000 0.50", " 0.50")
    )
    result = inspect_input(MmcifInspectionRequest(content=broken.encode()))

    assert result.outcome == "rejected"
    assert result.issue is not None
    assert result.issue.code == "missing_atom_site_column"


def test_duplicate_atom_ids_in_one_model_are_rejected() -> None:
    duplicate = PDB.replace("    2", "    1", 1)
    result = inspect_input(PdbInspectionRequest(content=duplicate.encode()))

    assert result.outcome == "rejected"
    assert result.issue is not None
    assert result.issue.code == "duplicate_atom_id"


def test_structure_limits_reject_instead_of_returning_partial_atoms() -> None:
    result = inspect_input(
        PdbInspectionRequest(
            content=PDB.encode(),
            limits=StructureLimits(max_atoms=1),
        )
    )

    assert result.outcome == "rejected"
    assert result.issue is not None
    assert result.issue.code == "too_many_atoms"


@pytest.mark.parametrize(
    "inspection_request",
    [PdbInspectionRequest(content=PDB.encode()), MmcifInspectionRequest(content=MMCIF.encode())],
)
def test_structure_result_json_roundtrip_is_immutable(inspection_request) -> None:
    result = inspect_input(inspection_request)
    restored = IntakeInspection.model_validate_json(result.model_dump_json(round_trip=True))

    assert restored == result
    with pytest.raises(ValidationError, match="frozen"):
        restored.outcome = "rejected"
