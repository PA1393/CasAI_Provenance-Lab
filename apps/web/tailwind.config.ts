import type { Config } from "tailwindcss";

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
          DEFAULT: "#0a0a0f",
          card: "#13131c",
        },
        border: {
          DEFAULT: "#1f1f28",
        },
        text: {
          DEFAULT: "#e8e8ed",
        },
        muted: "#8a8a95",
        accent: {
          DEFAULT: "#7dd3d8",
          red: "#e85d4d",
          amber: "#f5b942",
          green: "#9dd89d",
        },
        // Legacy aliases for any leftover references
        ink: "#e8e8ed",
        mist: "#13131c",
        accentSoft: "#1a2a2a",
      },
      fontFamily: {
        serif: ["Georgia", "Cambria", "Times New Roman", "serif"],
        mono: ["JetBrains Mono", "Consolas", "Monaco", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
