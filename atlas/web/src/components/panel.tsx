"use client";

import { useId, useRef, useState } from "react";
import type { Meta } from "@/lib/types";
import { filtersSummary, IMPORTANCE_PILLARS, SELF_EDU_LEVELS, type Level, type Prefs,
  type SelfEdu } from "@/lib/prefs";
import type { AboutYou } from "@/lib/about-you";
import { InfoTip } from "./info-tip";
import { Segmented } from "./segmented";

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

export function Field({ label, htmlFor, children }: {
  label: string; htmlFor?: string; children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-caption font-semibold text-ink-2">
        {label}
      </label>
      {children}
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"
      className={`shrink-0 text-ink-3 transition-transform ${open ? "rotate-180" : ""}`}
      fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
      <path d="M4 6l4 4 4-4" />
    </svg>
  );
}

/** A collapsible rail group: its heading holds the disclosure button
 * (aria-expanded), so a screen reader meets it by heading and by state.
 * Collapsed, `summary` says what the group holds now. */
function Disclosure({ heading, testid, summary, children }: {
  heading: string; testid: string; summary: React.ReactNode; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <section data-testid={testid} className="border-t border-rule pt-4">
      <h2 className="font-display text-body-lg font-semibold">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen(!open)}
          className="flex min-h-11 w-full items-center justify-between gap-3 text-left desk:min-h-8"
        >
          {heading}
          <Chevron open={open} />
        </button>
      </h2>
      <div className="mt-1 text-caption text-ink-3">{summary}</div>
      <div id={id} hidden={!open} className="mt-4 flex flex-col gap-4">
        {children}
      </div>
    </section>
  );
}

/** Phase 5's search rail (the design audit of 8 October 2026), replacing
 * the v3 panel: three groups, each a heading. "What matters to you" is
 * always open — the bigger-pool-or-closer-match slider and the four
 * importance controls, each a segmented radiogroup. "Narrow it down" and
 * "Sharpen compatibility" start collapsed, each with a line saying what it
 * holds. Sends choices, never weights (item 5). The visitor's own sex and
 * ages moved to the hero's quick search; their own education and race
 * (m4.0.0, ADR 0018: kept in this browser and never sent) live under
 * Sharpen compatibility, with Phase 4c's same-sex behaviour unchanged.
 * Rendered once: in the sticky rail from 1120px, in the sheet or drawer
 * below that. */
export function RailGroups({
  prefs,
  meta,
  onChange,
  sameSex,
  sameSexNote,
  about,
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
  // registry through /v1/meta — the rail types no race wording
  const raceGroups = meta.race_groups;
  const allIds = raceGroups.map((g) => g.id);
  const raceSelected = prefs.race ?? allIds;

  return (
    <div className="flex flex-col gap-4" data-testid="search-panel">
      <section className="flex flex-col gap-4" data-testid="weighting">
        <h2 className="font-display text-h3">{policy.rail_matters_heading}</h2>
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-1">
            <label htmlFor={`${uid}-svo`} className="text-caption font-semibold text-ink-2">
              {policy.slider_label}
            </label>
            {/* Phase 4b: the one explanation of the compatibility figure
                (the figure has no box of its own); a same-sex search adds
                the served sentence saying whose pairing patterns it uses */}
            <InfoTip id={`${uid}-svo-info`} label="What the slider changes" testid="slider-info">
              {policy.slider_info}
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
          <div className="flex justify-between text-caption font-semibold text-ink-2" data-testid="slider-poles">
            <span>{poles.low}</span>
            <span>{poles.high}</span>
          </div>
        </div>

        {/* Item 4 (2d): FOUR controls, labels and subtitles from the
            registry through /v1/meta — the frontend sends choices, never
            weights. */}
        <div className="flex flex-col gap-4" data-testid="importance">
          {IMPORTANCE_PILLARS.map((pillar) => (
            <ImportanceRow
              key={pillar}
              label={meta.pillars[pillar]?.display_name ?? pillar}
              subtitle={meta.pillars[pillar]?.control_subtitle ?? ""}
              value={prefs.importance[pillar]}
              onPick={(lv) => set({ importance: { ...prefs.importance, [pillar]: lv } })}
            />
          ))}
        </div>
      </section>

      <Disclosure
        heading={policy.rail_narrow_heading}
        testid="looking-for-section"
        summary={<span data-testid="filters-summary">{filtersSummary(prefs)}</span>}
      >
        <fieldset>
          <legend className="mb-1.5 text-caption font-semibold text-ink-2">Single means</legend>
          <div className="flex flex-wrap gap-2">
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
                  className={`flex h-11 items-center gap-1.5 rounded-full px-3.5 text-body-sm desk:h-9 ${on
                    ? "border-[1.5px] border-accent bg-tint font-semibold text-accent-hover"
                    : "border border-line-strong bg-surface font-medium text-ink-2 hover:text-ink"}`}
                  onClick={() => {
                    const next = on
                      ? prefs.marital.filter((m) => m !== v)
                      : [...prefs.marital, v];
                    // one must stay on: no marital status is no search
                    if (next.length) set({ marital: next });
                  }}
                >
                  {on && <CheckIcon />}
                  {label}
                </button>
              );
            })}
          </div>
        </fieldset>

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

        {/* Nothing editorial here — label, boxes, clear-all. Eight equal
            groups since m2.2.0 (ADR 0006): the selection is the filter,
            and zero or all eight ticked means everyone. */}
        <fieldset data-testid="race-panel">
          <div className="mb-1 flex items-baseline justify-between">
            <legend className="text-caption font-semibold text-ink-2">
              Race &amp; ethnicity
            </legend>
            {prefs.race?.length ? (
              <button
                type="button"
                className="min-h-11 text-caption font-semibold text-accent underline underline-offset-2 desk:min-h-0"
                onClick={() => set({ race: undefined })}
              >
                Include all
              </button>
            ) : null}
          </div>
          <div className="grid grid-cols-1">
            {raceGroups.map((g) => {
              const on = raceSelected.includes(g.id);
              return (
                <label key={g.id} className="flex min-h-11 cursor-pointer items-center gap-2.5 text-body-sm desk:min-h-8">
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
      </Disclosure>

      <Disclosure
        heading={policy.rail_sharpen_heading}
        testid="about-you-section"
        summary={
          // after the Phase 5 report (Nathan): the pill alone, no note
          <span className="inline-flex h-[22px] items-center rounded-full bg-sunken px-2 text-overline tracking-normal text-ink-2">
            {policy.optional_pill}
          </span>
        }
      >
        {/* m3.0.0: OPTIONAL inputs about the visitor; since m4.0.0 (ADR
            0018) kept in this browser and never sent. Education unset means
            the average for the visitor's sex and age; race is used only
            when a group is chosen, and never on a same-sex search (Phase
            4c: there the select stays operable, muted and explained —
            SelfRaceField). Labels and levels come from /v1/meta. */}
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
          <SelfRaceField
            id={`${uid}-selfrace`}
            label={policy.self_race_label}
            value={about.race ?? ""}
            sameSex={sameSex}
            tip={policy.self_race_same_sex_tip}
            tipLabel={policy.self_race_same_sex_tip_label}
            preferNotToSay={policy.prefer_not_to_say}
            groups={raceGroups}
            onPick={(race) => onAbout({ ...about, race })}
          />
        </div>
      </Disclosure>
    </div>
  );
}

export function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" className="shrink-0"
      fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2.5 7.5l3 3 6-7" />
    </svg>
  );
}

