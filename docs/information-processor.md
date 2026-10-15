# Information Processor contracts and validation

The next local increment adds separate bounded read/variant dataset adapters;
see [FASTQ/VCF intake and CLI usage](multi-format-intake.md). It does not change
the sequence `IntakeRequest` into an untyped catch-all file request.

This module prepares non-executable research drafts using pure functions. It is
the first intake milestone and is not connected to API routes, Supabase, the UI,
or the existing run pipeline yet. Existing research-object behavior is unchanged.

## Contracts

`apps/api/app/modules/information_processor/contracts.py` defines strict,
serializable Pydantic contracts. Unknown fields are rejected. Nested field values
and sequence records are immutable in memory; collections use tuples.

- `IntakeRequest` declares one of six input methods and optional metadata.
- `InputDetection` reports a format suggestion and candidate molecule types.
  Detection always requires confirmation. Alphabet-compatible prose and gene
  symbols cannot reliably be distinguished from sequences using letters alone.
- `FieldValue` retains a value, origin, source, optional confidence and explicit
  confirmation flag. Missing values are unresolved. AI-inferred fields cannot
  claim user confirmation.
- `MissingField` classifies a gap as required, recommended or optional and gives
  the action needed to resolve it.
- `OriginalArtifact` retains exact UTF-8 bytes, SHA-256 and byte length. Its JSON
  representation encodes the bytes as base64; it does not write a stored file.
- `SequenceRecord` separates FASTA records and retains field-level origins.
  Sequence length and SHA-256 are deterministic computed properties. Nucleotide
  and residue coordinates use the declared 1-based-inclusive convention.
- `ResearchDraft` contains the source artifact, normalized records, metadata,
  warnings and missing information. `ready_for_confirmation` does not mean
  approved or executable: all drafts remain non-executable.

## Pure entry points

`parser.detect_input(bytes)` reports FASTA, accession-like text, possible pasted
sequence or unknown input. A detection is a suggestion, not a scientific fact.

`parser.parse_sequences(bytes, input_format=..., molecule_type=...)` validates
FASTA or pasted DNA, RNA or protein. It requires FASTA headers, preserves record
order and identifiers, and rejects empty records and duplicate identifiers.
Blank lines and whole-line semicolon comments are supported in FASTA. Whitespace
within sequences is removed and lowercase letters become uppercase; the original
artifact remains unchanged. Case and whitespace normalization produce notices.

DNA and RNA accept their respective IUPAC nucleotide alphabets. Protein accepts
the standard residue letters plus B, X, Z, J, U and O. Ambiguous symbols remain
visible and produce warnings. Gap markers and protein stop markers are rejected,
not silently removed. Declared DNA rejects U; declared RNA rejects T. RNA stays
RNA unless `rna_to_dna=True` is explicitly requested with an RNA declaration.
Conversion retains the original RNA artifact and source molecule type.

`processing.process_input(IntakeRequest(...))` prepares a draft without network,
database or model calls. Local sequence input without a molecule declaration
remains an incomplete draft. Organism is recommended for local sequences; it is
required for gene resolution. Missing structure, transcript or assembly details
are never inferred from sequence headers.

Accession and gene requests remain unresolved until a later adapter retrieves
exact, versioned reference records. Supplied reference metadata is attributed to
the researcher, not to a database. Gene input exposes missing organism and
transcript selection explicitly. Written objectives are retained as draft text,
with no inferred sequence, organism or reference. Declared AI-origin sequences
are rejected on every sequence/source entry path. This metadata policy cannot
detect someone falsely attributing generated text to a researcher.

The synthetic demo fixture is identified as `casai.synthetic.sequence.v1` and
labeled explanatory with an explicit synthetic-data warning. It has no claimed
organism, reference accession or experimental evidence, and cannot be replaced
with arbitrary customer text through the demo method.

## Identity and limits

Original artifact SHA-256 covers exact bytes. Sequence SHA-256 covers normalized
letters. Draft `normalized_checksum` covers canonical JSON containing schema and
normalization versions, input method, ordered record values, identifiers,
descriptions, molecule semantics, metadata and objective. Formatting-only changes
to sequence input preserve normalized identity while changing the source artifact
hash. Meaningful metadata, molecule or record-order changes produce a new hash.
Field attribution and warnings remain separately retained; this hash does not
claim to identify an approved scientific plan or reproduce a model-assisted run.

Inputs default to a 10,000,000-byte limit and 1,000 FASTA records. Corrupt UTF-8,
unsupported control characters, invalid alphabets, format mismatches and empty
input raise `InputValidationError` with a serializable `ProcessingNotice`.

To serialize and restore an internal draft with computed properties excluded:

```python
payload = draft.model_dump_json(round_trip=True)
restored = ResearchDraft.model_validate_json(payload)
```

## Verification and next milestone

Run the offline intake tests from the repository root:

```bash
bun scripts/api-python.ts -m pytest -c pyproject.toml tests/test_input_processing.py -q
```

The next milestone adds thin detection/process/missing-information/confirmation
routes, original-artifact and draft persistence, replaceable reference adapters,
and immutable confirmed versions. It must resolve exact reference records before
calling them database-retrieved, retain reference versions and retrieval metadata,
and link provenance actors and activities to the stored artifacts. No database
migration, live reference resolver or confirmation endpoint is part of this pure
validation milestone. FASTQ and VCF use the separate bounded dataset adapters
and local CLI described in [multi-format intake](multi-format-intake.md), not
this sequence request contract. GenBank, general coordinate/assembly files,
tabular metadata, PDB/mmCIF and production objective extraction remain unsupported.
