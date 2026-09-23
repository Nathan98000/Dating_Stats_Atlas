/** URL state (§10.1): every preference lives in the query string. This
 * module maps searchParams <-> a typed pref state <-> the m2.0.0 request
 * body. It never computes a ranking number — that is the API's job. */
import type { RankBody } from "./permalink";

export const PILLARS = ["pool", "match", "reach", "cost", "weather",
  "students"] as const;
/** m3.0.0: the seeker's own optional attributes (ADR 0009) — cube level
 * names for education, spec ids for race; labels live in the registry */
export const SELF_EDU_LEVELS = ["hs_or_less", "some_college", "bachelors",
  "graduate"] as const;
export type SelfEdu = (typeof SELF_EDU_LEVELS)[number];
export type Level = "not_much" | "some" | "a_lot";
/** The four m2.1.0 importance controls (item 4): Cost of living, Social
 * life, Student life, Weather — labels and subtitles arrive from the
 * registry through /v1/meta, never from here. */
export const IMPORTANCE_PILLARS = ["cost", "reach", "students", "weather"] as const;
export type ImportancePillar = (typeof IMPORTANCE_PILLARS)[number];

export interface Prefs {
  selfSex: "male" | "female";
  selfAge: number;
  seekSex?: "male" | "female"; // absent = opposite of selfSex
  ageMin: number;
  ageMax: number;
  marital: string[]; // never_married / previously_married
  educationMin?: "bachelors" | "graduate";
  incomeMin?: number;
  race?: string[]; // spec ids of ticked groups (all eight equal since
  // m2.2.0/ADR 0006); absent = all — zero and all-eight mean everyone
  /** m3.0.0: optional "about you" inputs; absent = not disclosed, and
   * the API falls back to the population-average marginal */
  selfEdu?: SelfEdu;
  selfRace?: string;
  poolVsMatch?: number; // 0..1 (the URL param stays "s")
  importance: Record<ImportancePillar, Level>;
  sort: "best_first" | "worst_first";
}

/** The stated default profile: a woman of 30 seeking men 28–40, never
 * married or divorced/widowed, everything mattering "some". */
export const DEFAULT_PREFS: Prefs = {
  selfSex: "female",
  selfAge: 30,
  ageMin: 28,
  ageMax: 40,
  marital: ["never_married", "previously_married"],
  importance: { cost: "some", reach: "some", students: "some", weather: "some" },
  sort: "best_first",
};

const MARITAL_SHORT: Record<string, string> = {
  never: "never_married",
  previously: "previously_married",
};
const MARITAL_LONG: Record<string, string> = Object.fromEntries(
  Object.entries(MARITAL_SHORT).map(([s, l]) => [l, s]),
);
const LEVEL_SHORT: Record<Level, string> = { not_much: "n", some: "s", a_lot: "a" };
const LEVEL_LONG: Record<string, Level> = { n: "not_much", s: "some", a: "a_lot" };
const IMPORTANCE_PARAMS = [["ic", "cost"], ["ir", "reach"], ["ist", "students"],
  ["iw", "weather"]] as const;
// the contract's eight race ids (labels live in the registry): needed
// here so a URL or token listing all eight normalizes to "no filter"
export const RACE_IDS = ["hispanic", "white_nh", "black_nh", "asian_nh",
  "aian_nh", "nhpi_nh", "two_or_more_nh", "other_nh"] as const;

export type SearchParams = Record<string, string | string[] | undefined>;

/** The preference dialect's parameter names — the ONE list behind
 * isDefaultSearch, the nav links' carried query (Phase 2f item 2) and
 * the cookie fallback. */
export const PREF_KEYS = ["self_sex", "self_age", "self_edu", "self_race",
  "sex", "age", "marital", "edu", "inc", "race", "s", "ic", "ir", "ist", "iw",
  "il", "sort"] as const;

/** Phase 2f item 2 (ADR 0007): preferences persist in a cookie so the
 * search follows the visitor across the site. The query string stays the
 * shareable form, and EXPLICIT PARAMETERS ALWAYS WIN — the cookie is
 * read only when the URL carries no preference parameter at all, so a
 * shared link, a permalink or a reproduction route is never overridden
 * by whatever the visitor last searched. */
