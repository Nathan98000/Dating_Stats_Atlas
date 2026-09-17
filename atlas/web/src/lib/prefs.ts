/** URL state (§10.1): every preference lives in the query string. This
 * module maps searchParams <-> a typed pref state <-> the m2.0.0 request
 * body. It never computes a ranking number — that is the API's job. */
import type { RankBody } from "./permalink";

export const PILLARS = ["pool", "balance", "reach", "cost", "lifestyle"] as const;
export type Level = "not_much" | "some" | "a_lot";

export interface Prefs {
  selfSex: "male" | "female";
  selfAge: number;
  seekSex?: "male" | "female"; // absent = opposite of selfSex
  ageMin: number;
  ageMax: number;
  marital: string[]; // never_married / previously_married
  educationMin?: "bachelors" | "graduate";
  incomeMin?: number;
  race?: string[]; // the six selectable spec names; absent = all
  poolVsBalance?: number; // 0..1
  importance: { cost: Level; reach: Level; lifestyle: Level };
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
  importance: { cost: "some", reach: "some", lifestyle: "some" },
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

export type SearchParams = Record<string, string | string[] | undefined>;

function one(sp: SearchParams, k: string): string | undefined {
  const v = sp[k];
  return Array.isArray(v) ? v[0] : v;
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
    const parts = race.split(",").filter(Boolean);
    // zero ticked = all (the model treats it the same; the URL stays honest)
    if (parts.length) p.race = parts;
  }
  const s = parseFloat(one(sp, "s") ?? "");
  if (Number.isFinite(s) && s >= 0 && s <= 1) p.poolVsBalance = s;
  for (const [param, pillar] of [["ic", "cost"], ["ir", "reach"], ["il", "lifestyle"]] as const) {
    const lv = LEVEL_LONG[one(sp, param) ?? ""];
    if (lv) p.importance[pillar] = lv;
  }
  if (one(sp, "sort") === "worst_first") p.sort = "worst_first";
  return p;
}

export function toSearchParams(p: Prefs): URLSearchParams {
  const sp = new URLSearchParams();
  sp.set("self_sex", p.selfSex);
  sp.set("self_age", String(p.selfAge));
  if (p.seekSex) sp.set("sex", p.seekSex);
  sp.set("age", `${p.ageMin}-${p.ageMax}`);
  sp.set("marital", p.marital.map((m) => MARITAL_LONG[m]).join(","));
  if (p.educationMin) sp.set("edu", p.educationMin);
  if (p.incomeMin !== undefined) sp.set("inc", String(p.incomeMin));
  if (p.race?.length) sp.set("race", p.race.join(","));
  if (p.poolVsBalance !== undefined) sp.set("s", String(p.poolVsBalance));
  for (const [param, pillar] of [["ic", "cost"], ["ir", "reach"], ["il", "lifestyle"]] as const) {
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
  if (p.seekSex) body.seeking.sex = p.seekSex;
  if (p.educationMin) body.seeking.education_min = p.educationMin;
  if (p.incomeMin !== undefined) body.seeking.income_min = p.incomeMin;
  if (p.race?.length) body.seeking.race_ethnicity = [...p.race];
  const touched =
    p.poolVsBalance !== undefined ||
    Object.values(p.importance).some((l) => l !== "some");
  if (touched) {
    body.pool_vs_balance = p.poolVsBalance ?? 0.4545;
    body.importance = { ...p.importance };
  }
  return body;
}

export function bodyToPrefs(body: RankBody): Prefs {
  const p: Prefs = {
    selfSex: body.self.sex === "male" ? "male" : "female",
    selfAge: body.self.age,
    ageMin: body.seeking.age[0],
    ageMax: body.seeking.age[1],
    marital: [...body.seeking.marital],
    importance: { ...DEFAULT_PREFS.importance, ...(body.importance ?? {}) },
    sort: (body.sort as Prefs["sort"]) ?? "best_first",
  };
  if (body.seeking.sex === "male" || body.seeking.sex === "female") {
    p.seekSex = body.seeking.sex;
  }
  if (body.seeking.education_min === "bachelors"
      || body.seeking.education_min === "graduate") {
    p.educationMin = body.seeking.education_min;
  }
  if (body.seeking.income_min !== undefined) p.incomeMin = body.seeking.income_min;
  if (body.seeking.race_ethnicity?.length) p.race = [...body.seeking.race_ethnicity];
  if (body.pool_vs_balance !== undefined) p.poolVsBalance = body.pool_vs_balance;
  else if (body.size_vs_odds !== undefined) p.poolVsBalance = body.size_vs_odds;
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
    chips.push({ label: `${p.race.length} of 6 groups`, active: true });
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
