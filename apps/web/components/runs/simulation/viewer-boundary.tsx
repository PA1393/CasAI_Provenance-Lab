"use client";

import { Component, type ReactNode } from "react";

export class ViewerBoundary extends Component<{ children: ReactNode }, { failed: boolean; diagnostic: string }> {
  state = { failed: false, diagnostic: "" };
  static getDerivedStateFromError(error: unknown) { return { failed: true, diagnostic: error instanceof Error ? error.message.slice(0, 240) : "Viewer initialization error" }; }
  render() {
    if (this.state.failed) return <div role="alert" className="flex h-full flex-col justify-center gap-3 rounded-lg border border-border bg-bg-sunken p-5 text-sm">
      <p className="font-semibold">The reference structure viewer could not initialize.</p>
      <p className="text-text-secondary">Your run and results are unchanged. The CasAI scene, Summary and Provenance remain available. Reopen this run after updating the desktop app.</p>
      <details className="text-xs text-muted"><summary>Viewer diagnostic</summary><p className="mt-2 break-words">{this.state.diagnostic}</p></details>
    </div>;
    return this.props.children;
  }
}
