# Build set 2: bounded local FASTQ and VCF inspection

Implemented after the milestone-1 FASTA/pasted-sequence foundation. This is an
increment of the expanded intake plan, **not completion of the original
milestone 2 API/persistence/confirmation work**.

## What works

- FASTA rejects Unicode sequence separators before they can silently disappear.
  Whitespace notices now describe actual sequence source characters.
- `detect_dataset` suggests FASTQ/VCF from the first decoded header and always
  requires confirmation. Detection does not validate the entire file.
- `process_fastq` retains single-end and two-file paired-end reads separately.
  Wrapped sequence/quality lines, LF/CRLF, repeated identifiers, lowercase
  normalization, IUPAC DNA letters, and printable ASCII qualities are supported.
  Quality lengths, mate counts, IDs/order and common mate-direction labels are
  checked. Duplicate read IDs are not merged. Phred+33 must be explicitly
  declared; absent declarations remain unresolved, and other quality dialects
  are rejected rather than guessed or silently converted.
- `process_vcf` inspects a restricted literal-allele profile of VCF 4.2–4.5:
  fixed columns, sample names, positive positions, finite nonnegative QUAL,
  filters, multiallelic REF/ALT, simple haploid/polyploid genotypes, missing
  alleles, and uniform phased/unphased separators. Alleles are uppercase with
  visible normalization notices. Sample columns are preserved independently;
  selecting a sample does not discard others or reconstruct a haplotype.
- INFO, metadata lines and non-GT FORMAT values are retained but their header
  schemas, types/cardinalities and biological meaning are **not validated or
  interpreted**. Passing inspection is not full VCF specification compliance.
- Optional uncompressed reference FASTA checks exact contig IDs, coordinates and
  REF strings, failing on absent/mismatching/truncated reference sequence.
  `reference_checked` means these local REF comparisons passed, not that a
  researcher-supplied assembly label was independently verified.
- Original bytes (including gzip) are retained in frozen `DatasetArtifact`s.
  Each read/variant points to a retained artifact checksum plus record/line.
  Scientific payload checksums are separate from original-byte checksums;
  compression and case formatting do not alter normalized read identity.
  Checked reference identity uses normalized contig sequences.
- Every result is an immutable `DatasetDraft`, `status=draft`,
  `executable=False`. No alignment, assembled source sequence, experimental
  validation, efficacy score or automatic confirmation is produced.

## Module and function map

- `datasets.py`: `DatasetArtifact`, `ReadRecord`, `SampleCall`, `VariantRecord`,
  `DatasetDraft`; frozen contracts, role/source validators, byte/count/scientific
  checksum properties. Record fields inherit their `file_extracted` record
  origin/source; supplied selections use `FieldValue` attribution.
- `dataset_parser.py`: `DatasetLimits`, `DatasetDetection`, `_artifact`, `_lines`,
  `detect_dataset`, `_fastq_records`, `_pair_identity`, `process_fastq`, `_genotype`,
  `process_vcf`, and metadata/error helpers. Parsing is pure and has no network,
  file-write, database or model-call dependency.
- `cli.py`: `_read` and `main`; bounded local reads and JSON inspection summaries.
- Tests: malformed records, compression budgets/corruption, pairing/genotypes,
  reference mismatches, immutable JSON roundtrips, checksums, CLI and FASTA
  regression cases. Synthetic examples live in `test-fixtures/intake/`.

## Local command-line usage

From `apps/api`, with its existing virtual environment:

```bash
.venv/bin/python -m app.modules.information_processor.cli --format fastq \
  --input ../../test-fixtures/intake/reads-r1.fastq \
  --mate ../../test-fixtures/intake/reads-r2.fastq \
  --sample synthetic_sample --quality-encoding phred33

.venv/bin/python -m app.modules.information_processor.cli --format vcf \
  --input ../../test-fixtures/intake/variants.vcf \
  --reference ../../test-fixtures/intake/reference.fasta \
  --assembly synthetic_demo --sample synthetic_sample
```

CLI summaries omit original byte content, reads and variant/genotype payloads.
They include artifact labels/hashes, sample selections, counts, warnings, missing
fields and normalized identity. This is intentionally a summary, not a complete
`DatasetDraft` export. The Python functions return the full typed draft with
original artifacts. Source files are never modified or uploaded. Summaries still
contain sample labels, filenames and VCF headers; they are not anonymized exports.

Exit 0 means inspection returned a draft (which can still have missing fields).
Exit 2 means invalid arguments, inaccessible input, or structured rejection.
The CLI reports structured parsing errors without an application stack trace.

## Resource and format boundaries

Default **per-file** limits: 10,000,000 original bytes; 10,000,000 decoded bytes;
200,000 bytes per line; 10,000 lines; 1,000 records; gzip expansion ratio at most 100.
Paired FASTQ can therefore return up to 2,000 reads from two 1,000-record files.
The reference FASTA has its own byte/record budgets. `DatasetLimits` exposes
positive integer overrides for Python callers; the CLI uses safe defaults.

Gzip is decoded line-by-line under limits and rejects truncated/corrupt streams.
This avoids unbounded whole-file decompression, but originals and parsed records
are still retained in bounded memory. Exceeding a limit rejects the file; it
never returns a silent partial dataset. Large production read datasets need a
future streaming record store and durable artifact handles—not just raised
in-memory limits. File imports currently support LF/CRLF, not standalone CR.

VCF symbolic/structural alleles, breakends, spanning-deletion `*`, mixed-phase or
leading-phase GT syntax, telomeric POS=0, and old versions outside 4.2–4.5 are
unsupported in this profile. BCF, indexed queries, gzip reference FASTA, BAM/CRAM,
GenBank, genomic annotations, Sanger traces and structure/trajectory intake
remain planned. Named FORMAT fields other than GT are preserved as strings;
missing trailing sample fields are explicit `.` values, never numeric zero.

Missing sample identity, quality encoding, assembly or exact reference is
exposed where applicable. A correct REF match alone is not permission to edit
and does not remove the need for confirmation/versioning.

## Integration still outstanding

This intake increment adds no API route, upload UI, database migration, durable
project store, reference retrieval, approved-version workflow, desktop installer
or physical simulation. Existing legacy routes and mock fields are not
silently connected to these adapters. The next integration increment should
add artifact persistence and the intake API/confirmation boundary before UI
adoption; desktop packaging remains a separate tested deliverable.

## Format references

- [FASTQ quality and wrapping conventions](https://biopython.org/docs/latest/api/Bio.SeqIO.QualityIO.html)
- [VCF specification](https://samtools.github.io/hts-specs/VCFv4.5.pdf)
