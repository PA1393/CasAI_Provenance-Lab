import Link from "next/link";
import { getResearchObject } from "@/lib/api/client";
import { ResearchObjectSummary } from "@/components/research-objects/research-object-summary";
import { ErrorState } from "@/components/ui/error-state";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function ResearchObjectPage({ params }: Props) {
  const { id } = await params;

  let researchObject;
  try {
    researchObject = await getResearchObject(id);
  } catch {
    return (
      <div className="mx-auto max-w-3xl">
        <Link href="/research-objects" className="text-sm text-slate-500 hover:text-accent">
          ← Research Objects
        </Link>
        <div className="mt-6">
          <ErrorState message={`Could not load research object: ${id}`} />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-start justify-between">
        <div>
          <Link href="/research-objects" className="text-sm text-slate-500 hover:text-accent">
            ← Research Objects
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-ink">Research Object</h1>
        </div>
        <Link
          href="/runs"
          className="inline-flex rounded-full border border-accent px-5 py-2.5 text-sm font-semibold text-accent transition hover:bg-accentSoft"
        >
          Start Run
        </Link>
      </div>
      <div className="mt-8">
        <ResearchObjectSummary researchObject={researchObject} />
      </div>
    </div>
  );
}
