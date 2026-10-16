# Bounded PDB and PDBx mmCIF structure intake

Sprint 6 adds offline inspection for user-supplied legacy PDB and PDBx/mmCIF
coordinate files. It produces immutable, non-executable drafts and does not
retrieve structures, infer missing residues, calculate bonds, render scenes, or
claim that supplied coordinates are experimentally validated.

## Entry points and contracts

- `PdbInspectionRequest` and `MmcifInspectionRequest` join the existing
  transport-neutral `inspect_input()` dispatcher.
- `process_pdb()` reads fixed-column `ATOM`, `HETATM`, `MODEL`, and `ENDMDL`
  records.
- `process_mmcif()` reads one `atom_site` loop and accepts the official author
  identifiers with label identifiers as explicit fallbacks.
- `StructureArtifact` retains the exact source bytes, filename label, declared
  format, byte length, and SHA-256 checksum.
- `AtomSite` records atom/residue identity, chain, model, Cartesian coordinates,
  occupancy, provenance source, and explicit angstrom units.
- `StructureDraft` stays `status=draft` and `executable=false`; its normalized
  checksum excludes byte formatting and provenance pointers but includes every
  normalized atom value.

## Validation boundaries

Default limits are 10 MB, 250,000 lines, and 100,000 atoms. Exceeding a limit
rejects the complete inspection; no partial structure is returned. Coordinates
must be finite, occupancy must be between zero and one, required atom identity
fields must be present, and atom identifiers must be unique within each model.
Every atom points back to the retained source artifact.

The mmCIF adapter intentionally supports only a flat `atom_site` coordinate
loop. It validates loop cardinality and required coordinate columns. Semicolon
multiline values inside `atom_site`, multiple coordinate loops, anisotropic
parameters, chemistry dictionaries, assemblies, secondary structure,
connectivity, trajectories, and arbitrary CIF categories are outside this
bounded profile. The legacy PDB adapter requires the modern element field and
does not guess it from an atom name.

Blank chain IDs are retained as blank rather than invented. Author residue
numbers remain strings because insertion/author numbering must not be silently
converted into a new coordinate system. Parsed coordinates alone do not prove
experimental origin, structural coverage, biological assembly, or suitability
for simulation.

## Verification

Run the focused adapter tests from the repository root:

```bash
bun scripts/api-python.ts -m pytest -c pyproject.toml tests/test_structure_intake.py -q
```

Format references:

- [wwPDB legacy PDB coordinate records](https://www.wwpdb.org/documentation/file-format-content/format30/sect9.html)
- [PDBx/mmCIF syntax](https://mmcif.wwpdb.org/docs/tutorials/mechanics/pdbx-mmcif-syntax.html)
- [PDBx/mmCIF atom site coordinates](https://mmcif.wwpdb.org/docs/tutorials/content/atomic-description.html)
- [PDB to PDBx/mmCIF coordinate correspondence](https://mmcif.rcsb.org/docs/pdb_to_pdbx_correspondences.html)
