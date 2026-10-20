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

## Current integration status

Legacy research objects and runs use Supabase. New confirmed research versions,
guide maps, draft simulation plans and scene manifests use the immutable local
workspace. The UI currently consumes the legacy research-object/run endpoints.
These are distinct storage and identity boundaries; connecting them requires an
explicit persistence adapter and migration, not a client-side type cast.

The web interface shares one layout and CSS theme-token system across pages.
Desktop currently wraps a development URL; production packaging is unfinished.
See [the combined delivery plan](remaining-delivery-plan.md) for the verified
gaps and integration order, including the work transferred from contributor two.

## Early Domains

- runs
- uploads
- provenance
- compare
- export
- pipeline

