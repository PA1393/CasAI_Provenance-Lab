type ErrorStateProps = {
  message?: string;
};

export function ErrorState({ message = "Something went wrong." }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-accent-red/40 bg-bg-card px-6 py-8 text-center">
      <p className="font-mono text-xs tracking-[0.2em] uppercase font-semibold text-accent-red">
        Error
      </p>
      <p className="mt-2 text-sm text-text">{message}</p>
    </div>
  );
}
