/** URL state (§10.1): every preference lives in the query string, and the
 * query string is the only client-side source of truth. This module maps
 * searchParams <-> a typed pref state <-> the §8.2 request body. It never
 * computes a ranking number — that is the API's job alone. */
import type { RankBody } from "./permalink";

export const PILLARS = ["pool", "balance", "reach", "cost", "lifestyle"] as const;

export interface Prefs {
  selfSex: "male" | "female";
  selfAge: number;
  seekSex?: "male" | "female";
  ageMin: number;
  ageMax: number;
  marital: string[]; // spec names
  educationMin?: string;
  incomeMin?: number;
  race?: string[]; // spec names
  sizeVsOdds?: number; // slider, mutually exclusive with weights
  weights?: Record<string, number>; // fine-tune, full 5-pillar vector
}

/** §10.2's "sensible default profile": a woman of 30 seeking men 28-40 who
 * never married or were previously married, no education/income/identity
 * filters, default weights. Arbitrary by necessity, stated on the page,
 * and one click from being the visitor's own. */
export const DEFAULT_PREFS: Prefs = {
  selfSex: "female",
  selfAge: 30,
  ageMin: 28,
  ageMax: 40,
  marital: ["never_married", "previously_married"],
};

const MARITAL_SHORT: Record<string, string> = {
  never: "never_married",
  previously: "previously_married",
  currently: "currently_married",
};
const MARITAL_LONG: Record<string, string> = Object.fromEntries(
  Object.entries(MARITAL_SHORT).map(([s, l]) => [l, s]),
);

export type SearchParams = Record<string, string | string[] | undefined>;

function one(sp: SearchParams, k: string): string | undefined {
  const v = sp[k];
  return Array.isArray(v) ? v[0] : v;
}

export function parsePrefs(sp: SearchParams): Prefs {
  const p: Prefs = { ...DEFAULT_PREFS, marital: [...DEFAULT_PREFS.marital] };
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
  }
  const marital = one(sp, "marital");
  if (marital) {
    const parts = marital.split(",").map((m) => MARITAL_SHORT[m]).filter(Boolean);
    if (parts.length) p.marital = parts;
  }
  const edu = one(sp, "edu");
  if (edu && ["some_college", "bachelors", "graduate"].includes(edu)) {
    p.educationMin = edu;
  }
  const inc = parseInt(one(sp, "inc") ?? "", 10);
  if (Number.isFinite(inc)) p.incomeMin = inc;
  const race = one(sp, "race");
  if (race) {
    const parts = race.split(",").filter(Boolean);
    if (parts.length) p.race = parts;
  }
  const s = parseFloat(one(sp, "s") ?? "");
  if (Number.isFinite(s) && s >= 0 && s <= 1) p.sizeVsOdds = s;
  const w = one(sp, "w");
  if (w) {
    const vals = w.split(",").map(Number);
    if (vals.length === PILLARS.length && vals.every((v) => Number.isFinite(v) && v >= 0)) {
      p.weights = Object.fromEntries(PILLARS.map((k, i) => [k, vals[i]]));
      p.sizeVsOdds = undefined; // explicit weights win, matching the API rule
    }
  }
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
  if (p.weights) sp.set("w", PILLARS.map((k) => p.weights![k]).join(","));
  else if (p.sizeVsOdds !== undefined) sp.set("s", String(p.sizeVsOdds));
  return sp;
}

export function toRankBody(p: Prefs, pins?: { dataVersion: string; modelVersion: string }): RankBody {
  const body: RankBody = {
    self: { sex: p.selfSex, age: p.selfAge },
    seeking: {
      age: [p.ageMin, p.ageMax],
      marital: [...p.marital],
    },
  };
  if (p.seekSex) body.seeking.sex = p.seekSex;
  if (p.educationMin) body.seeking.education_min = p.educationMin;
  if (p.incomeMin !== undefined) body.seeking.income_min = p.incomeMin;
  if (p.race?.length) body.seeking.race_ethnicity = [...p.race];
  if (p.weights) {
    // the API's Weights model carries all five pillars; send the full vector
    body.weights = Object.fromEntries(PILLARS.map((k) => [k, p.weights![k] ?? 0]));
  } else if (p.sizeVsOdds !== undefined) {
    body.size_vs_odds = p.sizeVsOdds;
  }
  if (pins) {
    body.data_version = pins.dataVersion;
    body.model_version = pins.modelVersion;
  }
  return body;
}

/** The reverse of toRankBody, for permalink tokens (/r/...) — a decoded
 * body becomes URL state so "re-run under the current build" is one link. */
export function bodyToPrefs(body: RankBody): Prefs {
  const p: Prefs = {
    selfSex: body.self.sex === "male" ? "male" : "female",
    selfAge: body.self.age,
    ageMin: body.seeking.age[0],
    ageMax: body.seeking.age[1],
    marital: [...body.seeking.marital],
  };
  if (body.seeking.sex === "male" || body.seeking.sex === "female") {
    p.seekSex = body.seeking.sex;
  }
  if (body.seeking.education_min) p.educationMin = body.seeking.education_min;
  if (body.seeking.income_min !== undefined) p.incomeMin = body.seeking.income_min;
  if (body.seeking.race_ethnicity?.length) p.race = [...body.seeking.race_ethnicity];
  if (body.weights) p.weights = { ...body.weights };
  else if (body.size_vs_odds !== undefined) p.sizeVsOdds = body.size_vs_odds;
  return p;
}

export function describePrefs(p: Prefs, opts?: { withIdentity?: boolean }): string {
  const seek = p.seekSex ?? (p.selfSex === "female" ? "male" : "female");
  const seekNoun = seek === "male" ? "men" : "women";
  const selfNoun = p.selfSex === "male" ? "man" : "woman";
  const maritalWords: Record<string, string> = {
    never_married: "never married",
    previously_married: "previously married",
    currently_married: "currently married",
  };
  let s = `a ${selfNoun}, ${p.selfAge}, seeking ${seekNoun} ${p.ageMin}–${p.ageMax}, ` +
    p.marital.map((m) => maritalWords[m]).join(" or ");
  if (p.educationMin) {
    const edu: Record<string, string> = {
      some_college: "some college or more",
      bachelors: "bachelor's or more",
      graduate: "a graduate degree",
    };
    s += `, with ${edu[p.educationMin]}`;
  }
  if (p.incomeMin !== undefined) s += `, earning $${p.incomeMin.toLocaleString()}+`;
  if (opts?.withIdentity && p.race?.length) s += `, with an identity filter active`;
  return s;
}
