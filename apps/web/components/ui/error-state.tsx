type ErrorStateProps = {
  message?: string;
};

export function ErrorState({ message = "Something went wrong." }: ErrorStateProps) {
  return (
    <div className="rounded-3xl border border-red-200 bg-red-50 px-6 py-8 text-center">
      <p className="font-medium text-red-700">Error</p>
      <p className="mt-1 text-sm text-red-600">{message}</p>
    </div>
  );
}
