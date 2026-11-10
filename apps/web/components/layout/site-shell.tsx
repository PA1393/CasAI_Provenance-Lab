import type { ReactNode } from "react";
import { Header } from "./header";
import { Sidebar } from "./sidebar";
import { WorkspaceGate } from "./workspace-gate";
import { ConnectionStatus } from "./connection-status";

export function SiteShell({ children }: { children: ReactNode }) {
  return (
    <WorkspaceGate><div className="min-h-screen lg:grid lg:grid-cols-[9rem_minmax(0,1fr)]">
      <Sidebar />
      <div className="min-w-0">
        <Header />
        <ConnectionStatus />
        <main id="main-content" tabIndex={-1}>{children}</main>
      </div>
    </div></WorkspaceGate>
  );
}
