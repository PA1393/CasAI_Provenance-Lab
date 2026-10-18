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

Execution sessions retain immutable attempt lineage. Attempts move explicitly from
pending to running and then to a terminal state. Retrying a partial, failed or
cancelled attempt appends a new attempt that points to its predecessor; it does not
overwrite the prior execution, artifacts or failure explanation. Cancellation is
limited to the active attempt and requires a recorded reason.

These B6 increments define planning, approval gates, in-process orchestration and
attempt lifecycle rules. Persistence and API orchestration remain separate
follow-up increments.
