"use client";

/** Phase 6 (F35): the search fields' own clear button — 44x44, an ink-3
 * cross — in place of the browser's blue one (hidden in globals.css), shown
 * while the field holds text. It sits at the field's right end (the field
 * keeps room for it); pressing it never takes focus from the field. */
export function ClearButton({ label, onClear }: { label: string; onClear: () => void }) {
  return (
    <button
      type="button"
      aria-label={label}
      data-testid="clear-button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClear}
      className="absolute right-0 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full text-ink-3 hover:text-ink"
    >
      <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" fill="none"
        stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
        <path d="M3 3l8 8M11 3l-8 8" />
      </svg>
    </button>
  );
}
