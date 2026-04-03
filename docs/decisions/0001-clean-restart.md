# Decision 0001: Clean Restart

We are intentionally rebuilding Provenance Lab from scratch with a minimal scaffold.

## Reasons

- The previous attempt accumulated Docker complexity
- Repository structure drift made ownership unclear
- Dependency conflicts slowed development
- Integration work was incomplete and hard to reason about

## Decision

Start with a Turborepo monorepo containing:

- `apps/web`
- `apps/api`
- `packages/config`
- `packages/env`

Defer Docker, auth, database integration, orchestration tooling, and microservices.

