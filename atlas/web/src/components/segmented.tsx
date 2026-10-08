"use client";

import { useRef } from "react";

/** Phase 5's segmented control (the importance levels; Best/Worst first):
 * a real radiogroup. The track is --sunken; the selected segment is
 * white with a 1.5px --ink-2 border (6.47:1 against the track, where
 * --line-strong would be 2.79:1) and --shadow-sm. One tab stop (roving
 * tabindex): the arrow keys move the selection and focus with it, Home
 * and End jump to the ends. Segments are 32px tall on the desk and 44px
 * below 1120px. */
export function Segmented<T extends string>({
  label,
  labelledBy,
  options,
  value,
  onChange,
  testid,
  inline = false,
}: {
  /** the group's accessible name, when no visible label names it */
  label?: string;
  labelledBy?: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  testid?: string;
  /** hug the content (Best/Worst) instead of filling the width */
  inline?: boolean;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const at = Math.max(0, options.findIndex((o) => o.value === value));
  const move = (i: number) => {
    const n = options.length;
    const j = (i + n) % n;
    onChange(options[j].value);
    refs.current[j]?.focus();
  };
  return (
    <div
      role="radiogroup"
      aria-label={label}
      aria-labelledby={labelledBy}
      data-testid={testid}
      className={`${inline ? "inline-grid auto-cols-fr grid-flow-col" : "grid auto-cols-fr grid-flow-col"} gap-[3px] rounded-md bg-sunken p-[3px]`}
      onKeyDown={(e) => {
        if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); move(at + 1); }
        else if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); move(at - 1); }
        else if (e.key === "Home") { e.preventDefault(); move(0); }
        else if (e.key === "End") { e.preventDefault(); move(options.length - 1); }
      }}
    >
      {options.map((o, i) => {
        const on = i === at;
        return (
          <button
            key={o.value}
            ref={(el) => { refs.current[i] = el; }}
            type="button"
            role="radio"
            aria-checked={on}
            tabIndex={on ? 0 : -1}
            onClick={() => onChange(o.value)}
            className={`flex h-11 items-center justify-center whitespace-nowrap rounded-sm px-3 text-body-sm desk:h-8 ${on
              ? "border-[1.5px] border-ink-2 bg-surface font-semibold text-ink shadow-sm"
              : "border border-transparent font-medium text-ink-2 hover:text-ink"}`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
