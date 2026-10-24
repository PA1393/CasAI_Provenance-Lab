"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { saveFastaText } from "@casai/env";
import { getConfirmedFasta, prepareConfirmedRunInput } from "@/lib/api/client";
import { verifyConfirmedFasta, type SequenceDraft } from "@/lib/intake";

type Props = {
  versionId: string; records: SequenceDraft["records"]; busy: boolean;
  perform: (operation: () => Promise<void>) => Promise<void>;
  onNotice: (message: string) => void;
};

export function ConfirmedInputActions({ versionId, records, busy, perform, onNotice }: Props) {
  const router = useRouter();
  const [selected, setSelected] = useState(records.length === 1 ? records[0].record_id : "");
  const [name, setName] = useState("Confirmed sequence input");
  const record = records.find(item => item.record_id === selected);
  const runnable = record?.molecule_type === "DNA" && record.sequence_length <= 5_000;
  return <section aria-label="Confirmed input actions" className="space-y-3 border-t border-border pt-4">
    <h3 className="font-semibold">Use your confirmed input</h3>
    <p>The FASTA download preserves all records, normalized sequences, source references and record checksums. The current run engine takes one unambiguous DNA record of up to 5,000 bases.</p>
    <label className="block">Record for run setup<select disabled={busy} className="mt-1 w-full rounded border border-border bg-bg-card p-2" value={selected} onChange={event => setSelected(event.target.value)}>
      <option value="">Choose a record</option>{records.map(item => <option key={item.record_id} value={item.record_id}>{item.record_id} · {item.molecule_type} · {item.sequence_length} bases/residues</option>)}
    </select></label>
    <label className="block">Run input name<input disabled={busy} value={name} maxLength={200} onChange={event => setName(event.target.value)} className="mt-1 w-full rounded border border-border bg-bg-card p-2" /></label>
    <div className="flex flex-wrap gap-3">
      <button type="button" disabled={busy || !runnable || !name.trim()} className="rounded-lg bg-accent px-4 py-2 font-semibold text-bg disabled:opacity-40" onClick={() => void perform(async () => {
        const input = await prepareConfirmedRunInput(versionId, selected, name.trim());
        router.push(`/research-objects/${input.research_object_id}`);
      })}>Use in a run</button>
      <button type="button" disabled={busy} className="rounded-lg border border-border px-4 py-2 font-semibold disabled:opacity-40" onClick={() => void perform(async () => {
        const result = await getConfirmedFasta(versionId);
        await verifyConfirmedFasta(result, versionId);
        const saved = await saveFastaText(result.filename, result.content);
        onNotice(saved === "cancelled" ? "Save cancelled; no file was written." : saved === "saved" ? "Normalized FASTA saved. Checksum verified." : "Normalized FASTA download requested. Checksum verified.");
      })}>Download normalized FASTA</button>
    </div>
    <p className="text-xs text-muted">Use in a run prepares an input and opens run setup; it does not submit an analysis. Repeated preparation reopens the same record. Name changes apply only to the first preparation. Neither download nor confirmation validates biological accuracy.</p>
  </section>;
}
