import type { Metadata } from "next";
import { Figtree, Fraunces } from "next/font/google";
import "./globals.css";
import { PRE_PAINT_SCRIPT } from "@/lib/about-you";

const fraunces = Fraunces({
  subsets: ["latin"],
  weight: "variable",
  axes: ["opsz", "SOFT"],
  variable: "--font-fraunces",
});
const figtree = Figtree({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-figtree",
});

export const metadata: Metadata = {
  title: "Dating Stats Atlas",
  description:
    "Which city has the best dating scene for you? Estimated from the Census Bureau's own survey, city by city.",
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
      <body className="min-h-screen">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-surface focus:px-3 focus:py-2 focus:text-ink"
        >
          Skip to results
        </a>
        {children}
      </body>
    </html>
  );
}
