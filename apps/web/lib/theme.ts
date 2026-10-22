export type Theme = "light" | "dark";
export const THEME_STORAGE_KEY = "casai-theme";

const UNSAFE_JS_CHAR_MAP: Record<string, string> = {
  "<": "\\u003C",
  ">": "\\u003E",
  "/": "\\u002F",
  "\\": "\\\\",
  "\b": "\\b",
  "\f": "\\f",
  "\n": "\\n",
  "\r": "\\r",
  "\t": "\\t",
  "\0": "\\0",
  "\u2028": "\\u2028",
  "\u2029": "\\u2029",
};

function escapeUnsafeJsChars(value: string): string {
  return value.replace(/[<>/\\\b\f\n\r\t\0\u2028\u2029]/g, (ch) => UNSAFE_JS_CHAR_MAP[ch] ?? ch);
}

export function resolveTheme(saved: string | null, systemDark: boolean): Theme {
  return saved === "light" || saved === "dark" ? saved : systemDark ? "dark" : "light";
}

// Run before painting; storage denial must not prevent the OS preference fallback.
export const THEME_BOOTSTRAP = `(()=>{let saved=null;try{saved=localStorage.getItem(${escapeUnsafeJsChars(JSON.stringify(THEME_STORAGE_KEY))})}catch{}document.documentElement.dataset.theme=(${resolveTheme.toString()})(saved,window.matchMedia("(prefers-color-scheme: dark)").matches)})()`;
