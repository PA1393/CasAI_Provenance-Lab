import { LoadingState } from "@/components/ui/loading-state";

export default function ResearchObjectsLoading() {
  return (
    <section className="px-8 pt-12 pb-12 max-w-7xl mx-auto">
      <div className="h-8 w-48 shimmer rounded bg-bg-card" />
      <div className="mt-10">
        <LoadingState />
      </div>
    </section>
  );
}
