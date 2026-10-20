import { InputBundleForm } from "@/components/research-objects/input-bundle-form";
import { ParsingStatus } from "@/components/research-objects/parsing-status";

export default function NewResearchObjectPage() {
  return (
    <section className="mx-auto max-w-5xl px-4 pb-16 pt-7 sm:px-6 lg:px-8 lg:pt-9">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-accent">Sequence intake</p>
          <h1 className="mt-1 max-w-3xl font-serif-display text-3xl text-text sm:text-4xl">
            Add a research input
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary sm:text-base">
            Choose a FASTA file, review the detected details, then save the research input.
          </p>
        </div>
        <ParsingStatus />
      </div>
      <div className="mt-7">
        <InputBundleForm />
      </div>
    </section>
  );
}