/** "My race or ethnicity" (Phase 4c, Nathan's change 1; ADR 0018
 * amended). A same-sex search uses no race (ADR 0018 §3), yet the select
 * stays operable — never disabled or aria-disabled: a choice is stored as
 * usual, changes nothing on this search, and applies as soon as the search
 * is opposite-sex again. There the field is muted (grey text on paper, a
 * dashed border; every colour holds WCAG AA) and the registry's tip says
 * why: it shows while the pointer is over the field or the select has
 * keyboard focus, Escape dismisses it, and it is always the select's
 * description (aria-describedby), so a screen reader announces it. A touch
 * screen has no hover: there an information button beside the label opens
 * the same text (InfoTip; the CSS shows it only under (hover: none)). An
 * opposite-sex search gets the plain field, no tip. */
export function SelfRaceField({
  id,
  label,
  value,
  sameSex,
  tip,
  tipLabel,
  preferNotToSay,
  groups,
  onPick,
}: {
  id: string;
  label: string;
  value: string;
  sameSex: boolean;
  tip: string;
  tipLabel: string;
  preferNotToSay: string;
  groups: { id: string; label: string }[];
  onPick: (race: string | undefined) => void;
}) {
  const [hover, setHover] = useState(false);
  const [focus, setFocus] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const open = sameSex && (hover || focus) && !dismissed;
  const tipId = `${id}-tip`;
  return (
    <div
      className="relative flex flex-col gap-1.5"
      data-testid="self-race-field"
      data-muted={sameSex ? "" : undefined}
      onPointerEnter={(e) => {
        if (e.pointerType !== "touch") setHover(true);
      }}
      onPointerLeave={(e) => {
        if (e.pointerType !== "touch") {
          setHover(false);
          setDismissed(false);
        }
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape" && open) {
          e.stopPropagation();
          setDismissed(true);
        }
      }}
    >
      <div className="flex items-center gap-2">
        <label
          htmlFor={id}
          className={`text-caption font-semibold ${sameSex ? "text-ink-3" : "text-ink-2"}`}
        >
          {label}
        </label>
        {sameSex && (
          <span className="touch-only">
            <InfoTip id={`${id}-touch-tip`} label={tipLabel} testid="self-race-tip-button">
              {tip}
            </InfoTip>
          </span>
        )}
      </div>
      <select
        id={id}
        className={sameSex ? "ctl ctl-muted" : "ctl"}
        data-testid="self-race"
        value={value}
        aria-describedby={sameSex ? tipId : undefined}
        onFocus={(e) => {
          // keyboard focus only: a click already hovers, and a tap on a
          // touch screen has the information button
          setFocus(keyboardFocus(e.currentTarget));
          setDismissed(false);
        }}
        onBlur={() => {
          setFocus(false);
          setDismissed(false);
        }}
        onChange={(e) => onPick(e.target.value || undefined)}
      >
        <option value="">{preferNotToSay}</option>
        {groups.map((g) => (
          <option key={g.id} value={g.id}>{g.label}</option>
        ))}
      </select>
      {sameSex && (
        // always in the page as the select's description; seen only while
        // open. The padding bridges the gap, so the pointer can move from
        // the field onto the box without it closing.
        <span
          className={open ? "absolute inset-x-0 top-full z-40 pt-2" : "hidden"}
          data-testid="self-race-tip-bridge"
        >
          <span
            id={tipId}
            role="tooltip"
            data-testid="self-race-tip"
            className="block rounded-lg border border-rule bg-surface px-3.5 py-3 text-left text-caption font-normal text-ink-2 shadow-overlay"
          >
            {tip}
          </span>
        </span>
      )}
    </div>
  );
}

