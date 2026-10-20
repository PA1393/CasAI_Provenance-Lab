# CasAI Provenance Lab - Repository Rules

## Product
- Company: CasAI
- Product: Provenance Lab

## Goal
Provenance Lab is a research software platform for CRISPR/base-editing workflows.
It helps researchers create, track, compare, and understand computational runs before lab validation.

## Current Phase
We are extending the existing concept demo incrementally.
Preserve working flows and complete small, verified integration milestones.
Do not overbuild.
Current coverage and remaining delivery scope are recorded in
`docs/remaining-delivery-plan.md`.

## Architecture
- Turborepo monorepo
- apps/web = Next.js App Router frontend
- apps/api = FastAPI backend
- packages/config = shared TS/tooling config
- packages/env = shared env helpers/validation
- docs/ at root
- test-fixtures/ at root

## Tech Stack
- Next.js
- React
- TypeScript
- Tailwind CSS
- Bun
- Turborepo
- FastAPI
- Uvicorn
- Python 3.12

## Explicitly Excluded For Now
- No Docker
- No auth
- No additional database platform; preserve the existing Supabase integration
- Local immutable workspace storage and Supabase are distinct boundaries until
  an explicit persistence adapter connects them
- No Prefect
- No microservices
- No over-engineering

## Backend Direction
- FastAPI is the main domain API
- Keep business logic in the backend
- Frontend should consume backend APIs
- Use a modular-monolith structure

## Frontend Direction
- Keep UI minimal and clean
- Do not add unnecessary UI libraries
- Focus on clear file organization and maintainability
- Reuse the shared navigation, layout and light/dark theme tokens on every screen
- Label heuristics and explanatory scenes accurately; never fabricate measurements

## Early Product Domains
These should be reflected in structure, even if not fully implemented:
- runs
- uploads
- provenance
- compare
- export
- pipeline

## Coding Expectations
- Prefer simple, readable code
- Add comments only where they improve clarity
- Keep naming consistent
- Avoid unnecessary abstractions
- Favor starter scaffolding over premature optimization
