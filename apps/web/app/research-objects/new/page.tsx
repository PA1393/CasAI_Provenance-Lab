import { InputBundleForm } from "@/components/research-objects/input-bundle-form";
import { ParsingStatus } from "@/components/research-objects/parsing-status";
import { Eyebrow } from "@/components/ui/eyebrow";

export default function NewResearchObjectPage() {
  return (
    <section className="px-8 pt-12 pb-12 max-w-3xl mx-auto">
      <Eyebrow>──── LAYER 1 + LAYER 2 / INGEST + RESEARCH OBJECT</Eyebrow>
      <div className="mt-4 flex items-center justify-between gap-4">
        <h1 className="font-serif-display text-4xl md:text-5xl">
          New <span className="italic text-accent">Research Object.</span>
        </h1>
        <ParsingStatus />
      </div>
      <p className="mt-4 text-muted max-w-2xl">
        Upload your gene sequence inputs. We will validate, hash, and normalize them into a
        canonical, immutable bundle.
      </p>
      <div className="mt-10">
        <InputBundleForm />
      </div>
    </section>
  );
}
