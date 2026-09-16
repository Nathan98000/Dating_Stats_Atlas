"use client";

import { useId } from "react";
import type { Meta } from "@/lib/types";
import { PILLARS, type Prefs } from "@/lib/prefs";

const MARITAL_LABELS: Record<string, string> = {
  never_married: "Never married",
  previously_married: "Previously married",
  currently_married: "Currently married",
};
const EDU_LABELS: Record<string, string> = {
  some_college: "Some college or more",
  bachelors: "Bachelor's or more",
  graduate: "Graduate degree",
};
const RACE_LABELS: Record<string, string> = {
  hispanic: "Hispanic or Latino",
  white_nh: "White (non-Hispanic)",
  black_nh: "Black (non-Hispanic)",
  asian_nh: "Asian (non-Hispanic)",
  aian_nh: "American Indian or Alaska Native (non-Hispanic)",
  nhpi_nh: "Native Hawaiian or Pacific Islander (non-Hispanic)",
  two_or_more_nh: "Two or more races (non-Hispanic)",
  other_nh: "Some other race (non-Hispanic)",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-xs font-semibold text-ink-3">{label}</span>
      {children}
    </label>
  );
}

const selectCls =
  "border border-rule bg-raised px-2 py-1.5 text-sm text-ink";

/** The controls (§10.2/§10.3): beside the results, the size-versus-odds
 * slider as the hero, per-pillar weights in a fine-tune disclosure below,
 * identity filters off by default in a secondary group (§10.4, D02).
 * The income control offers only cube band edges — anything else 422s. */
