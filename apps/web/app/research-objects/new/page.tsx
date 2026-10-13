import { InputBundleForm } from "@/components/research-objects/input-bundle-form";
import { ParsingStatus } from "@/components/research-objects/parsing-status";
import { Eyebrow } from "@/components/ui/eyebrow";

export default function NewResearchObjectPage() {
  return (
    <section className="mx-auto max-w-5xl px-5 pb-16 pt-10 md:px-8 md:pt-14">
      <Eyebrow>Sequence intake</Eyebrow>
      <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="max-w-3xl font-serif-display text-4xl md:text-5xl">
            Review the source before it becomes a record.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-text-secondary">
            CasAI validates and normalizes the sequence in your browser, then gives you one
            final review before creating a versioned research object.
          </p>
        </div>
        <ParsingStatus />
      </div>
      <div className="mt-8 md:mt-10">
        <InputBundleForm />
      </div>
    </section>
  );
}
