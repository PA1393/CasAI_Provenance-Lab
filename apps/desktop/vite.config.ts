import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";
import sharedTailwind from "../web/tailwind.config";

const local = (path: string) => fileURLToPath(new URL(path, import.meta.url));

export default defineConfig({
  base: "./",
  resolve: {
    alias: [
      { find: "next/link", replacement: local("./src/compat/link.tsx") },
      { find: "next/navigation", replacement: local("./src/compat/navigation.ts") },
      { find: "next/dynamic", replacement: local("./src/compat/dynamic.tsx") },
      { find: "@casai/env", replacement: local("./src/connection.ts") },
      { find: "@", replacement: local("../web") },
    ],
    dedupe: ["react", "react-dom"],
  },
  oxc: { jsx: { runtime: "automatic" } },
  css: {
    postcss: {
      plugins: [tailwindcss({
        ...sharedTailwind,
        content: [local("./src/**/*.{ts,tsx}"), local("../web/{app,components,lib}/**/*.{ts,tsx}")],
      }), autoprefixer()],
    },
  },
  build: { target: "es2022", sourcemap: false },
  server: { host: "127.0.0.1", port: 1420, strictPort: true },
});
