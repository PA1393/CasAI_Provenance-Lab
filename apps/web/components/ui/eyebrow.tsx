import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  muted?: boolean;
};

export function Eyebrow({ children, muted = false }: Props) {
  return (
    <div
      className={`font-mono text-xs tracking-[0.2em] uppercase font-semibold ${
        muted ? "text-muted" : "text-accent"
      }`}
    >
      {children}
    </div>
  );
}