export const PREFS_COOKIE = "dsa_prefs";
export const PREFS_COOKIE_MAX_AGE = 180 * 24 * 60 * 60; // ~180 days

export function one(sp: SearchParams, k: string): string | undefined {
  const v = sp[k];
  return Array.isArray(v) ? v[0] : v;
}

/** True when the URL carries none of the preference params — the visitor
 * gets the stated default profile, and pages that show it say so. */
export function isDefaultSearch(sp: SearchParams): boolean {
  return !PREF_KEYS.some((k) => one(sp, k) !== undefined);
}

/** The cookie's stored query string back into searchParams shape; null
 * when the cookie is absent, unreadable, or carries no preference key. */
export function cookieSearchParams(
  value: string | undefined,
): SearchParams | null {
  if (!value) return null;
  try {
    const usp = new URLSearchParams(decodeURIComponent(value));
    const sp: SearchParams = {};
    for (const k of PREF_KEYS) {
      const v = usp.get(k);
      if (v !== null) sp[k] = v;
    }
    return isDefaultSearch(sp) ? null : sp;
  } catch {
    return null;
  }
}

/** The preference subset of a query string, for nav links that carry the
 * visitor's search from page to page (Phase 2f item 2). */
export function prefQueryString(usp: URLSearchParams): string {
  const out = new URLSearchParams();
  for (const k of PREF_KEYS) {
    const v = usp.get(k);
    if (v !== null) out.set(k, v);
  }
  return out.toString();
}

export function parsePrefs(sp: SearchParams): Prefs {
  const p: Prefs = {
    ...DEFAULT_PREFS,
    marital: [...DEFAULT_PREFS.marital],
    importance: { ...DEFAULT_PREFS.importance },
  };
  const selfSex = one(sp, "self_sex");
  if (selfSex === "male" || selfSex === "female") p.selfSex = selfSex;
  const selfAge = parseInt(one(sp, "self_age") ?? "", 10);
  if (Number.isFinite(selfAge)) p.selfAge = Math.min(70, Math.max(18, selfAge));
  const selfEdu = one(sp, "self_edu");
  if ((SELF_EDU_LEVELS as readonly string[]).includes(selfEdu ?? "")) {
    p.selfEdu = selfEdu as SelfEdu;
  }
  const selfRace = one(sp, "self_race");
  if ((RACE_IDS as readonly string[]).includes(selfRace ?? "")) p.selfRace = selfRace;
  const seekSex = one(sp, "sex");
  if (seekSex === "male" || seekSex === "female") p.seekSex = seekSex;
  const age = (one(sp, "age") ?? "").match(/^(\d+)-(\d+)$/);
  if (age) {
    p.ageMin = Math.max(18, parseInt(age[1], 10));
    p.ageMax = Math.min(70, parseInt(age[2], 10));
    if (p.ageMin > p.ageMax) [p.ageMin, p.ageMax] = [p.ageMax, p.ageMin];
  }
  const marital = one(sp, "marital");
  if (marital) {
    const parts = marital.split(",").map((m) => MARITAL_SHORT[m]).filter(Boolean);
    if (parts.length) p.marital = parts;
  }
  const edu = one(sp, "edu");
  if (edu === "bachelors" || edu === "graduate") p.educationMin = edu;
  const inc = parseInt(one(sp, "inc") ?? "", 10);
  if (Number.isFinite(inc)) p.incomeMin = inc;
  const race = one(sp, "race");
  if (race !== undefined) {
    const known = new Set<string>(RACE_IDS);
    const parts = [...new Set(race.split(",").filter((r) => known.has(r)))];
    // zero ticked = all, and ALL EIGHT ticked = all too (m2.2.0): both
    // normalize to no filter so one search has one spelling
    if (parts.length && parts.length < RACE_IDS.length) p.race = parts;
  }
  const s = parseFloat(one(sp, "s") ?? "");
  if (Number.isFinite(s) && s >= 0 && s <= 1) p.poolVsMatch = s;
  for (const [param, pillar] of IMPORTANCE_PARAMS) {
    const lv = LEVEL_LONG[one(sp, param) ?? ""];
    if (lv) p.importance[pillar] = lv;
  }
  // the m2.0.0 URL param for the bundled control: applies to both halves
  const il = LEVEL_LONG[one(sp, "il") ?? ""];
  if (il) {
    p.importance.weather = il;
    p.importance.students = il;
  }
  if (one(sp, "sort") === "worst_first") p.sort = "worst_first";
  return p;
}

