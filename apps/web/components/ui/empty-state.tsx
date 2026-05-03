import Link from "next/link";

type EmptyStateProps = {
  message: string;
  actionLabel?: string;
  actionHref?: string;
};

export function EmptyState({ message, actionLabel, actionHref }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-bg-card/50 py-20 text-center">
      <p className="text-muted">{message}</p>
      {actionLabel && actionHref && (
        <Link
          href={actionHref}
          className="mt-6 inline-flex font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded bg-text text-bg hover:bg-accent transition-colors"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
