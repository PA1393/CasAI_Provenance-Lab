import { z } from "zod";

const publicEnvSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.string().url().default("http://127.0.0.1:8000"),
});

export function getPublicEnv() {
  return publicEnvSchema.parse({
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  });
}

