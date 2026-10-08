"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

/** The accessible information affordance (Phase 2d item 2, shared since
 * Phase 2e; reworked in Phase 2f item 3 so the note stays open long
 * enough to use). Hover is handled on the WRAPPER, not the button: the
 * button and its note are one pointer target (the note is the wrapper's
 * descendant, though positioned against the viewport), and the note
 * starts flush with the button's 44px hit area, so moving the pointer
 * from the button into the note never crosses dead space. Focus leaving the
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
  const [pos, setPos] = useState<{ left: number; top: number; width: number } | null>(null);

  // After the Phase 5 report (Nathan): the note is positioned against the
  // viewport (position: fixed) from the button's own box, so no container
  // clips it — the side rail scrolls inside itself now — and no card later
  // in the page covers it. It sits under the button, flush with the
  // button's 44px hit area (no dead space to cross), flips above when
  // there is no room below, stays inside the viewport, and follows the
  // button while anything scrolls.
  const place = useCallback(() => {
    const b = btn.current;
    if (!b) return;
    const r = b.getBoundingClientRect();
    const pad = 12;
    const width = Math.min(290, window.innerWidth - 2 * pad);
    const left = Math.min(Math.max(r.left + r.width / 2 - width / 2, pad),
                          window.innerWidth - pad - width);
    const h = note.current?.offsetHeight ?? 0;
    const below = r.bottom + h <= window.innerHeight - pad || r.top - h < pad;
    setPos({ left: Math.round(left), top: Math.round(below ? r.bottom : r.top - h), width });
  }, []);
  useLayoutEffect(() => {
    if (!open) {
      setPos(null);
      return;
    }
    place();
    // a second pass, once the note's own height is known
    const raf = requestAnimationFrame(place);
    window.addEventListener("scroll", place, { capture: true, passive: true });
    window.addEventListener("resize", place);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", place, { capture: true });
      window.removeEventListener("resize", place);
    };
  }, [open, place]);

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
        className="-m-[14px] flex h-11 w-11 items-center justify-center rounded-full text-ink-3 hover:text-accent"
        onClick={() => setOpen(true)}
        onFocus={() => setOpen(true)}
      >
        {/* Phase 5: a 16px icon inside a 44x44 hit area (the negative
            margin keeps the line it sits in at the icon's size) */}
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" fill="none">
          <circle cx="8" cy="8" r="7.1" stroke="currentColor" strokeWidth="1.5" />
          <path d="M8 7.2v4.3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <circle cx="8" cy="4.9" r="1" fill="currentColor" />
        </svg>
      </button>
      {open && (
        <span
          className="fixed z-50"
          style={pos ? { left: pos.left, top: pos.top, width: pos.width }
                     : { left: 0, top: 0, width: 290, visibility: "hidden" }}
          data-testid={`${testid}-bridge`}
        >
          <span
            ref={note}
            id={id}
            role="note"
            data-testid={`${testid}-note`}
            className="block rounded-lg border border-rule bg-surface px-3.5 py-3 text-left text-caption font-normal text-ink-2 shadow-overlay"
          >
            {children}
          </span>
        </span>
      )}
    </span>
  );
}
