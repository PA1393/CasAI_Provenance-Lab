import { InputBundleForm } from "@/components/research-objects/input-bundle-form";
import { ParsingStatus } from "@/components/research-objects/parsing-status";

export default function NewResearchObjectPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-semibold text-ink">New Research Object</h1>
        <ParsingStatus />
      </div>
      <div className="mt-8">
        <InputBundleForm />
      </div>
    </div>
  );
}
