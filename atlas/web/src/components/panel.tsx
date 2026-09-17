"use client";

import { useId, useRef, useState } from "react";
import type { Meta } from "@/lib/types";
import { IMPORTANCE_PILLARS, type Level, type Prefs } from "@/lib/prefs";

const RACE_LABELS: Record<string, string> = {
  hispanic: "Hispanic",
  white_nh: "White",
  black_nh: "Black",
  asian_nh: "Asian",
  aian_nh: "Native American",
  nhpi_nh: "Pacific Islander",
};
const ALL_SIX = Object.keys(RACE_LABELS);
const EDU_OPTIONS: { value: "" | "bachelors" | "graduate"; label: string }[] = [
  { value: "", label: "Any" },
  { value: "bachelors", label: "College degree" },
  { value: "graduate", label: "Graduate degree" },
];
const LEVELS: { value: Level; label: string }[] = [
  { value: "not_much", label: "Not much" },
  { value: "some", label: "Some" },
  { value: "a_lot", label: "A lot" },
];

function Field({ label, htmlFor, children }: {
  label: string; htmlFor?: string; children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-[13px] font-semibold text-ink-2">
        {label}
      </label>
      {children}
    </div>
  );
}

/** The HomeV3 panel: the whole scoring model plus the whole search, with
 * no hidden defaults. Sends choices, never weights (item 5). */
