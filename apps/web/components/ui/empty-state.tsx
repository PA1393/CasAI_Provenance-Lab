import Link from "next/link";

type EmptyStateProps = {
  message: string;
  actionLabel?: string;
  actionHref?: string;
};

export function EmptyState({ message, actionLabel, actionHref }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white/60 py-20 text-center">
      <p className="text-slate-500">{message}</p>
      {actionLabel && actionHref && (
        <Link
          href={actionHref}
          className="mt-4 inline-flex rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
