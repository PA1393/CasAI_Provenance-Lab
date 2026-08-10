import type { Metadata } from "next";
import { Fraunces, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { SiteShell } from "@/components/layout/site-shell";

// Fraunces for display: a warm serif with real italics, which is what stops the
// headings reading like every other dark-mode developer tool. Inter carries the
// interface copy, JetBrains Mono the sequence data and labels. All self-hosted
// by next/font, so no font-CDN request and no swap flash.
const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CasAI — Provenance Lab",
  description:
    "The system of record for gene editing. Track CRISPR and base-editing computational runs with full provenance.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${sans.variable} ${mono.variable}`}
    >
      <body>
        <SiteShell>{children}</SiteShell>
      </body>
    </html>
  );
}