export function toSearchParams(p: Prefs): URLSearchParams {
  const sp = new URLSearchParams();
  sp.set("self_sex", p.selfSex);
  sp.set("self_age", String(p.selfAge));
  if (p.selfEdu) sp.set("self_edu", p.selfEdu);
  if (p.selfRace) sp.set("self_race", p.selfRace);
  if (p.seekSex) sp.set("sex", p.seekSex);
  sp.set("age", `${p.ageMin}-${p.ageMax}`);
  sp.set("marital", p.marital.map((m) => MARITAL_LONG[m]).join(","));
  if (p.educationMin) sp.set("edu", p.educationMin);
  if (p.incomeMin !== undefined) sp.set("inc", String(p.incomeMin));
  if (p.race?.length) sp.set("race", p.race.join(","));
  if (p.poolVsMatch !== undefined) sp.set("s", String(p.poolVsMatch));
  for (const [param, pillar] of IMPORTANCE_PARAMS) {
    if (p.importance[pillar] !== "some") {
      sp.set(param, LEVEL_SHORT[p.importance[pillar]]);
    }
  }
  if (p.sort !== "best_first") sp.set("sort", p.sort);
  return sp;
}

export function toRankBody(p: Prefs): RankBody {
  const body: RankBody = {
    self: { sex: p.selfSex, age: p.selfAge },
    seeking: {
      age: [p.ageMin, p.ageMax],
      marital: [...p.marital],
    },
    sort: p.sort,
  };
  if (p.selfEdu) body.self.education = p.selfEdu;
  if (p.selfRace) body.self.race_ethnicity = p.selfRace;
  if (p.seekSex) body.seeking.sex = p.seekSex;
  if (p.educationMin) body.seeking.education_min = p.educationMin;
  if (p.incomeMin !== undefined) body.seeking.income_min = p.incomeMin;
  if (p.race?.length) body.seeking.race_ethnicity = [...p.race];
  const touched =
    p.poolVsMatch !== undefined ||
    Object.values(p.importance).some((l) => l !== "some");
  if (touched) {
    body.pool_vs_match = p.poolVsMatch ?? 0.4545;
    body.importance = { ...p.importance };
  }
  return body;
}

export function bodyToPrefs(body: RankBody): Prefs {
  // importance keys from an older token: "lifestyle" was the bundled
  // control — its level lands on both split pillars; unknown keys drop
  const imp = { ...DEFAULT_PREFS.importance };
  for (const [k, v] of Object.entries(body.importance ?? {})) {
    if ((IMPORTANCE_PILLARS as readonly string[]).includes(k)) {
      imp[k as ImportancePillar] = v as Level;
    } else if (k === "lifestyle") {
      imp.weather = v as Level;
      imp.students = v as Level;
    }
  }
  const p: Prefs = {
    selfSex: body.self.sex === "male" ? "male" : "female",
    selfAge: body.self.age,
    ageMin: body.seeking.age[0],
    ageMax: body.seeking.age[1],
    marital: [...body.seeking.marital],
    importance: imp,
    sort: (body.sort as Prefs["sort"]) ?? "best_first",
  };
  if ((SELF_EDU_LEVELS as readonly string[]).includes(body.self.education ?? "")) {
    p.selfEdu = body.self.education as SelfEdu;
  }
  if ((RACE_IDS as readonly string[]).includes(body.self.race_ethnicity ?? "")) {
    p.selfRace = body.self.race_ethnicity;
  }
  if (body.seeking.sex === "male" || body.seeking.sex === "female") {
    p.seekSex = body.seeking.sex;
  }
  if (body.seeking.education_min === "bachelors"
      || body.seeking.education_min === "graduate") {
    p.educationMin = body.seeking.education_min;
  }
  if (body.seeking.income_min !== undefined) p.incomeMin = body.seeking.income_min;
  if (body.seeking.race_ethnicity?.length) {
    const sel = [...new Set(body.seeking.race_ethnicity)];
    // a token listing all eight round-trips to "no filter" (m2.2.0)
    if (sel.length < RACE_IDS.length) p.race = sel;
  }
  // the slider value survives whichever name a token carries: the m3.0.0
  // control, the m2.x pool_vs_balance alias, or m2.0.0's size_vs_odds
  if (body.pool_vs_match !== undefined) p.poolVsMatch = body.pool_vs_match;
  else if (body.pool_vs_balance !== undefined) p.poolVsMatch = body.pool_vs_balance;
  else if (body.size_vs_odds !== undefined) p.poolVsMatch = body.size_vs_odds;
  return p;
}

