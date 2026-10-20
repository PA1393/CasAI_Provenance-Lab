"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";
const storageKey = "casai-theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
    function sync(event: StorageEvent) {
      if (event.key !== storageKey) return;
      const next = event.newValue === "dark" ? "dark" : "light";
      document.documentElement.dataset.theme = next;
      setTheme(next);
    }
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);
  function select(next: Theme) {
    document.documentElement.dataset.theme = next;
    setTheme(next);
    try { localStorage.setItem(storageKey, next); } catch {
      // Theme switching also works when persistent storage is unavailable.
    }
  }
  return (
    <div aria-label="Appearance" role="group" className="inline-flex shrink-0 rounded-lg border border-border bg-bg-card p-1">
      {(["light", "dark"] as const).map((mode) => (
        <button key={mode} type="button" aria-label={`${mode === "light" ? "Light" : "Dark"} mode`} aria-pressed={theme === mode} title={`${mode === "light" ? "Light" : "Dark"} mode`} onClick={() => select(mode)} className={`grid h-9 w-11 place-items-center rounded-md transition-colors ${theme === mode ? "bg-accent-soft text-accent" : "text-text-secondary hover:bg-bg-sunken"}`}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5" aria-hidden="true">
            {mode === "light" ? <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></> : <path d="M20.5 13.3A8.6 8.6 0 0 1 10.7 3.5a8.6 8.6 0 1 0 9.8 9.8Z" />}
          </svg>
        </button>
      ))}
    </div>
  );
}
