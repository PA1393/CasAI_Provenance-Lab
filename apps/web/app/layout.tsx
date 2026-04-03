import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CasAI Provenance Lab",
  description: "Track computational runs for CRISPR and base-editing workflows.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

