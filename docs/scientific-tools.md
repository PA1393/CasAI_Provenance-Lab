# Scientific tool integrations

The API integrates CRISPOR, Cas-OFFinder, CRISPResso2, and inDelphi through
`app.modules.integrations`. These tools are intentionally not Python dependencies of the
main API: each has its own runtime, genome, hardware, or licensing requirements.

## Configuration

Set only the tools used by a deployment:

```env
SCIENTIFIC_TOOL_TIMEOUT_SECONDS=900
CRISPOR_COMMAND=/opt/crispor/crispor.py
CRISPOR_GENOME_DIR=/data/crispor/genomes
CAS_OFFINDER_COMMAND=/opt/cas-offinder/cas-offinder
CAS_OFFINDER_DEVICE=C
CRISPRESSO_COMMAND=/opt/crispresso/bin/CRISPResso
INDELPHI_PYTHON=/opt/indelphi/bin/python
INDELPHI_MODEL_DIR=/opt/indelphi-model
```

Cas-OFFinder needs a local FASTA/2bit genome directory and an OpenCL device. The adapter
targets the production Cas-OFFinder 2.4.1 six-column contract; it does not use the
production-incompatible v3 beta bulge format. CRISPOR needs its own indexed genome directory.
CRISPResso2 needs real FASTQ reads, an amplicon sequence, and a guide. inDelphi is launched
through a separate Python interpreter because its published models depend on old pandas and
scikit-learn versions.

## Provenance

Call an adapter through `execute_with_provenance()` from
`app.modules.provenance.service`. A successful invocation emits
`scientific_tool_completed`; a command failure emits `scientific_tool_failed` and is
re-raised. Events include:

- tool and detected version
- operation and argument vector
- input and output SHA-256 fingerprints
- duration and return status
- compact result counts
- bounded stderr diagnostics

Raw sequences and large result tables are not copied into provenance. CRISPResso sequence
arguments are redacted from the recorded command. Detailed parsed results are returned to
the caller for storage in the results domain.

The existing deterministic base-edit pipeline remains unchanged and emits its own stage
events. External adapters run only when a caller explicitly invokes them through
`execute_with_provenance()`; this layer does not silently substitute a tool or label the
deterministic engine as a third-party execution. Persisting detailed adapter results into a
versioned run plan is a later orchestration slice.
