# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run both servers (dev):**
```bash
bun run dev:web   # Next.js on :3000
bun run dev:api   # FastAPI on :8000
```

**Frontend:**
```bash
bun run check:web          # typecheck + lint + build
cd apps/web && npm run typecheck
cd apps/web && npm run lint
```

**Backend:**
```bash
bun run check:api                                           # lint + test
python -m uvicorn app.main:app --reload --port 8000        # dev server (from apps/api)
python -m pytest -c apps/api/pyproject.toml apps/api/tests # run all tests
python -m pytest apps/api/tests/test_runs.py               # single test file
python -m ruff check apps/api                              # lint only
```

**Build all:**
```bash
bun run build
```

## Environment Setup

**Backend** — create `apps/api/.env`:
```
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
```

**Frontend** — optional `apps/web/.env.local`:
```
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Architecture

Turborepo monorepo. Frontend calls the backend REST API; the backend owns all business logic and talks to Supabase directly (service key never reaches the browser).

```
apps/web/     Next.js 15 App Router — routes, UI, API consumption only
apps/api/     FastAPI — domain logic, REST routes (/api/v1/...), Supabase client
packages/
  config/     Shared TypeScript/ESLint/tooling config
  env/        Frontend runtime env validation (Zod)
docs/         Architecture and setup notes
test-fixtures/ Sample data
```

**Backend layout (`apps/api/app/`):**
- `main.py` — app factory, router registration
- `core/config.py` — Pydantic settings (reads `.env`)
- `routers/` — one file per domain (runs, research_objects, etc.)
- `services/` — business logic called by routers
- `db/` — Supabase client initialization

**Frontend layout (`apps/web/app/`):**
- App Router pages under domain folders: `/runs`, `/research-objects`
- `lib/api.ts` — typed fetch helpers for backend calls
- `components/` — shared UI components

**API versioning:** all routes are prefixed `/api/v1/`.

**Supabase tables:** `runs`, `research_objects`, `provenance`, `results`.

## Key Principles (from RULES.md / docs/architecture.md)

- Keep the frontend thin — business logic lives in FastAPI, not Next.js
- Modular-monolith backend shape; no microservices
- Favor readability over abstraction; avoid premature optimization
- No Docker, no auth, no Prefect in scope currently
- Do not overbuild — clean scaffold over feature completeness

## Domains in Scope

`runs` · `uploads` · `provenance` · `compare` · `export` · `pipeline`