const MARITAL_WORDS: Record<string, string> = {
  never_married: "never married",
  previously_married: "divorced or widowed",
};
const EDU_WORDS: Record<string, string> = {
  bachelors: "a college degree",
  graduate: "a graduate degree",
};

/** Plain-words restatement of the search (chips, headings, and the
 * narrow-state body's {search} slot — NarrowV3's own grammar). */
export function describeSearch(p: Prefs): string {
  const seek = p.seekSex ?? (p.selfSex === "female" ? "male" : "female");
  const noun = seek === "male" ? "Men" : "Women";
  let s = `${noun} ${p.ageMin}–${p.ageMax}, `
    + p.marital.map((m) => MARITAL_WORDS[m]).join(" or ");
  if (p.educationMin) s += `, with ${EDU_WORDS[p.educationMin]}`;
  if (p.incomeMin !== undefined) {
    s += `, earning $${p.incomeMin.toLocaleString("en-US")} or more`;
  }
  return s;
}

export function searchChips(p: Prefs): { label: string; active: boolean }[] {
  const seek = p.seekSex ?? (p.selfSex === "female" ? "male" : "female");
  const chips = [
    { label: `${p.selfSex === "female" ? "Woman" : "Man"}, ${p.selfAge}`, active: false },
    { label: `${seek === "male" ? "Men" : "Women"} ${p.ageMin}–${p.ageMax}`, active: false },
    { label: p.marital.length === 2 ? "Single"
        : p.marital[0] === "never_married" ? "Never married" : "Divorced or widowed",
      active: p.marital.length === 1 },
  ];
  if (p.educationMin) {
    chips.push({ label: p.educationMin === "bachelors" ? "College degree" : "Graduate degree", active: true });
  }
  if (p.incomeMin !== undefined) {
    chips.push({ label: `Earning $${p.incomeMin.toLocaleString("en-US")}+`, active: true });
  }
  if (p.race?.length) {
    chips.push({ label: `${p.race.length} of ${RACE_IDS.length} groups`, active: true });
  }
  return chips;
}

/** The narrow-state wideners (NarrowV3/MetroV3): each restates the query
 * it would produce, and each is a one-click, one-change loosening. */
export function wideners(p: Prefs): { label: string; sub: string; next: Prefs }[] {
  const out: { label: string; sub: string; next: Prefs }[] = [];
  const span = p.ageMax - p.ageMin;
  const wMin = Math.max(18, p.ageMin - 3);
  const wMax = Math.min(70, p.ageMax + Math.max(2, Math.round(span / 2)));
  out.push({
    label: `Widen the ages to ${wMin}–${wMax}`,
    sub: "everything else stays the same",
    next: { ...p, ageMin: wMin, ageMax: wMax },
  });
  if (p.incomeMin !== undefined) {
    out.push({
      label: "Drop the income filter",
      sub: p.educationMin ? "keeps the ages and the degree" : "keeps everything else",
      next: { ...p, incomeMin: undefined },
    });
  }
  if (p.educationMin) {
    out.push({
      label: "Any degree",
      sub: p.incomeMin !== undefined ? "keeps the ages and the income" : "keeps everything else",
      next: { ...p, educationMin: undefined },
    });
  }
  if (p.race?.length) {
    out.push({
      label: "Include every group",
      sub: "keeps everything else",
      next: { ...p, race: undefined },
    });
  }
  if (p.marital.length === 1) {
    out.push({
      label: "Never married or divorced",
      sub: "keeps everything else",
      next: { ...p, marital: ["never_married", "previously_married"] },
    });
  }
  return out.slice(0, 3);
}
