import type { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";

export function SiteShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Header />
        <main className="flex-1 p-6 md:p-10">{children}</main>
      </div>
    </div>
  );
}
