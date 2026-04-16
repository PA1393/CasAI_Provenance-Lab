import { LoadingState } from "@/components/ui/loading-state";

export default function RunsLoading() {
  return (
    <div className="mx-auto max-w-4xl">
      <div className="h-8 w-16 animate-pulse rounded-full bg-slate-200" />
      <div className="mt-8">
        <LoadingState />
      </div>
    </div>
  );
}
