# Simulation orchestration

CasAI simulation plans are typed, deterministic descriptions of transparent
computational work. They are not wet-lab protocols or molecular-dynamics claims.

The `casai.simulation-plan.v1` contract binds a plan to content-addressed research,
guide, ranking and enzyme artifacts. Draft plans never execute. An approved plan
is executable only when the research input is confirmed and every mapping input
is approved. Rejected or unresolved inputs are not silently repaired.

Stages declare a pinned engine and version, operation, required/optional policy,
dependencies and bounded scalar settings. Dependencies must point to earlier
stages, which keeps the initial plan graph deterministic and acyclic. The plan ID
hashes the canonical scientific content, including approval state and stage order.
Plans and stages are labeled explanatory; executing a plan will produce separately
labeled computed results rather than upgrading the plan into experimental evidence.

Exact engine dispatch now requires the engine identifier, version and operation
declared by each stage. There is no fallback or silent substitution. A required
stage failure stops later work and fails the execution. An optional stage failure
allows independent work to continue and produces a partial result; dependent
stages are skipped or failed according to their own requirement policy.

Adapter timeouts, subprocess exceptions, unexpected errors and invalid results
are recorded as failed stage outcomes without discarding earlier artifacts.
Unexpected diagnostics expose only the exception category, not subprocess output
or researcher data. Process-control exceptions such as interrupts still propagate.

Execution sessions retain immutable attempt lineage. Attempts move explicitly from
pending to running and then to a terminal state. Retrying a partial, failed or
cancelled attempt appends a new attempt that points to its predecessor; it does not
overwrite the prior execution, artifacts or failure explanation. Cancellation is
limited to the active attempt and requires a recorded reason.

These B6 increments define planning, approval gates, in-process orchestration and
attempt lifecycle rules. `POST /api/v1/simulation-plans` now creates an immutable
draft from an exact confirmed research version, guide map and optional ranking;
`GET /api/v1/simulation-plans/{plan_id}` reloads it with integrity checks. The API
cannot self-approve a plan or mark it executable. Approval remains a separate
review responsibility, and executable-session persistence remains a follow-up.

Current v1 session/attempt identities describe deterministic in-memory lineage,
not globally unique invocations. Before durable persistence, introduce a versioned
server-generated session nonce and session-scoped attempt IDs/idempotency rules;
do not persist v1 IDs as unique run records. See `remaining-delivery-plan.md` for
the identity and trusted-actor boundaries required before that phase.
