import Link from "next/link";
import { Suspense } from "react";
import { SearchBox } from "./search";

/** The v3 header: brand, two links, find-a-city. */
export function SiteHeader({ border = true }: { border?: boolean }) {
  return (
    <header
      className={`flex flex-wrap items-center justify-between gap-x-10 gap-y-3 px-6 py-5 sm:px-12 ${border ? "border-b border-rule" : ""}`}
    >
      <Link
        href="/"
        className="font-display text-[23px] font-semibold tracking-tight text-ink"
      >
        Dating Stats Atlas
      </Link>
      <div className="flex items-center gap-6">
        <Link href="/" className="text-sm font-semibold text-ink-2 hover:text-ink">
          Browse cities
        </Link>
        <Link
          href="/compare"
          className="text-sm font-semibold text-ink-2 hover:text-ink"
        >
          Compare cities
        </Link>
        <Link
          href="/what-we-measure"
          className="text-sm font-semibold text-ink-2 hover:text-ink"
        >
          What we measure
        </Link>
        <Link
          href="/how-it-works"
          className="text-sm font-semibold text-ink-2 hover:text-ink"
        >
          How it works
        </Link>
        <Suspense fallback={<div className="h-[42px] w-[190px]" />}>
          <SearchBox />
        </Suspense>
      </div>
    </header>
  );
}

export function PrimaryButton({
  children,
  onClick,
  type = "button",
  small = false,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  small?: boolean;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      className={`rounded-lg bg-accent font-bold text-white hover:bg-accent-hover ${small ? "min-h-[42px] px-[18px] text-[13.5px]" : "min-h-[46px] px-5 text-[14.5px]"}`}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({
  children,
  onClick,
  small = false,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  small?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border-[1.5px] border-ink bg-transparent font-bold text-ink hover:bg-tint ${small ? "min-h-[42px] px-[18px] text-[13.5px]" : "min-h-[46px] px-5 text-[14.5px]"}`}
    >
      {children}
    </button>
  );
}

export function MaleMark({ color = "var(--male)", size = 15 }: { color?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="6.5" cy="9.5" r="4.2" fill="none" stroke={color} strokeWidth="1.6" />
      <path d="M10 6L14 2M10.5 2H14V5.5" fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function FemaleMark({ color = "var(--female)", size = 15 }: { color?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="6" r="4.2" fill="none" stroke={color} strokeWidth="1.6" />
      <path d="M8 10.4V15M5.6 12.8H10.4" fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