export function SearchPanel({
  prefs,
  meta,
  onChange,
  sameSexNote,
}: {
  prefs: Prefs;
  meta: Meta;
  onChange: (next: Prefs) => void;
  sameSexNote: boolean;
}) {
  const uid = useId();
  const set = (patch: Partial<Prefs>) => onChange({ ...prefs, ...patch });
  const seekSexEffective = prefs.seekSex ?? (prefs.selfSex === "female" ? "male" : "female");
  const s = prefs.poolVsBalance ?? 0.4545;
  const raceSelected = prefs.race ?? ALL_SIX;

  return (
    <div className="flex flex-col gap-6 rounded-xl border border-rule bg-surface p-6">
      {/* the slider: the hero control */}
      <div className="flex flex-col gap-2.5">
        <div className="flex items-center gap-2">
          <label htmlFor={`${uid}-svo`} className="text-sm font-semibold">
            What matters more to you?
          </label>
          <InfoTip
            id={`${uid}-svo-info`}
            label="What the slider changes"
            text={meta.policy_strings.slider_info}
          />
        </div>
        <input
          id={`${uid}-svo`}
          type="range"
          className="svo"
          min={0}
          max={1}
          step={0.05}
          value={s}
          style={{ "--fill": `${s * 100}%` } as React.CSSProperties}
          aria-valuetext={`${Math.round(s * 100)} percent toward dating pool balance`}
          onChange={(e) => set({ poolVsBalance: parseFloat(e.target.value) })}
        />
        <div className="flex justify-between text-[12.5px] font-semibold text-ink-2">
          <span>{"Dating pool size"}</span>
          <span>{"Dating pool balance"}</span>
        </div>
        {sameSexNote && (
          <p className="text-[12.5px] leading-relaxed text-ink-3">
            {meta.policy_strings.balance_same_sex}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-4 border-t border-rule pt-5">
        <div className="grid grid-cols-[1fr_96px] gap-3">
          <Field label="I'm a" htmlFor={`${uid}-you`}>
            <select
              id={`${uid}-you`}
              className="ctl"
              value={prefs.selfSex}
              onChange={(e) => set({ selfSex: e.target.value as Prefs["selfSex"] })}
            >
              <option value="female">Woman</option>
              <option value="male">Man</option>
            </select>
          </Field>
          <Field label="My age" htmlFor={`${uid}-myage`}>
            <input
              id={`${uid}-myage`}
              type="number"
              inputMode="numeric"
              className="ctl"
              min={18}
              max={70}
              value={prefs.selfAge}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10);
                if (Number.isFinite(v)) set({ selfAge: Math.min(70, Math.max(18, v)) });
              }}
            />
          </Field>
        </div>

        <Field label="I'm looking for" htmlFor={`${uid}-seek`}>
          <select
            id={`${uid}-seek`}
            className="ctl"
            value={seekSexEffective}
            onChange={(e) => set({ seekSex: e.target.value as Prefs["seekSex"] })}
          >
            <option value="male">Men</option>
            <option value="female">Women</option>
          </select>
        </Field>

        <AgeRange prefs={prefs} onChange={onChange} />

        <fieldset>
          <legend className="mb-1.5 text-[13px] font-semibold text-ink-2">
            Single means
          </legend>
          <div className="flex gap-2">
            {[
              { v: "never_married", label: "Never married" },
              { v: "previously_married", label: "Divorced or widowed" },
            ].map(({ v, label }) => {
              const on = prefs.marital.includes(v);
              return (
                <button
                  key={v}
                  type="button"
                  role="checkbox"
                  aria-checked={on}
                  className={`min-h-[40px] flex-1 rounded-lg border px-2 text-[13px] font-semibold ${on ? "border-tint-border bg-tint text-accent-hover" : "border-rule bg-surface text-ink-3"}`}
                  onClick={() => {
                    const next = on
                      ? prefs.marital.filter((m) => m !== v)
                      : [...prefs.marital, v];
                    if (next.length) set({ marital: next });
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Education" htmlFor={`${uid}-edu`}>
            <select
              id={`${uid}-edu`}
              className="ctl"
              value={prefs.educationMin ?? ""}
              onChange={(e) =>
                set({ educationMin: (e.target.value || undefined) as Prefs["educationMin"] })
              }
            >
              {EDU_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Earning at least" htmlFor={`${uid}-inc`}>
            {/* only the survey's own income steps — anything else has no count */}
            <select
              id={`${uid}-inc`}
              className="ctl"
              value={prefs.incomeMin ?? ""}
              onChange={(e) =>
                set({ incomeMin: e.target.value ? parseInt(e.target.value, 10) : undefined })
              }
            >
              <option value="">Any</option>
              {meta.controls.income_band_edges.map((edge) => (
                <option key={edge} value={edge}>
                  ${edge.toLocaleString("en-US")}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {/* Item 3: nothing editorial here — label, six boxes, clear-all.
            The always-counted-groups disclosure moved to How it works and
            the methodology (the report says so). */}
        <fieldset data-testid="race-panel">
          <div className="mb-2 flex items-baseline justify-between">
            <legend className="text-[13px] font-semibold text-ink-2">
              Race &amp; ethnicity
            </legend>
            {prefs.race?.length ? (
              <button
                type="button"
                className="text-[12.5px] font-semibold text-accent underline underline-offset-2"
                onClick={() => set({ race: undefined })}
              >
                Include all
              </button>
            ) : null}
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
            {ALL_SIX.map((r) => {
              const on = raceSelected.includes(r);
              return (
                <label key={r} className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="check"
                    checked={on}
                    onChange={(e) => {
                      const cur = new Set(prefs.race ?? ALL_SIX);
                      if (e.target.checked) cur.add(r);
                      else cur.delete(r);
                      // all six or none = no filter; the model treats both
                      // as everyone, and the URL says so honestly
                      const next = [...cur].filter((x) => ALL_SIX.includes(x));
                      set({
                        race:
                          next.length === 0 || next.length === ALL_SIX.length
                            ? undefined
                            : next,
                      });
                    }}
                  />
                  {RACE_LABELS[r]}
                </label>
              );
            })}
          </div>
        </fieldset>
      </div>

      {/* Item 4: FOUR controls, labels and subtitles from the registry
          through /v1/meta — student life is no longer bundled with the
          weather, and the frontend still sends choices, never weights. */}
      <div className="flex flex-col gap-3 border-t border-rule pt-5" data-testid="importance">
        <div>
          <p className="text-sm font-semibold">How much do these matter?</p>
          <p className="text-[12.5px] text-ink-3">Beyond the people themselves.</p>
        </div>
        <div className="flex flex-col gap-3">
          {IMPORTANCE_PILLARS.map((pillar) => (
            <ImportanceRow
              key={pillar}
              label={meta.pillars[pillar]?.display_name ?? pillar}
              subtitle={meta.pillars[pillar]?.control_subtitle ?? ""}
              value={prefs.importance[pillar]}
              onPick={(lv) =>
                set({ importance: { ...prefs.importance, [pillar]: lv } })
              }
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/** Item 2's information affordance: a real button, not a hover-only
 * tooltip — it opens on hover AND focus AND tap, closes on Escape and
 * blur, and is wired with aria-expanded + aria-describedby so the note
 * reaches keyboard and touch users (gate 2/5). */
function InfoTip({ id, label, text }: { id: string; label: string; text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex">
      <button
        type="button"
        data-testid="slider-info"
        aria-label={label}
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        className="flex h-[22px] w-[22px] items-center justify-center rounded-full border-[1.5px] border-ink-3 text-[12px] font-bold leading-none text-ink-2 hover:border-accent hover:text-accent"
        // click/tap OPENS (a toggle would fight the hover-open on pointer
        // devices: the click's own hover reopens, the toggle re-closes);
        // closing is Escape, blur, or the pointer leaving — and on touch,
        // tapping anywhere else blurs
        onClick={() => setOpen(true)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
      >
        i
      </button>
      {open && (
        <span
          id={id}
          role="note"
          data-testid="slider-info-note"
          className="absolute left-1/2 top-[30px] z-40 w-[290px] -translate-x-1/2 rounded-lg border border-rule bg-surface px-3.5 py-3 text-[12.5px] font-normal leading-relaxed text-ink-2"
        >
          {text}
        </span>
      )}
    </span>
  );
}

function ImportanceRow({
  label,
  subtitle,
  value,
  onPick,
}: {
  label: string;
  subtitle: string;
  value: Level;
  onPick: (lv: Level) => void;
}) {
  return (
    <div className="grid grid-cols-[150px_1fr] items-center gap-x-3 max-sm:grid-cols-1 max-sm:gap-y-1">
      <span className="flex flex-col">
        <span className="text-[13px] font-semibold text-ink-2">{label}</span>
        {subtitle ? (
          <span className="text-[11.5px] leading-snug text-ink-3">{subtitle}</span>
        ) : null}
      </span>
      <div role="radiogroup" aria-label={`${label} importance`} className="flex gap-[5px]">
        {LEVELS.map((lv) => {
          const on = value === lv.value;
          return (
            <button
              key={lv.value}
              type="button"
              role="radio"
              aria-checked={on}
              className={`min-h-[34px] flex-1 rounded-[7px] border text-xs font-semibold ${on ? "border-accent bg-accent text-white" : "border-rule bg-paper text-ink-3 hover:border-ink-3"}`}
              onClick={() => onPick(lv.value)}
            >
              {lv.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** The two-handle age control (StatesV3): one visual track, two range
 * inputs, each handle separately labelled and keyboard-movable one year at
 * a time; handles can meet but not cross. */
export function AgeRange({
  prefs,
  onChange,
}: {
  prefs: Prefs;
  onChange: (next: Prefs) => void;
}) {
  const uid = useId();
  const lo = useRef<HTMLInputElement>(null);
  const MIN = 18;
  const MAX = 70;
  const pct = (v: number) => ((v - MIN) / (MAX - MIN)) * 100;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between">
        <span id={`${uid}-lab`} className="text-[13px] font-semibold text-ink-2">
          Aged
        </span>
        <output className="text-[15px] font-bold" data-testid="age-output">
          {prefs.ageMin} – {prefs.ageMax}
        </output>
      </div>
      <div className="age-track" role="group" aria-labelledby={`${uid}-lab`}>
        <span className="rail" />
        <span
          className="fill"
          style={{ left: `${pct(prefs.ageMin)}%`, right: `${100 - pct(prefs.ageMax)}%` }}
        />
        <input
          ref={lo}
          type="range"
          min={MIN}
          max={MAX}
          step={1}
          value={prefs.ageMin}
          aria-label="Youngest age"
          aria-valuetext={`youngest age ${prefs.ageMin}`}
          onChange={(e) => {
            const v = Math.min(parseInt(e.target.value, 10), prefs.ageMax);
            onChange({ ...prefs, ageMin: v });
          }}
        />
        <input
          type="range"
          min={MIN}
          max={MAX}
          step={1}
          value={prefs.ageMax}
          aria-label="Oldest age"
          aria-valuetext={`oldest age ${prefs.ageMax}`}
          onChange={(e) => {
            const v = Math.max(parseInt(e.target.value, 10), prefs.ageMin);
            onChange({ ...prefs, ageMax: v });
          }}
        />
      </div>
      <div className="flex justify-between text-xs text-ink-3">
        <span>{MIN}</span>
        <span>{MAX}</span>
      </div>
    </div>
  );
}
