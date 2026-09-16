import type { Metadata } from "next";
import { IBM_Plex_Mono, Newsreader, Public_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  style: ["normal", "italic"],
  variable: "--font-newsreader",
});
const publicSans = Public_Sans({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-public-sans",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Dating Stats Atlas",
  description:
    "Compatible partners per U.S. metro, from Census microdata — every number with its margin, every margin honest.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${newsreader.variable} ${publicSans.variable} ${plexMono.variable}`}
    >
      <body className="min-h-screen">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-raised focus:px-3 focus:py-2 focus:text-ink"
        >
          Skip to results
        </a>
        {children}
        <footer className="mx-auto mt-16 max-w-6xl border-t border-rule px-5 py-8 text-sm text-ink-2">
          <div className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2">
            <p className="max-w-[52ch]">
              Every figure on this site traces to a named public source and
              transformation, carries its margin of error in the row, and is
              suppressed rather than guessed when the sample is too small.
            </p>
            <nav className="flex gap-6">
              <Link className="underline underline-offset-2 hover:text-ink" href="/methodology">
                How the numbers are made
              </Link>
              <Link className="underline underline-offset-2 hover:text-ink" href="/">
                Rankings
              </Link>
            </nav>
          </div>
        </footer>
      </body>
    </html>
  );
}
