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

This first B6 increment defines planning and approval gates only. Engine
availability, attempts, retries, cancellation, persistence and API orchestration
remain separate follow-up increments.
