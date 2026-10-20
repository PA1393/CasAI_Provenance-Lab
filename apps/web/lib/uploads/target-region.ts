export function parseTargetRegion(startText: string, endText: string, sequenceLength: number): [number, number] | undefined {
  if (!startText && !endText) return undefined;
  if (!/^\d+$/.test(startText) || !/^\d+$/.test(endText)) {
    throw new Error("Enter both target coordinates as whole numbers.");
  }
  const start = Number(startText);
  const end = Number(endText);
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end < start || end > sequenceLength) {
    throw new Error(`Use 1-based inclusive coordinates from 1 to ${sequenceLength.toLocaleString()}, with the end at or after the start.`);
  }
  return [start, end];
}
