export const MAX_UPLOAD_BYTES = 10_000_000;

const FASTA_EXTENSIONS = new Set(["fasta", "fa", "fna"]);
const IUPAC_NUCLEOTIDES = new Set("ACGTUNRYSWKMBDHV");

export type UploadIssue = {
  severity: "error" | "warning";
  message: string;
};

export type FastaReview = {
  format: "fasta" | "unsupported";
  sequence: string;
  sequenceLength: number;
  recordCount: number;
  gcContent: number;
  ambiguousBases: number;
  preview: string;
  issues: UploadIssue[];
  ready: boolean;
};

export function canReviewUpload(
  file: { name: string } | null,
  review: FastaReview | null,
  reading: boolean,
): boolean {
  return !!file && !!review?.ready && !reading;
}

function extensionOf(filename: string): string {
  return filename.split(".").pop()?.toLowerCase() ?? "";
}

export function inspectFastaUpload(
  filename: string,
  size: number,
  text: string,
): FastaReview {
  const issues: UploadIssue[] = [];
  const format = FASTA_EXTENSIONS.has(extensionOf(filename)) ? "fasta" : "unsupported";

  if (format === "unsupported") {
    issues.push({
      severity: "error",
      message: "This intake currently accepts .fasta, .fa, and .fna files.",
    });
  }
  if (size > MAX_UPLOAD_BYTES) {
    issues.push({
      severity: "error",
      message: `The file is larger than the ${MAX_UPLOAD_BYTES / 1_000_000} MB limit.`,
    });
  }
  if (!text.trim()) {
    issues.push({ severity: "error", message: "The selected file is empty." });
  }

  const lines = text.split(/\r?\n/);
  const headers = lines.filter((line) => line.trimStart().startsWith(">"));
  const sequence = lines
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith(">") && !line.startsWith(";"))
    .join("")
    .toUpperCase()
    .replaceAll("U", "T");

  if (text.trim() && !sequence) {
    issues.push({ severity: "error", message: "The file contains no sequence bases." });
  }

  const invalid = [...new Set(sequence)].filter((base) => !IUPAC_NUCLEOTIDES.has(base));
  if (invalid.length) {
    issues.push({
      severity: "error",
      message: `Invalid sequence characters: ${invalid.sort().join(", ")}.`,
    });
  }
  if (sequence && headers.length === 0) {
    issues.push({
      severity: "warning",
      message: "No FASTA header was found. CasAI will treat this as one unnamed record.",
    });
  }
  if (headers.length > 1) {
    issues.push({
      severity: "warning",
      message: `${headers.length} records will be concatenated into one target sequence.`,
    });
  }

  const canonicalLength = [...sequence].filter((base) => "ACGT".includes(base)).length;
  const gcBases = [...sequence].filter((base) => base === "G" || base === "C").length;
  const ambiguousBases = sequence.length - canonicalLength;

  return {
    format,
    sequence,
    sequenceLength: sequence.length,
    recordCount: Math.max(headers.length, sequence ? 1 : 0),
    gcContent: canonicalLength ? gcBases / canonicalLength : 0,
    ambiguousBases,
    preview: sequence.slice(0, 96),
    issues,
    ready: !issues.some((issue) => issue.severity === "error"),
  };
}
