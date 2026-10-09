"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { Meta } from "@/lib/types";
import type { Prefs } from "@/lib/prefs";
import { AgeRange, MyAgeField } from "./panel";

/** Phase 5: the hero's quick search — today's four first controls, moved
 * (onSelfSex, onSeekSex, MyAgeField, AgeRange, and their test ids). From
 * 640px it reads as one sentence, "I'm a [Woman] aged [30], looking for
 * [Men] aged [28 – 40]"; below that it is a 2x2 grid of labelled fields.
 * Each control's accessible name is its short label ("My age", "Their
 * age"); the sentence's words are what the eye reads beside it. The age
 * range opens a popover holding the two-handle AgeRange (Escape closes it
 * and focus returns to its button). "I'm a" keeps its data-variant
 * wrapper: the pre-paint veil (ADR 0018). After the Phase 5 report
 * (Nathan): no trust line beside the sentence. */
export function QuickSearch({
  prefs,
  meta,
  selfSex,
  onSelfSex,
  onSeekSex,
  onChange,
}: {
  prefs: Prefs;
  meta: Meta;
  selfSex: "male" | "female";
  onSelfSex: (sex: "male" | "female") => void;
  onSeekSex: (sex: "male" | "female") => void;
  onChange: (next: Prefs) => void;
}) {
  const uid = useId();
  const s = meta.policy_strings;
  return (
    <div
      className="mt-6 flex flex-wrap items-center gap-4 rounded-lg border border-rule bg-surface px-6 py-5 max-sm:mt-4 max-sm:p-3.5"
      data-testid="quick-search"
    >
      <div className="grid w-full grid-cols-2 gap-2.5 sm:flex sm:w-auto sm:flex-wrap sm:items-center sm:gap-2.5">
        <Slot word={s.quick_self_sex} label={s.quick_self_sex_short} htmlFor={`${uid}-you`}>
          <div data-variant="">
            <select
              id={`${uid}-you`}
              className="ctl tok"
              data-testid="self-sex"
              value={selfSex}
              onChange={(e) => onSelfSex(e.target.value as "male" | "female")}
            >
              <option value="female">Woman</option>
              <option value="male">Man</option>
            </select>
          </div>
        </Slot>
        <Slot word={s.quick_self_age} label={s.quick_self_age_short} htmlFor={`${uid}-myage`}>
          <div className="sm:w-[64px]">
            <MyAgeField
              id={`${uid}-myage`}
              value={prefs.selfAge}
              errorText={s.age_range_error}
              tokenClass="tok text-center"
              onCommit={(v) => onChange({ ...prefs, selfAge: v })}
            />
          </div>
          <span aria-hidden="true" className="-ml-2 text-body-lg text-ink-2 max-sm:hidden">,</span>
        </Slot>
        <Slot word={s.quick_seek_sex} label={s.quick_seek_sex_short} htmlFor={`${uid}-seek`}>
          <select
            id={`${uid}-seek`}
            className="ctl tok"
            data-testid="seek-sex"
            value={prefs.seekSex}
            onChange={(e) => onSeekSex(e.target.value as "male" | "female")}
          >
            <option value="male">Men</option>
            <option value="female">Women</option>
          </select>
        </Slot>
        <Slot word={s.quick_seek_age} label={s.quick_seek_age_short} htmlFor={`${uid}-ages`}>
          <AgePopover id={`${uid}-ages`} label={s.quick_seek_age_short} closeLabel={s.close}
            prefs={prefs} onChange={onChange} />
        </Slot>
      </div>
    </div>
  );
}

/** One field of the sentence: below 640px a label above the control; from
 * 640px the sentence's word before it (aria-hidden — the label, kept for
 * screen readers, names the control). Phase 6 (F34): the word and its
 * token wrap as one, so a line never ends on a lone label. */
function Slot({ word, label, htmlFor, children }: {
  word: string; label: string; htmlFor: string; children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1 sm:shrink-0 sm:flex-row sm:items-center sm:gap-2.5 sm:whitespace-nowrap">
      <label htmlFor={htmlFor} className="text-caption font-semibold text-ink-2 sm:sr-only">
        {label}
      </label>
      <span aria-hidden="true" className="text-body-lg text-ink-2 max-sm:hidden">
        {word}
      </span>
      {children}
    </div>
  );
}

/** The age range's token: a button showing "28 – 40" that opens a 300px
 * popover with the two-handle control. Escape, a click outside, or Close
 * closes it, and focus returns to the button. */
function AgePopover({ id, label, closeLabel, prefs, onChange }: {
  id: string; label: string; closeLabel: string; prefs: Prefs; onChange: (next: Prefs) => void;
}) {
  const [open, setOpen] = useState(false);
  const btn = useRef<HTMLButtonElement>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const close = (refocus = true) => {
    setOpen(false);
    if (refocus) btn.current?.focus();
  };
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    // focus moves into the popover: its first handle
    wrap.current?.querySelector<HTMLInputElement>('input[type="range"]')?.focus();
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);
  return (
    <div
      ref={wrap}
      className="relative"
      onKeyDown={(e) => {
        if (e.key === "Escape" && open) {
          e.stopPropagation();
          close();
        }
      }}
    >
      <button
        ref={btn}
        id={id}
        type="button"
        aria-expanded={open}
        aria-controls={`${id}-pop`}
        aria-label={`${label} ${prefs.ageMin} – ${prefs.ageMax}`}
        data-testid="age-token"
        className="ctl tok flex w-full items-center justify-between gap-2 text-left"
        onClick={() => setOpen(!open)}
      >
        <span>{prefs.ageMin} – {prefs.ageMax}</span>
        <svg width="12" height="8" viewBox="0 0 12 8" aria-hidden="true" className="text-ink-3"
          fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M1 1.5l5 5 5-5" /></svg>
      </button>
      <div
        id={`${id}-pop`}
        role="dialog"
        aria-label={label}
        hidden={!open}
        data-testid="age-popover"
        className="absolute left-0 top-full z-40 mt-2 w-[300px] rounded-lg border border-rule bg-surface p-5 shadow-overlay max-sm:right-0 max-sm:left-auto"
      >
        <AgeRange prefs={prefs} onChange={onChange} exact />
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            className="min-h-11 rounded-md px-3 text-body-sm font-semibold text-accent hover:text-accent-hover"
            onClick={() => close()}
          >
            {closeLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
