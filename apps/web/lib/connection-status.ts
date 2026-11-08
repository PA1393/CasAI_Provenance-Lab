export type WorkspaceConnection = {
  mode: "demo" | "accounts";
  storage: "supabase" | "temporary" | "unknown";
  location: "local" | "hosted";
};

export function parseWorkspaceConnection(data: unknown, apiUrl: string): WorkspaceConnection {
  const value = data as Record<string, unknown> | null;
  if (!value || value.schema_version !== "casai.demo-capabilities.v1" ||
    (value.access_mode !== "demo" && value.access_mode !== "accounts")) {
    throw new Error("Matching backend capabilities unavailable");
  }
  const hostname = new URL(apiUrl).hostname;
  return {
    mode: value.access_mode,
    storage: value.storage_backend === "temporary" || value.storage_backend === "supabase" ? value.storage_backend : "unknown",
    location: ["localhost", "127.0.0.1", "[::1]"].includes(hostname) ? "local" : "hosted",
  };
}

export function connectionCopy(connection: WorkspaceConnection) {
  const endpoint = connection.location === "local" ? "local API" : "hosted API";
  if (connection.storage === "temporary") return {
    label: `Temporary ${connection.location === "local" ? "local " : ""}demo · connected to ${endpoint}`,
    detail: "Test records disappear when this rehearsal backend stops. Supabase is not used by this session.",
  };
  return {
    label: `Connected to ${endpoint}`,
    detail: connection.storage === "supabase"
      ? "Supabase adapter configured. API reachable; database migrations, access isolation and persistence are not verified by this indicator."
      : "Storage type was not reported. API reachable; database persistence has not been verified.",
  };
}
