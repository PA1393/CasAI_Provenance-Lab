export function exportNotice(result: "requested" | "saved" | "cancelled", previewAvailable = true): string {
  if (result === "cancelled") return "Save cancelled. No file was written.";
  if (result === "saved") return "Checksums verified. The desktop app confirmed the package was written to your chosen file.";
  return "Checksums verified. Browser download requested—not a confirmed save. Check Downloads for the JSON file. " + (previewAvailable
    ? "If it is missing, use the verified JSON fallback below."
    : "The JSON is too large for the manual preview. If it is missing, retry in the desktop app or a browser that permits downloads.");
}
