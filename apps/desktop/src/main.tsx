import { Component, StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { resolveTheme, THEME_STORAGE_KEY } from "../../web/lib/theme";
import { DesktopApp } from "./shell";
import "../../web/app/globals.css";
import "./style.css";

let saved = null;
try { saved = localStorage.getItem(THEME_STORAGE_KEY); } catch {}
document.documentElement.dataset.theme = resolveTheme(saved, matchMedia("(prefers-color-scheme: dark)").matches);

class DesktopErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <main role="alert" className="p-8">
      <h1 className="font-serif-display text-3xl">This screen could not be displayed</h1>
      <p className="my-4">Reopen the workspace to retry. If a submission was interrupted, inspect Runs before submitting again.</p>
      <button className="rounded bg-accent px-4 py-2 text-bg" onClick={() => location.reload()}>Reopen workspace</button>
    </main>;
    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(<StrictMode><DesktopErrorBoundary><DesktopApp /></DesktopErrorBoundary></StrictMode>);
