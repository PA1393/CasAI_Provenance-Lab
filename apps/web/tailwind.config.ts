import type { Config } from "tailwindcss";

// Palette: true-neutral blacks (no colour cast in the greys) with a single
// green accent. Greys and greens are Apple's dark-mode system values, which is
// what makes the whole thing read as native on macOS rather than as a theme.
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#000000",
          card: "#0c0c0c",
          elevated: "#151515",
        },
        border: {
          DEFAULT: "#1e1e1e",
          strong: "#2c2c2c",
        },
        text: {
          DEFAULT: "#f5f5f7",
          secondary: "#a1a1a6",
        },
        muted: "#6e6e73",
        accent: {
          DEFAULT: "#30d158",
          dim: "#248a3d",
          bright: "#5ee77f",
          red: "#ff453a",
          amber: "#ff9f0a",
          green: "#30d158",
        },
        // Legacy aliases for any leftover references
        ink: "#f5f5f7",
        mist: "#0c0c0c",
        accentSoft: "#0f2417",
      },
      fontFamily: {
        // Space Grotesk everywhere but code. Its narrow apertures and cut
        // terminals give the product a recognisable voice that a system sans
        // can't, while staying a workhorse at body sizes. The variables are
        // defined by next/font in layout.tsx, so the files are self-hosted and
        // there is no render-blocking request to a font CDN.
        sans: ["var(--font-display)", "-apple-system", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "-apple-system", "system-ui", "sans-serif"],
        serif: ["var(--font-display)", "-apple-system", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: {
        // Softer than Tailwind's defaults — closer to the continuous corners
        // used across macOS surfaces.
        DEFAULT: "0.5rem",
        md: "0.625rem",
        lg: "0.875rem",
        xl: "1.125rem",
        "2xl": "1.375rem",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.6), 0 8px 24px -12px rgba(0,0,0,0.9)",
        raised: "0 2px 6px rgba(0,0,0,0.7), 0 16px 40px -16px rgba(0,0,0,0.95)",
        glow: "0 0 0 1px rgba(48,209,88,0.28), 0 0 28px -6px rgba(48,209,88,0.35)",
      },
      transitionTimingFunction: {
        // Apple's standard ease — noticeably calmer than Tailwind's default.
        apple: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