/** Whether an element's focus came from the keyboard (:focus-visible); a
 * browser without the selector counts every focus. */
function keyboardFocus(el: HTMLElement): boolean {
  try {
    return el.matches(":focus-visible");
  } catch {
    return true;
  }
}

/** Item 8: a real editable number field — click in, type 34, tab away.
 * The draft is validated on BLUR, never per keystroke (per-keystroke
 * clamping turned typing "34" into 18 then 70: the "3" clamped before
 * the "4" arrived). Out-of-range or empty shows the registry's message
 * and keeps the last good value. */
export function MyAgeField({
  id,
  value,
  errorText,
  onCommit,
  tokenClass = "",
}: {
  id: string;
  value: number;
  errorText: string;
  onCommit: (v: number) => void;
  /** extra classes (the quick search's sentence token) */
  tokenClass?: string;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const [invalid, setInvalid] = useState(false);
  return (
    <>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        className={`ctl ${tokenClass}`}
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
           className="pt-1 text-caption text-error">
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
    <div className="flex flex-col gap-1.5">
      <span className="flex flex-col">
        <span className="text-caption font-semibold text-ink-2">{label}</span>
        {subtitle ? <span className="text-caption text-ink-3">{subtitle}</span> : null}
      </span>
      <Segmented label={`${label} importance`} options={LEVELS} value={value} onChange={onPick} />
    </div>
  );
}

/** The two-handle age control (StatesV3): one visual track, two range
 * inputs, each handle separately labelled and keyboard-movable one year at
 * a time; handles can meet but not cross. */
export function AgeRange({
  prefs,
  onChange,
  exact = false,
}: {
  prefs: Prefs;
  onChange: (next: Prefs) => void;
  /** Phase 6 (F02): two number fields for exact ages under the track */
  exact?: boolean;
}) {
  const uid = useId();
  const lo = useRef<HTMLInputElement>(null);
  const MIN = 18;
  const MAX = 70;
  const pct = (v: number) => ((v - MIN) / (MAX - MIN)) * 100;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between">
        <span id={`${uid}-lab`} className="text-caption font-semibold text-ink-2">
          Aged
        </span>
        <output className="text-body font-semibold" data-testid="age-output">
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
      <div className="flex justify-between text-caption text-ink-3">
        <span>{MIN}</span>
        <span>{MAX}</span>
      </div>
      {exact && (
        <div className="mt-2 flex items-center gap-2.5 text-body text-ink-2" data-testid="age-exact">
          <span aria-hidden="true">From</span>
          <ExactAge label="Youngest age" value={prefs.ageMin} testid="age-from"
            commit={(v) => onChange({ ...prefs, ageMin: Math.min(v, prefs.ageMax) })} />
          <span aria-hidden="true">to</span>
          <ExactAge label="Oldest age" value={prefs.ageMax} testid="age-to"
            commit={(v) => onChange({ ...prefs, ageMax: Math.max(v, prefs.ageMin) })} />
        </div>
      )}
    </div>
  );
}

/** Phase 6 (F02): an exact age beside the two thumbs — a 48px number field
 * holding the same state. A typed value is kept as typed until Enter or
 * leaving the field, then clamped to 18-70 and to its partner (From <= To);
 * Escape still closes the popover. Labelled as its thumb is. */
function ExactAge({ label, value, testid, commit }: {
  label: string; value: number; testid: string; commit: (v: number) => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const done = () => {
    if (draft === null) return;
    const v = parseInt(draft, 10);
    setDraft(null);
    if (Number.isFinite(v)) {
      const c = Math.min(70, Math.max(18, v));
      if (c !== value) commit(c);
    }
  };
  return (
    <input
      type="number"
      inputMode="numeric"
      min={18}
      max={70}
      aria-label={label}
      data-testid={testid}
      className="ctl min-h-12 w-20 text-center"
      value={draft ?? String(value)}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={done}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          done();
        }
      }}
    />
  );
}
