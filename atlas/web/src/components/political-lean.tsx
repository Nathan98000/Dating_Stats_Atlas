import Link from "next/link";
import type { Meta, PoliticalLeanBlock } from "@/lib/types";

/** Political lean (Phase 4d, ADR 0019, Nathan's decision): how the metro
 * area voted in the 2024 presidential election — context only, never
 * scored, never a filter or a weight, never asked of the visitor. Every
 * number and word is the API's (GET /v1/political_lean) or the
 * registry's (via /v1/meta): the component arranges them and computes
 * nothing. The neutrality rules hold here: the parties' names and the
 * numbers only, Democratic always before Republican (the everyone-else
 * share between them on the bar), no band word, no tone, and colour
 * never the only cue — each segment's name sits under the bar in text,
 * and the bar itself is announced with all three shares. */

const SEGMENT_BG: Record<string, string> = {
  dem: "bg-dem",
  other: "bg-lean-other",
  rep: "bg-rep",
};

/** The split bar: three segments in the API's order, sized by the share
 * the API sends (in percent), a thin surface-coloured gap between them. */
export function LeanBar({ block }: { block: Extract<PoliticalLeanBlock, { available: true }> }) {
  return (
    <div
      role="img"
      aria-label={block.bar_label}
      data-testid="lean-bar"
      className="flex h-2.5 w-full gap-[2px] overflow-hidden rounded-full"
    >
      {block.segments.map((s) => (
        <span
          key={s.key}
          data-segment={s.key}
          className={`h-full ${SEGMENT_BG[s.key]}`}
          style={{ flexGrow: s.width, flexBasis: 0 }}
        />
      ))}
    </div>
  );
}

/** Each segment's name, under the bar in the bar's order, with its colour
 * as a swatch beside it. */
export function LeanKey({ block }: { block: Extract<PoliticalLeanBlock, { available: true }> }) {
  return (
    <span className="flex flex-wrap gap-x-3 gap-y-0.5 text-[12px] text-ink-2" data-testid="lean-key">
      {block.segments.map((s) => (
        <span key={s.key} className="inline-flex items-center gap-1.5" data-key={s.key}>
          <span aria-hidden="true" className={`inline-block h-2.5 w-2.5 rounded-sm ${SEGMENT_BG[s.key]}`} />
          {s.label}
        </span>
      ))}
    </span>
  );
}

/** The city page's card, on the stat grid's six subgrid rows (name / value
 * / caption / bar / key / link) so it lines up with its neighbours. */
export function PoliticalLeanCard({ block, meta }: { block: PoliticalLeanBlock | undefined; meta: Meta }) {
  const le = meta.features.political_lean;
  if (!le || !block) return null;
  const statName = (le.stat_page_name ?? le.display_name).toLowerCase();
  return (
    <div className="stat-card rounded-xl border border-rule bg-surface p-[18px]" data-card="political_lean">
      <span className="text-[13px] font-semibold text-ink-2">{le.display_name}</span>
      {block.available ? (
        <>
          <span
            className="font-display text-[19px] font-semibold leading-snug [text-wrap:balance]"
            data-testid="lean-text"
          >
            {block.text}
          </span>
          <span className="unit-line text-[12.5px] text-ink-3" data-testid="lean-caption">
            {le.unit}
          </span>
          <div className="pt-0.5">
            <LeanBar block={block} />
          </div>
          <LeanKey block={block} />
          {meta.stat_pages.includes("political_lean") ? (
            <Link
              href="/stats/political_lean"
              className="self-start text-[12.5px] font-semibold text-accent hover:text-accent-hover"
            >
              {meta.policy_strings.stat_page_link.replace("{name}", statName)}
            </Link>
          ) : (
            <span aria-hidden="true" />
          )}
        </>
      ) : (
        <>
          {/* the other cards' blank state: the name, the one line, the
              remaining rows empty */}
          <span className="text-sm text-ink-3" data-testid="lean-missing">
            {block.note}
          </span>
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
        </>
      )}
    </div>
  );
}

/** A compare-table cell: the same text the card shows, or "Not available". */
export function PoliticalLeanCell({ block }: { block: PoliticalLeanBlock | undefined }) {
  return (
    <td className="px-5 py-3.5" data-lean-cell="">
      {block?.available ? (
        <span className="text-[15px] font-semibold">{block.text}</span>
      ) : (
        <span className="text-[12.5px] text-ink-3">{block?.note}</span>
      )}
    </td>
  );
}
