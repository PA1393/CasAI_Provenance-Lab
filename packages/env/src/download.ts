export function requestTextDownload(filename: string, content: string): "requested" {
  const url = URL.createObjectURL(new Blob([content], {
    type: filename.endsWith(".fasta") ? "text/plain;charset=utf-8" : "application/json",
  }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
  return "requested";
}
