/** The browser's side of ADR 0018: the server computes every "about you"
 * variant of a search and this module SELECTS one — it copies the API's
 * numbers into the rows the components render and never computes a
 * ranking number. A line-for-line mirror of atlas.model.variants
 * .select_variant; tests/variants.test.ts holds the two equal on cases
 * the Python model emits. Plain module: the server uses it for the
 * default variant (the first paint) and to cut a page's slice. */
import { effectiveSex, raceUsed, type AboutYou } from "./about-you";
import type {
  Band,
  MatchBlock,
  RankedRow,
  RankResponse,
  Stat,
  VariantColumns,
  VariantResponse,
} from "./types";

/** the compatibility figure's position in every row's stats (the model
 * asserts pool_size first, match_propensity second) */
export const MATCH_COLUMN = 1;
const COLUMNS = ["order", "rank", "score", "score_display", "value", "display",
  "capped", "band", "standing", "z", "contribution", "explain"] as const;

export function variantIndex(resp: VariantResponse, about: AboutYou): number {
  const V = resp.variants;
  const sex = effectiveSex(about, V.sought_sex);
  return V.index[sex][about.edu ?? "none"][raceUsed(about) ?? "off"];
}

export function selectVariant(resp: VariantResponse, about: AboutYou): RankResponse {
  const V = resp.variants;
  const sex = effectiveSex(about, V.sought_sex);
  const vi = variantIndex(resp, about);
  const same = sex === V.sought_sex;
  const bal = V.balance; // the search's, whoever is searching (m4.1.0)
  const c = V.columns;
  const rows: RankedRow[] = [];
  if (resp.ranked.length) {
    const order = c.order[vi];
    const capped = new Set(c.capped[vi]);
    for (let p = 0; p < order.length; p++) {
      const b = order[p];
      const base = resp.ranked[b];
      const match: MatchBlock = {
        available: base.match.available,
        value: c.value[vi][p],
        display: c.display[vi][p],
        capped: capped.has(p),
        unit_line: base.match.unit_line,
      };
      if (same) match.note = V.same_sex_note;
      const stats: Stat[] = base.stats.slice();
      const bandIx = c.band[vi][p];
      let band: Band | undefined;
      if (bandIx !== null) {
        const bd = V.match_bands[bandIx];
        band = { key: bd.key, standing_all: c.standing[vi][p] as number,
                 label: bd.label, tone: bd.tone };
        match.band = band;
      }
      if (!stats[MATCH_COLUMN].missing) {
        const entry: Stat = {
          ...stats[MATCH_COLUMN],
          value: c.value[vi][p],
          display: c.display[vi][p] ?? undefined,
          standing: c.standing[vi][p] ?? undefined,
          z: c.z[vi][p] ?? undefined,
          contribution: c.contribution[vi][p],
        };
        if (band) entry.band = band;
        stats[MATCH_COLUMN] = entry;
      }
      const ex = V.explain[c.explain[vi][p]];
      rows.push({
        ...base,
        rank: c.rank[vi][p],
        score: c.score[vi][p],
        score_display: c.score_display[vi][p],
        balance: bal.ranked[b],
        match,
        stats,
        contributions: base.contributions.map((x) =>
          x.pillar === "match" ? { pillar: "match", value: c.contribution[vi][p] as number } : x),
        top_stats: ex.top_stats,
        summary_line: ex.summary_line,
        movers: ex.movers,
      });
    }
  }
  if (resp.sort === "worst_first") rows.reverse();
  return {
    data_version: resp.data_version,
    model_version: resp.model_version,
    permalink: resp.permalink,
    sort: resp.sort,
    counts: resp.counts,
    weights: resp.weights,
    few_metros_notice: resp.few_metros_notice,
    shown_unranked: resp.shown_unranked,
    balance_words: bal.balance_words,
    match_inputs: V.list[vi].match_inputs,
    ranked: rows,
    suppressed: resp.suppressed.map((r, j) => ({ ...r, balance: bal.suppressed[j] })),
  };
}

/** A page that shows a few cities (the city page, the compare page) needs
 * only their rows: the same response cut down to them — every variant's
 * values for those cities, their ranks as served (in the whole list),
 * their balance. Data plumbing on the server; the browser selects from
 * the slice exactly as from the whole. */
export function sliceVariants(resp: VariantResponse, cbsas: string[]): VariantResponse {
  const want = new Set(cbsas);
  const keep = resp.ranked.flatMap((r, i) => (want.has(r.cbsa) ? [i] : []));
  const remap = new Map(keep.map((b, j) => [b, j]));
  const V = resp.variants;
  const c = V.columns;
  const positions = c.order.map((o) => o.flatMap((b, p) => (remap.has(b) ? [p] : [])));
  const used = new Map<number, number>();
  const explain: typeof V.explain = [];
  const cols = {} as VariantColumns;
  for (const name of COLUMNS) {
    if (name === "order") {
      cols.order = c.order.map((o, vi) => positions[vi].map((p) => remap.get(o[p]) as number));
    } else if (name === "capped") {
      cols.capped = c.capped.map((cp, vi) => {
        const set = new Set(cp);
        return positions[vi].flatMap((p, q) => (set.has(p) ? [q] : []));
      });
    } else if (name === "explain") {
      cols.explain = c.explain.map((col, vi) => positions[vi].map((p) => {
        const e = col[p];
        if (!used.has(e)) {
          used.set(e, explain.length);
          explain.push(V.explain[e]);
        }
        return used.get(e) as number;
      }));
    } else {
      // every other column is values in the variant's rank order
      (cols as unknown as Record<string, unknown[][]>)[name] =
        (c as unknown as Record<string, unknown[][]>)[name].map(
          (col, vi) => positions[vi].map((p) => col[p]));
    }
  }
  const supKeep = resp.suppressed.flatMap((r, j) => (want.has(r.cbsa) ? [j] : []));
  const balance = {
    ...V.balance,
    ranked: keep.map((b) => V.balance.ranked[b]),
    suppressed: supKeep.map((j) => V.balance.suppressed[j]),
  };
  return {
    ...resp,
    ranked: keep.map((b) => resp.ranked[b]),
    suppressed: supKeep.map((j) => resp.suppressed[j]),
    variants: { ...V, explain, balance, columns: cols },
  };
}
