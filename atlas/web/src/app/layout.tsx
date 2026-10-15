import type { Metadata } from "next";
import { Figtree } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";
import { PRE_PAINT_SCRIPT } from "@/lib/about-you";
import { CHROME, pageMetadata, pageTitle, SITE_DESCRIPTION, SITE_URL } from "@/lib/chrome";

// Phase 8 (the round-4 review's R18): Google's Fraunces trimmed to what
// the site sets — SOFT pinned at 30, weights 600 to 700, every optical size
// — 58 KB where the whole variable font was 121 KB on every first visit
// (scripts/fraunces_trim.py; its licence beside it, fonts/OFL.txt)
const fraunces = localFont({
  src: [{ path: "./fonts/fraunces-latin.woff2", weight: "600 700", style: "normal" }],
  variable: "--font-fraunces",
  display: "swap",
  // the stand-in until it arrives is globals.css's "Fraunces Fallback"
  adjustFontFallback: false,
});
const figtree = Figtree({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-figtree",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  ...pageMetadata(
    pageTitle(),
    SITE_DESCRIPTION,
    "/",
  ),
  // every page sets its own canonical address (Phase 7, R07), so the
  // layout names none: a page without its own (the 404) has none
  alternates: undefined,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${fraunces.variable} ${figtree.variable}`}>
      <head>
        {/* m4.0.0 (ADR 0018): before the first paint, hide what a stored
            "about you" variant would change until the page has selected
            it (lib/about-you) — never a list that reorders under you */}
        <script dangerouslySetInnerHTML={{ __html: PRE_PAINT_SCRIPT }} />
      </head>
      <body className="flex min-h-screen flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-surface focus:px-3 focus:py-2 focus:text-ink"
        >
          {CHROME.skip_to_results}
        </a>
        {children}
      </body>
    </html>
  );
}
