import { getPublicEnv } from "@casai/env";

export type RunSummary = {
  id: string;
  name: string;
  status: string;
  pipeline: string;
  createdAt: string;
};

type RunsResponse = {
  items: RunSummary[];
};

export async function fetchRuns(): Promise<RunSummary[]> {
  const { NEXT_PUBLIC_API_BASE_URL } = getPublicEnv();

  const response = await fetch(`${NEXT_PUBLIC_API_BASE_URL}/api/v1/runs`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch runs: ${response.status}`);
  }

  const data = (await response.json()) as RunsResponse;
  return data.items;
}
