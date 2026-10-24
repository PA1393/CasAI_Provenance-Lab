export type IntakeMethod = "fasta" | "pasted_sequence" | "accession" | "gene" | "demo" | "objective";
export type Notice = { code: string; message: string };
export type Gap = { field: string; requirement: string; reason: string; action: string };
export type SequenceDraft = {
  kind: "sequence"; artifact_checksum: string; normalized_checksum: string;
  ready_for_confirmation: boolean; field_origins: Record<string, string>;
  records: { record_id: string; molecule_type: string | null; sequence_length: number; checksum: string }[];
  warnings: Notice[]; missing_fields: Gap[];
};
export type StoredDraft = { outcome: "accepted"; draft_id: string; draft: SequenceDraft };
export type Confirmation = { version_id: string; approved_by: string; executable: boolean };
export type ConfirmedFasta = {
  schema_version: "casai.confirmed-fasta.v1"; version_id: string; filename: string;
  content: string; byte_length: number; checksum: string; normalized_checksum: string;
  original_artifact_checksum: string; record_count: number; claim_type: string;
  warning_codes: string[];
};

export async function verifyConfirmedFasta(value: ConfirmedFasta, versionId: string): Promise<void> {
  if (!/^sha256:[0-9a-f]{64}$/.test(versionId) ||
      value.schema_version !== "casai.confirmed-fasta.v1" || value.version_id !== versionId ||
      value.filename !== `casai-confirmed-${versionId.slice(7)}.fasta` ||
      typeof value.content !== "string" || !value.content.startsWith(">")) {
    throw new Error("FASTA package does not match this confirmed version.");
  }
  const bytes = new TextEncoder().encode(value.content);
  if (bytes.length > 12_000_000) throw new Error("FASTA exceeds the download limit.");
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  const digest = "sha256:" + Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
  if (value.checksum !== digest || value.byte_length !== bytes.length) throw new Error("FASTA integrity check failed. Nothing was saved.");
}
export type DatasetInspection = {
  outcome: "accepted";
  draft: { kind: "dataset"; executable: false; record_count: number; normalized_checksum: string;
    warnings: Notice[]; missing_fields: Gap[]; reference_checked: boolean; data_role: string };
};
export const INPUT_BYTE_LIMIT = 10_000_000;
export function validateTextInput(content: string) {
  if (!content.trim()) throw new Error("Choose a nonempty input first.");
  if (new TextEncoder().encode(content).byteLength > INPUT_BYTE_LIMIT) throw new Error("Input exceeds 10 MB.");
}
export function confirmationBody(draft: SequenceDraft, actor: string, acknowledged: boolean) {
  if (!draft.ready_for_confirmation) throw new Error("Resolve required fields before confirmation.");
  if (!actor.trim()) throw new Error("Provide an attribution label (not an authenticated identity).");
  if (draft.warnings.length && !acknowledged) throw new Error("Acknowledge all warnings before confirmation.");
  return { expected_normalized_checksum: draft.normalized_checksum,
    expected_artifact_checksum: draft.artifact_checksum, actor_id: actor.trim(), decision: "approve",
    acknowledged_warning_codes: [...new Set(draft.warnings.map(warning => warning.code))].sort() };
}
