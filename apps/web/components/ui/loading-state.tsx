export function LoadingState({ count = 3 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="shimmer h-32 rounded-lg border border-border bg-bg-card"
        />
      ))}
    </div>
  );
}
