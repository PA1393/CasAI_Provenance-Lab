import type { Config } from "tailwindcss";

// Every colour resolves through a CSS variable rather than a literal. That is
// what lets `.instrument` (see globals.css) redefine the palette for a subtree:
// the simulation console flips to dark instrument colours without a single
// component changing the classes it renders.
//
// Values are space-separated RGB triplets so Tailwind's `/40` alpha modifiers
// still work — `bg-bg-card/40` and `border-accent/60` are both used in the app.
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

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
          DEFAULT: token("bg"),
          card: token("bg-card"),
          sunken: token("bg-sunken"),
          elevated: token("bg-card"),
        },
        border: {
          DEFAULT: token("border"),
          strong: token("border-strong"),
        },
        text: {
          DEFAULT: token("text"),
          secondary: token("text-secondary"),
        },
        muted: token("muted"),
        accent: {
          DEFAULT: token("accent"),
          bright: token("accent-bright"),
          soft: token("accent-soft"),
          dim: token("accent-bright"),
          amber: token("accent-amber"),
          red: token("accent-red"),
          green: token("accent"),
        },
        ink: token("text"),
        mist: token("bg-card"),
        accentSoft: token("accent-soft"),
      },
      fontFamily: {
        // A warm serif for display and a neutral sans for interface copy — the
        // pairing reads as clinical and considered rather than as a dark SaaS
        // template. Variables are emitted by next/font in layout.tsx.
        sans: ["var(--font-sans)", "-apple-system", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
        serif: ["var(--font-display)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: {
        DEFAULT: "0.5rem",
        md: "0.625rem",
        lg: "0.875rem",
        xl: "1.125rem",
        "2xl": "1.5rem",
      },
      boxShadow: {
        // Warm-tinted rather than neutral black — shadows over a bone background
        // look muddy if they are pure grey.
        card: "0 1px 2px rgb(41 34 26 / 0.04), 0 2px 6px -1px rgb(41 34 26 / 0.06)",
        raised: "0 2px 4px rgb(41 34 26 / 0.05), 0 12px 28px -8px rgb(41 34 26 / 0.14)",
        instrument: "inset 0 1px 0 rgb(255 255 255 / 0.03), 0 18px 40px -24px rgb(0 0 0 / 0.9)",
        glow: "0 0 0 1px rgb(var(--accent) / 0.25), 0 0 24px -6px rgb(var(--accent) / 0.35)",
      },
      transitionTimingFunction: {
        apple: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
