import { z } from "zod";
import { requestTextDownload } from "./download";

const publicEnvSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.string().url().default("http://127.0.0.1:8000"),
});

export function getPublicEnv() {
  return publicEnvSchema.parse({
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  });
}

// The desktop build supplies a restricted native transport at this same boundary.
// Web/server rendering continues to use the standard fetch implementation.
export function fetchApi(url: string, init?: RequestInit): Promise<Response> {
  return fetch(url, init);
}

export async function saveExportText(filename: string, content: string): Promise<"requested" | "saved" | "cancelled"> {
  return requestTextDownload(filename, content);
}

export const saveFastaText = saveExportText;
export const saveFeedbackText = saveExportText;

