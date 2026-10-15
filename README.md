# CasAI Provenance Lab

CasAI Provenance Lab is a research software platform for CRISPR/base-editing workflows. This repository is a clean restart focused on a lightweight, production-minded scaffold that a student team can understand and extend safely.

## Quick Start

### Install dependencies

```bash
bun install
```

### Run the web app

```bash
bun run dev:web
```

### Set up the backend virtual environment

Windows PowerShell:

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
cd ../..
```

macOS/Linux:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
cd ../..
```

### Run the backend

```bash
bun run dev:api
```

### Run checks

```bash
bun run check:web
bun run check:api
```

## Monorepo Structure

- `apps/web` - Next.js App Router frontend
- `apps/api` - FastAPI backend
- `packages/config` - shared TypeScript/tooling config
- `packages/env` - shared frontend env helpers
- `docs` - architecture and setup notes
- `test-fixtures` - sample fixture storage for early development

## Requirements

- Bun 1.3+
- Python 3.12

## Getting Started

The root API scripts use the backend interpreter at `apps/api/.venv` directly.
They do not use a repo-root `.venv` or whichever `python` happens to be on `PATH`.

The frontend expects the backend at `http://127.0.0.1:8000` by default.

## Information Processor milestone

The new backend intake module provides strict contracts, record-preserving FASTA
and pasted-sequence validation, declared DNA/RNA/protein handling, field origins,
original-artifact checksums and incomplete research drafts. It remains separate
from the current API and UI until the persistence/confirmation milestone.

See [Information Processor contracts and validation](docs/information-processor.md)
for supported input policies, limitations and the targeted test command.

The next local build set adds bounded FASTQ/VCF inspection, gzip limits, paired
read validation, exact supplied-FASTA REF checks, and a local command-line entry
point. See [multi-format intake and usage](docs/multi-format-intake.md).
This remains independent of API/UI persistence and does not add a desktop
installer or a physical simulation engine.
