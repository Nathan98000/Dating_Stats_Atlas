import { fmtInt, ordinal } from "@/lib/format";

/** A population figure with its margin IN THE ROW, in the policy's exact
 * words: "margin at least ±N" — never a bare "±", never a tooltip, never
 * hover (acceptance gate 1). Screen readers get a supplementary sentence
 * saying the margin is an upper bound, so the figure cannot be mistaken
 * for a precise one (gate 4). */
export function PoolFigure({
  pool,
  moe,
  marginWords,
  label,
  size = "md",
}: {
  pool: number;
  moe: number;
  marginWords: string; // policy_strings.margin_row, rendered verbatim
  label: string; // legend display name, e.g. "Compatible people"
  size?: "md" | "lg";
}) {
  return (
    <span data-figure="pool">
      <span className={size === "lg" ? "num text-lg font-semibold text-ink" : "num font-semibold text-ink"}>
        {fmtInt(pool)}
      </span>{" "}
      <span className="text-ink-2">{label.toLowerCase()}</span>
      <span className="text-ink-3" aria-hidden="true"> · </span>
      <span className="whitespace-nowrap text-ink-2">
        {marginWords} <span className="num">±{fmtInt(moe)}</span>
      </span>
      <span className="sr-only">
        . The margin of error is at least plus or minus {fmtInt(moe)} — a
        calibrated upper bound, not a precise figure.
      </span>
    </span>
  );
}

/** Standing as a strip-plot mark: a dot on a hairline at the percentile of
 * the query's ranked set. A statistical mark, not a gauge. */
export function StandingMark({ pct }: { pct: number }) {
  return (
    <span
      className="relative inline-block h-3 w-24 align-middle"
      role="img"
      aria-label={`${ordinal(pct)} percentile of ranked metros`}
    >
      <span aria-hidden="true" className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2 bg-rule" />
      <span
        aria-hidden="true"
        className="absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent"
        style={{ left: `${pct}%` }}
      />
    </span>
  );
}

const FLAG_LABELS: Record<string, string> = {
  low_allocation_purity: "allocation shared with other areas",
  gq_flag: "large group-quarters population",
};

/** Row flags, spelled out — the policy string is in the accessible text,
 * never a tooltip. */
export function FlagChips({
  flags,
  policy,
}: {
  flags: string[];
  policy: Record<string, string>;
}) {
  if (!flags.length) return null;
  return (
    <span className="flex flex-wrap gap-2">
      {flags.map((f) => {
        const missing = f.startsWith("missing_features:");
        const key = missing ? "missing_features" : f;
        const label = missing
          ? `some stats unavailable (${f.split(":")[1].split(";").join(", ")})`
          : (FLAG_LABELS[f] ?? f);
        return (
          <span key={f} className="border border-warn px-2 py-0.5 text-xs text-warn">
            {label}
            <span className="sr-only"> — {policy[key] ?? ""}</span>
          </span>
        );
      })}
    </span>
  );
}
