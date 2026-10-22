export type Theme = "light" | "dark";
export const THEME_STORAGE_KEY = "casai-theme";

export function resolveTheme(saved: string | null, systemDark: boolean): Theme {
  return saved === "light" || saved === "dark" ? saved : systemDark ? "dark" : "light";
}

// Run before painting; storage denial must not prevent the OS preference fallback.
export const THEME_BOOTSTRAP = `(()=>{let saved=null;try{saved=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)})}catch{}document.documentElement.dataset.theme=(${resolveTheme.toString()})(saved,window.matchMedia("(prefers-color-scheme: dark)").matches)})()`;
