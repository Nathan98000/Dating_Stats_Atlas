"use client";

import { useId, useRef, useState } from "react";
import type { Meta } from "@/lib/types";
import { IMPORTANCE_PILLARS, SELF_EDU_LEVELS, type Level, type Prefs,
  type SelfEdu } from "@/lib/prefs";
import type { AboutYou } from "@/lib/about-you";
import { InfoTip } from "./info-tip";

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

/** A panel section (Phase 4b, Nathan's change 3): a fieldset whose legend
 * is a real heading, so a screen reader meets the same two groups — and
 * can jump between them by heading — that the eye sees. A divided
 * section opens with a rule; it sits on a wrapper, since a fieldset's
 * own border would run through its legend. */
function Section({ heading, testid, divided = false, children }: {
  heading: string; testid: string; divided?: boolean; children: React.ReactNode;
}) {
  return (
    <div className={divided ? "border-t border-rule pt-6" : undefined}>
      <fieldset className="min-w-0" data-testid={testid}>
        <legend className="mb-4 p-0">
          <h2 className="font-display text-[19px] font-semibold leading-tight text-ink">
            {heading}
          </h2>
        </legend>
        <div className="flex flex-col gap-4">{children}</div>
      </fieldset>
    </div>
  );
}

/** The HomeV3 panel: the whole scoring model plus the whole search, with
 * no hidden defaults. Sends choices, never weights (item 5). m4.0.0 (ADR
 * 0018): "I'm a", "My education" and "My race or ethnicity" are the
 * visitor's own details — kept in this browser by the page and never
 * sent. Phase 4b (ADR 0018 amended): two sections, "About you" and "Who
 * you're looking for", then the weighting; race is one select whose
 * default, "Prefer not to say", means race is not used; no note sits
 * beside the details (the Privacy page explains where they go). */
