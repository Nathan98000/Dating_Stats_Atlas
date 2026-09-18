"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";

/** The accessible information affordance (Phase 2d item 2, shared since
 * Phase 2e; reworked in Phase 2f item 3 so the note stays open long
 * enough to use). Hover is handled on the WRAPPER, not the button: the
 * button and its note are one pointer target, and the note's container
 * starts flush with the button's bottom edge (the visual 8px gap is
 * padding inside the hover target), so moving the pointer from the
 * button into the note never crosses dead space. Focus leaving the
 * wrapper closes it (a relatedTarget still inside — tabbing from the
 * button onto a link in the note — keeps it open); Escape closes and
 * returns focus to the button; pointerdown anywhere outside closes.
 * Click/tap still OPENS rather than toggling (a toggle fights the
 * hover-open on pointer devices). */
export function InfoTip({
  id,
  label,
  testid = "info-tip",
  children,
}: {
  id: string;
  label: string;
  testid?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLSpanElement>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const note = useRef<HTMLSpanElement>(null);
  const [dx, setDx] = useState(0);

  // keep the note inside the viewport: a last-column card's centred note
  // would clip its "See more details" link off the right edge
  useLayoutEffect(() => {
    if (!open) {
      setDx(0);
      return;
    }
    const el = note.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const pad = 12;
    let shift = 0;
    if (r.right > window.innerWidth - pad) {
      shift = window.innerWidth - pad - r.right;
    }
    if (r.left + shift < pad) shift = pad - r.left;
    setDx(Math.round(shift));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  return (
    <span
      ref={wrap}
      className="relative inline-flex"
      onPointerEnter={(e) => {
        if (e.pointerType !== "touch") setOpen(true);
      }}
      onPointerLeave={(e) => {
        if (e.pointerType !== "touch") setOpen(false);
      }}
      onBlur={(e) => {
        // focusout with a relatedTarget check: leaving the wrapper
        // closes; moving between the button and the note's link does not
        if (!wrap.current?.contains(e.relatedTarget as Node)) setOpen(false);
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape" && open) {
          e.stopPropagation();
          setOpen(false);
          btn.current?.focus();
        }
      }}
    >
      <button
        ref={btn}
        type="button"
        data-testid={testid}
        aria-label={label}
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        className="flex h-[22px] w-[22px] items-center justify-center rounded-full border-[1.5px] border-ink-3 text-[12px] font-bold leading-none text-ink-2 hover:border-accent hover:text-accent"
        onClick={() => setOpen(true)}
        onFocus={() => setOpen(true)}
      >
        i
      </button>
      {open && (
        <span
          className="absolute left-1/2 top-[22px] z-40 -translate-x-1/2 pt-2"
          data-testid={`${testid}-bridge`}
        >
          <span
            ref={note}
            id={id}
            role="note"
            data-testid={`${testid}-note`}
            className="block w-[290px] rounded-lg border border-rule bg-surface px-3.5 py-3 text-left text-[12.5px] font-normal leading-relaxed text-ink-2"
            style={dx ? { transform: `translateX(${dx}px)` } : undefined}
          >
            {children}
          </span>
        </span>
      )}
    </span>
  );
}