export function Controls({
  prefs,
  meta,
  onChange,
}: {
  prefs: Prefs;
  meta: Meta;
  onChange: (next: Prefs) => void;
}) {
  const sliderId = useId();
  const svo = meta.model_defaults.size_vs_odds;
  const sliderValue = prefs.weights
    ? undefined
    : (prefs.sizeVsOdds ?? svo.default_s);
  const set = (patch: Partial<Prefs>) => onChange({ ...prefs, ...patch });

  return (
    <div className="flex flex-col gap-6">
      {/* hero control */}
      <div>
        <label htmlFor={sliderId} className="mb-1 block text-sm font-semibold text-ink">
          What matters more to you?
        </label>
        <input
          id={sliderId}
          type="range"
          className="svo"
          min={0}
          max={1}
          step={0.05}
          disabled={prefs.weights !== undefined}
          value={sliderValue ?? svo.default_s}
          aria-valuetext={
            sliderValue === undefined
              ? "custom weights active"
              : `${Math.round((sliderValue ?? 0) * 100)} percent toward best odds`
          }
          onChange={(e) =>
            set({ sizeVsOdds: parseFloat(e.target.value), weights: undefined })
          }
        />
        <div className="mt-1 flex justify-between text-xs text-ink-2">
          <span>{svo.label_low}</span>
          <span>{svo.label_high}</span>
        </div>
        {prefs.weights !== undefined && (
          <p className="mt-1 text-xs text-ink-3">
            Custom weights are active; the slider is off.{" "}
            <button
              type="button"
              className="text-accent underline"
              onClick={() => set({ weights: undefined, sizeVsOdds: svo.default_s })}
            >
              Back to the slider
            </button>
          </p>
        )}
      </div>

      <fieldset className="flex flex-col gap-3">
        <legend className="mb-1 text-xs font-semibold text-ink-3">About you</legend>
        <div className="grid grid-cols-2 gap-3">
          <Field label="You are">
            <select
              className={selectCls}
              value={prefs.selfSex}
              onChange={(e) => set({ selfSex: e.target.value as Prefs["selfSex"] })}
            >
              <option value="female">A woman</option>
              <option value="male">A man</option>
            </select>
          </Field>
          <Field label="Your age">
            <input
              type="number"
              className={selectCls}
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
      </fieldset>

      <fieldset className="flex flex-col gap-3">
        <legend className="mb-1 text-xs font-semibold text-ink-3">Seeking</legend>
        <Field label="Sex">
          <select
            className={selectCls}
            value={prefs.seekSex ?? "opposite"}
            onChange={(e) =>
              set({
                seekSex:
                  e.target.value === "opposite"
                    ? undefined
                    : (e.target.value as Prefs["seekSex"]),
              })
            }
          >
            <option value="opposite">The opposite sex</option>
            <option value="male">Men</option>
            <option value="female">Women</option>
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Age from">
            <input
              type="number"
              className={selectCls}
              min={18}
              max={70}
              value={prefs.ageMin}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10);
                if (Number.isFinite(v)) set({ ageMin: Math.min(prefs.ageMax, Math.max(18, v)) });
              }}
            />
          </Field>
          <Field label="to">
            <input
              type="number"
              className={selectCls}
              min={18}
              max={70}
              value={prefs.ageMax}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10);
                if (Number.isFinite(v)) set({ ageMax: Math.max(prefs.ageMin, Math.min(70, v)) });
              }}
            />
          </Field>
        </div>
        <fieldset>
          <legend className="mb-1 text-xs font-semibold text-ink-3">Marital status</legend>
          <div className="flex flex-col gap-1">
            {meta.controls.marital.map((m) => (
              <label key={m} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={prefs.marital.includes(m)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...prefs.marital, m]
                      : prefs.marital.filter((x) => x !== m);
                    if (next.length) set({ marital: next });
                  }}
                />
                {MARITAL_LABELS[m]}
              </label>
            ))}
          </div>
        </fieldset>
        <Field label="Education (minimum)">
          <select
            className={selectCls}
            value={prefs.educationMin ?? ""}
            onChange={(e) => set({ educationMin: e.target.value || undefined })}
          >
            <option value="">Any education</option>
            {["some_college", "bachelors", "graduate"].map((e) => (
              <option key={e} value={e}>
                {EDU_LABELS[e]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Income (minimum)">
          {/* a select over the cube's band edges — free text would 422 */}
          <select
            className={selectCls}
            value={prefs.incomeMin ?? ""}
            onChange={(e) =>
              set({ incomeMin: e.target.value ? parseInt(e.target.value, 10) : undefined })
            }
          >
            <option value="">Any income</option>
            {meta.controls.income_band_edges.map((edge) => (
              <option key={edge} value={edge}>
                ${edge.toLocaleString("en-US")}+
              </option>
            ))}
          </select>
        </Field>
      </fieldset>

      {/* identity controls: off by default, secondary, never a funnel step */}
      <details data-testid="identity-controls">
        <summary className="cursor-pointer text-sm font-semibold text-ink">
          Race &amp; ethnicity <span className="font-normal text-ink-3">(optional)</span>
        </summary>
        <div className="mt-2 flex flex-col gap-1 border-l-2 border-rule pl-3">
          <p className="mb-1 max-w-[40ch] text-xs text-ink-2">
            A filter describes your preference, in your session. Whenever one
            is on, each metro also shows how partnered people of that group
            there actually pair — {meta.policy_strings.pairing_framing}
          </p>
          {meta.controls.race_ethnicity.map((r) => (
            <label key={r} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={prefs.race?.includes(r) ?? false}
                onChange={(e) => {
                  const cur = prefs.race ?? [];
                  const next = e.target.checked
                    ? [...cur, r]
                    : cur.filter((x) => x !== r);
                  set({ race: next.length ? next : undefined });
                }}
              />
              {RACE_LABELS[r] ?? r}
            </label>
          ))}
        </div>
      </details>

      {/* fine-tune (§10.3): individual pillar weights live below the fold */}
      <details data-testid="fine-tune">
        <summary className="cursor-pointer text-sm font-semibold text-ink">
          Fine-tune the five weights
        </summary>
        <div className="mt-2 flex flex-col gap-2 border-l-2 border-rule pl-3">
          {PILLARS.map((p) => {
            const w =
              prefs.weights?.[p] ?? meta.model_defaults.pillar_weights[p];
            return (
              <label key={p} className="grid grid-cols-[7rem_1fr_3rem] items-center gap-2 text-sm">
                <span>{meta.pillars[p].display_name}</span>
                <input
                  type="range"
                  className="svo"
                  min={0}
                  max={0.6}
                  step={0.01}
                  value={w}
                  onChange={(e) => {
                    const base =
                      prefs.weights ??
                      Object.fromEntries(
                        PILLARS.map((k) => [k, meta.model_defaults.pillar_weights[k]]),
                      );
                    set({
                      weights: { ...base, [p]: parseFloat(e.target.value) },
                      sizeVsOdds: undefined,
                    });
                  }}
                />
                <span className="num text-xs text-ink-2">{(w * 100).toFixed(0)}%</span>
              </label>
            );
          })}
          <p className="text-xs text-ink-3">
            Weights are normalized to sum to one; the mix is what matters.
          </p>
        </div>
      </details>
    </div>
  );
}
