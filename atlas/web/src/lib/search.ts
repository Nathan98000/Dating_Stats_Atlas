/** ONE city matcher for every place a city is chosen (Phase 2e item 5).
 *
 * The compare pickers shipped with `[e.f, ...e.k].some(t =>
 * t.includes(query))` truncated in INDEX ORDER — alphabetical — so "new
 * york" matched thirteen New-York-State metros and filled all seven
 * slots with upstate cities before reaching New York itself. The header
 * search never had the bug because it scores before truncating. The
 * structural defect was two independent matchers, one unranked; this
 * module is now the only one.
 *
 * Scoring per token: exact 100, prefix ~80, substring ~50, subsequence
 * ~25 — so a name that BEGINS with the query beats one that merely
 * contains it. Queries and tokens are normalised (lowercase, periods
 * stripped) so "st louis" finds "St. Louis". State tokens are capped at
 * STATE_TOKEN_CAP: "washington" must rank the district above every city
 * in Washington State, and "new york" must never rank Albany by its
 * state alone.
 */

export interface CityEntry {
  s: string; // slug
  f: string; // display name full, e.g. "Provo, Utah"
  r: boolean; // in the ranked set
  k: string[]; // city-name tokens and colloquials
  st: string[]; // state tokens (full names and postal codes)
}

const STATE_TOKEN_CAP = 30;

function norm(s: string): string {
  return s.toLowerCase().replace(/\./g, "");
}

function tokenScore(token: string, q: string): number {
  const t = norm(token);
  if (t === q) return 100;
  if (t.startsWith(q)) return 80 - (t.length - q.length) * 0.5;
  const idx = t.indexOf(q);
  if (idx >= 0) return 50 - idx;
  let i = 0;
  let gaps = 0;
  for (const ch of t) {
    if (ch === q[i]) i++;
    else if (i > 0) gaps++;
    if (i === q.length) break;
  }
  if (i === q.length && gaps <= q.length * 2) return 25 - gaps;
  return 0;
}

export function scoreEntry(entry: CityEntry, rawQuery: string): number {
  const q = norm(rawQuery.trim());
  if (q.length < 2) return 0;
  let best = 0;
  for (const tok of [entry.f, ...entry.k]) {
    best = Math.max(best, tokenScore(tok, q));
  }
  for (const tok of entry.st) {
    best = Math.max(best, Math.min(tokenScore(tok, q), STATE_TOKEN_CAP));
  }
  return best;
}

/** The one entry point: scored, sorted, truncated — never index order. */
export function searchCities(
  index: CityEntry[],
  query: string,
  opts: { limit?: number; exclude?: string } = {},
): CityEntry[] {
  const { limit = 8, exclude } = opts;
  if (query.trim().length < 2) return [];
  return index
    .filter((e) => e.s !== exclude)
    .map((e) => ({ e, score: scoreEntry(e, query) }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((r) => r.e);
}
