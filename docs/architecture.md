# Architecture

## Principles

- Keep the frontend thin
- Keep business logic in the FastAPI backend
- Use a modular-monolith backend shape
- Avoid premature shared domain packages
- Favor readability over abstraction

## Current Boundaries

- `apps/web` handles routes, UI, and backend API consumption
- `apps/api` handles API routes and domain services
- `packages/config` holds shared TypeScript config
- `packages/env` validates frontend runtime configuration

## Early Domains

- runs
- uploads
- provenance
- compare
- export
- pipeline

