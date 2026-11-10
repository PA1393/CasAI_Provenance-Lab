import type { Run, ProvenanceEvent } from "../../lib/api/client";
import { failureStage, runFailure } from "../../lib/run-failure";

export function RunFailurePanel({ run, events }: { run: Run; events?: ProvenanceEvent[] }) {
  const issue = runFailure(run, events);
  if (!issue) return null;
  return <section role="status" className="mt-5 rounded-xl border border-accent-amber/40 bg-bg-card p-5">
    <h2 className="text-lg font-semibold">Stopped during {failureStage(issue.stage, issue.code)}</h2>
    <p className="mt-3 text-sm leading-6">{issue.message}</p>
    {issue.details?.length ? <ul className="mt-3 list-disc space-y-2 pl-5 text-sm">{issue.details.slice(0, 10).map((detail, index) => <li key={index}>{detail}</li>)}</ul> : null}
    <p className="mt-3 text-sm leading-6 text-text-secondary"><span className="font-semibold">Next step: </span>{issue.next_step}</p>
    <p className="mt-3 font-mono text-xs text-muted">Stage: {issue.stage} · Reason: {issue.code}</p>
  </section>;
}
