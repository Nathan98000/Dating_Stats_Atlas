"use client";

import { useEffect, useRef } from "react";

/** Phase 5: the search's sheet (below 640px) and drawer (640-1119px) — a
 * modal <dialog>, so focus is trapped and Escape closes it for free. A
 * click on the backdrop closes it, as does a downward swipe on the sheet;
 * the page behind stops scrolling while it is open; on close, focus
 * returns to the button that opened it (the browser's own return, made
 * explicit). Changes apply live; the sticky footer button only closes.
 *
 * Phase 6 (F05, F19): the footer's "Show results" closes the sheet and
 * hands the page `onFooter`'s next step (the results heading) instead of
 * returning focus to the bar; `lead`, a row at the top of the body, may do
 * the same (`afterClose` decides where focus goes once the sheet has
 * closed; returning false keeps the bar's return). The close button,
 * Escape and the backdrop still only close it. */
export function BottomSheet({
  open,
  onClose,
  title,
  footerLabel,
  closeLabel,
  returnFocus,
  onFooter,
  afterClose,
  lead,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  footerLabel: string;
  closeLabel: string;
  returnFocus: React.RefObject<HTMLElement | null>;
  /** the footer button: by default it only closes */
  onFooter?: () => void;
  /** after the sheet has closed: true when it placed focus itself */
  afterClose?: () => boolean;
  lead?: React.ReactNode;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const drag = useRef<{ y: number; dy: number } | null>(null);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      d.showModal();
      document.documentElement.style.overflow = "hidden";
    } else if (!open && d.open) {
      d.close();
    }
  }, [open]);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    const onClosed = () => {
      document.documentElement.style.overflow = "";
      onClose();
      if (!afterClose?.()) returnFocus.current?.focus();
    };
    d.addEventListener("close", onClosed);
    return () => d.removeEventListener("close", onClosed);
  }, [onClose, returnFocus, afterClose]);

  return (
    <dialog
      ref={ref}
      aria-label={title}
      data-testid="search-sheet"
      className="sheet m-0 max-h-none max-w-none bg-transparent p-0 backdrop:bg-ink/40"
      onClick={(e) => {
        // the dialog element itself is the backdrop area
        if (e.target === ref.current) ref.current?.close();
      }}
    >
      <div
        ref={panel}
        className="sheet-panel flex flex-col bg-surface shadow-overlay"
        onTouchStart={(e) => {
          const t = e.touches[0];
          const body = panel.current?.querySelector(".sheet-body");
          // only a swipe that starts at the handle, or with the body at its top
          if (body && body.scrollTop > 0 && !(e.target as HTMLElement).closest(".sheet-handle")) return;
          drag.current = { y: t.clientY, dy: 0 };
        }}
        onTouchMove={(e) => {
          if (!drag.current || !panel.current) return;
          const dy = Math.max(0, e.touches[0].clientY - drag.current.y);
          drag.current.dy = dy;
          panel.current.style.transform = dy ? `translateY(${dy}px)` : "";
        }}
        onTouchEnd={() => {
          if (!drag.current || !panel.current) return;
          const far = drag.current.dy > 90;
          panel.current.style.transform = "";
          drag.current = null;
          if (far) ref.current?.close();
        }}
      >
        <div className="sheet-handle flex justify-center pb-1 pt-2.5 sm:hidden" aria-hidden="true">
          <span className="h-1 w-10 rounded-full bg-data-neutral" />
        </div>
        <div className="flex items-center justify-between px-5 pt-2 sm:pt-4">
          <h2 className="font-display text-h3">{title}</h2>
          <button
            type="button"
            aria-label={closeLabel}
            onClick={() => ref.current?.close()}
            className="-mr-2 flex h-11 w-11 items-center justify-center rounded-full text-ink-2 hover:text-ink"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" fill="none"
              stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <path d="M4 4l10 10M14 4L4 14" />
            </svg>
          </button>
        </div>
        <div className="sheet-body flex-1 overflow-y-auto overscroll-contain px-5 pb-6 pt-2">
          {lead}
          {children}
        </div>
        <div className="border-t border-rule px-4 pb-[calc(14px+env(safe-area-inset-bottom))] pt-2.5">
          <button
            type="button"
            onClick={() => { onFooter?.(); ref.current?.close(); }}
            className="flex h-[52px] w-full items-center justify-center rounded-md bg-accent text-body font-semibold text-white hover:bg-accent-hover"
            data-testid="show-results"
          >
            {footerLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