export function SearchPanel({
  prefs,
  meta,
  onChange,
  sameSex,
  sameSexNote,
  about,
  selfSex,
  onSelfSex,
  onSeekSex,
  onAbout,
}: {
  prefs: Prefs;
  meta: Meta;
  onChange: (next: Prefs) => void;
  sameSex: boolean;
  /** the served same-sex sentence (the rows' match.note), shown in the
   * slider's box on a same-sex search only */
  sameSexNote: string;
  about: AboutYou;
  selfSex: "male" | "female";
  onSelfSex: (sex: "male" | "female") => void;
  onSeekSex: (sex: "male" | "female") => void;
  onAbout: (next: AboutYou) => void;
}) {
  const uid = useId();
  const set = (patch: Partial<Prefs>) => onChange({ ...prefs, ...patch });
  const s = prefs.poolVsMatch ?? 0.4545;
  const policy = meta.policy_strings;
  // m3.0.0 (ADR 0009): the pole labels and every string of the two
  // optional "about you" inputs arrive from the registry through /v1/meta
  const poles = meta.controls.slider_labels;
  // m2.2.0 (ADR 0006): eight equal groups, ids and labels from the
  // registry through /v1/meta — the panel types no race wording
  const raceGroups = meta.race_groups;
  const allIds = raceGroups.map((g) => g.id);
  const raceSelected = prefs.race ?? allIds;

  return (
    <div className="flex flex-col gap-6 rounded-xl border border-rule bg-surface p-6">
      <Section heading={policy.panel_about_you_heading} testid="about-you-section">
        <div className="grid grid-cols-[1fr_96px] gap-3">
          <div data-variant="">
            <Field label="I'm a" htmlFor={`${uid}-you`}>
              <select
                id={`${uid}-you`}
                className="ctl"
                data-testid="self-sex"
                value={selfSex}
                onChange={(e) => onSelfSex(e.target.value as "male" | "female")}
              >
                <option value="female">Woman</option>
                <option value="male">Man</option>
              </select>
            </Field>
          </div>
          <Field label="My age" htmlFor={`${uid}-myage`}>
            <MyAgeField
              id={`${uid}-myage`}
              value={prefs.selfAge}
              errorText={meta.policy_strings.age_range_error}
              onCommit={(v) => set({ selfAge: v })}
            />
          </Field>
        </div>

        {/* m3.0.0: OPTIONAL inputs about the visitor; since m4.0.0 (ADR
            0018) kept in this browser and never sent. Education unset means
            the average for the visitor's sex and age; race is used only
            when a group is chosen, and never on a same-sex search (there
            the select keeps its value, set aside). Stacked, not side by
            side: the registry's option wording ("Prefer not to say", "High
            school or less") does not fit a half-width select in the 360px
            panel. Labels and levels come from /v1/meta. */}
        <div data-variant="">
          <Field label={policy.self_edu_label} htmlFor={`${uid}-selfedu`}>
            <select
              id={`${uid}-selfedu`}
              className="ctl"
              data-testid="self-edu"
              value={about.edu ?? ""}
              onChange={(e) =>
                onAbout({ ...about, edu: (e.target.value || undefined) as SelfEdu | undefined })
              }
            >
              <option value="">{policy.prefer_not_to_say}</option>
              {SELF_EDU_LEVELS.map((lv) => (
                <option key={lv} value={lv}>{policy[`edu_${lv}`]}</option>
              ))}
            </select>
          </Field>
        </div>
        <div data-variant="">
          <Field label={policy.self_race_label} htmlFor={`${uid}-selfrace`}>
            <select
              id={`${uid}-selfrace`}
              className="ctl"
              data-testid="self-race"
              value={about.race ?? ""}
              disabled={sameSex}
              onChange={(e) => onAbout({ ...about, race: e.target.value || undefined })}
            >
              <option value="">{policy.prefer_not_to_say}</option>
              {raceGroups.map((g) => (
                <option key={g.id} value={g.id}>{g.label}</option>
              ))}
            </select>
          </Field>
        </div>
      </Section>

      <Section heading={policy.panel_looking_for_heading} testid="looking-for-section" divided>
        <Field label="I'm looking for" htmlFor={`${uid}-seek`}>
          <select
            id={`${uid}-seek`}
            className="ctl"
            data-testid="seek-sex"
            value={prefs.seekSex}
            onChange={(e) => onSeekSex(e.target.value as "male" | "female")}
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

        {/* Nothing editorial here — label, boxes, clear-all. Eight equal
            groups since m2.2.0 (ADR 0006): the selection is the filter,
            and zero or all eight ticked means everyone. */}
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
            {raceGroups.map((g) => {
              const on = raceSelected.includes(g.id);
              return (
                <label key={g.id} className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="check"
                    checked={on}
                    onChange={(e) => {
                      const cur = new Set(prefs.race ?? allIds);
                      if (e.target.checked) cur.add(g.id);
                      else cur.delete(g.id);
                      // all eight or none = no filter; the model treats
                      // both as everyone, and the URL says so honestly
                      const next = allIds.filter((x) => cur.has(x));
                      set({
                        race:
                          next.length === 0 || next.length === allIds.length
                            ? undefined
                            : next,
                      });
                    }}
                  />
                  {g.label}
                </label>
              );
            })}
          </div>
        </fieldset>
      </Section>

      {/* Phase 2f item 4.5: the slider sits WITH the other weighting
          control — one bordered group, the slider immediately above
          "How much do these matter?" — instead of opening the panel.
          The search fields above it keep their order untouched. */}
      <div className="flex flex-col gap-5 border-t border-rule pt-5" data-testid="weighting">
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center gap-2">
            <label htmlFor={`${uid}-svo`} className="text-sm font-semibold">
              What matters more to you?
            </label>
            {/* Phase 4b: the one explanation of the compatibility figure
                (the figure has no box of its own); a same-sex search adds
                the served sentence saying whose pairing patterns it uses */}
            <InfoTip
              id={`${uid}-svo-info`}
              label="What the slider changes"
              testid="slider-info"
            >
              {meta.policy_strings.slider_info}
              {sameSex && sameSexNote ? (
                <>
                  {" "}
                  <span className="mt-2 block" data-testid="slider-same-sex-note">
                    {sameSexNote}
                  </span>
                </>
              ) : null}
            </InfoTip>
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
            aria-valuetext={`${Math.round(s * 100)} percent toward ${poles.high.toLowerCase()}`}
            onChange={(e) => set({ poolVsMatch: parseFloat(e.target.value) })}
          />
          <div className="flex justify-between text-[12.5px] font-semibold text-ink-2" data-testid="slider-poles">
            <span>{poles.low}</span>
            <span>{poles.high}</span>
          </div>
          {sameSex && (
            <p className="text-[12.5px] leading-relaxed text-ink-3">
              {meta.policy_strings.balance_same_sex}
            </p>
          )}
        </div>

        {/* Item 4 (2d): FOUR controls, labels and subtitles from the
            registry through /v1/meta — the frontend still sends choices,
            never weights. */}
        <div className="flex flex-col gap-3" data-testid="importance">
          <p className="text-sm font-semibold">How much do these matter?</p>
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
    </div>
  );
}

/** Item 8: a real editable number field — click in, type 34, tab away.
 * The draft is validated on BLUR, never per keystroke (per-keystroke
 * clamping turned typing "34" into 18 then 70: the "3" clamped before
 * the "4" arrived). Out-of-range or empty shows the registry's message
 * and keeps the last good value. */
function MyAgeField({
  id,
  value,
  errorText,
  onCommit,
}: {
  id: string;
  value: number;
  errorText: string;
  onCommit: (v: number) => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const [invalid, setInvalid] = useState(false);
  return (
    <>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        className="ctl"
        min={18}
        max={70}
        data-testid="my-age"
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? `${id}-err` : undefined}
        value={draft ?? String(value)}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => {
          if (draft === null) return;
          const v = parseInt(draft, 10);
          if (Number.isFinite(v) && v >= 18 && v <= 70) {
            setInvalid(false);
            setDraft(null);
            if (v !== value) onCommit(v);
          } else {
            setInvalid(true);
            setDraft(null); // fall back to the last good value
          }
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
        }}
      />
      {invalid && (
        <p id={`${id}-err`} role="status" data-testid="my-age-error"
           className="pt-1 text-[12px] leading-snug text-poor">
          {errorText}
        </p>
      )}
    </>
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
