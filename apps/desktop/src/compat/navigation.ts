import { useSyncExternalStore } from "react";

export function routePath(hash: string): string {
  const path = hash.replace(/^#/, "") || "/";
  if (!path.startsWith("/") || path.startsWith("//") || /[\\\r\n]/.test(path)) return "/";
  return path;
}

const listeners = new Set<() => void>();
let revision = 0;
function notify() {
  revision += 1;
  for (const listener of listeners) listener();
}
if (typeof window !== "undefined") window.addEventListener("hashchange", notify);

export function usePathname(): string {
  useSyncExternalStore((listener) => {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, () => revision);
  return routePath(window.location.hash);
}

export function useRouter() {
  return {
    push(path: string) {
      if (routePath(`#${path}`) !== path) throw new Error("Only internal routes are supported");
      window.location.hash = path;
    },
    refresh: notify,
    back: () => window.history.back(),
  };
}

export function useRefreshRevision(): number {
  return useSyncExternalStore((listener) => {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, () => revision);
}
