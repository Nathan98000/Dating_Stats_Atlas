/** Permalink encode/decode, byte-compatible with atlas.model.preferences
 * .permalink(): canonical JSON (recursively sorted keys, compact
 * separators) over {self, seeking, weights, pool_vs_match, importance},
 * base64url with padding stripped, under
 * /r/<data_version>/<model_version>/<token>.
 *
 * One asymmetry matters: Python renders integral floats as "1.0" while
 * JSON.stringify renders 1. The §8.2 float-typed fields (the slider and
 * the pillar weights) are therefore formatted Python-style. The shared
 * test (tests/permalink.test.ts) asserts byte equality against cases
 * emitted by the Python model, so a drift here fails CI rather than
 * shipping two permalink dialects. m3.0.0 (ADR 0009): the slider is
 * pool_vs_match and the pillar is match; pool_vs_balance still DECODES
 * (old tokens route to the earlier-edition page) and, when a body
 * carries it, encodes as the canonical control exactly as Python does. */

const FLOAT_KEYS = new Set(["pool_vs_match", "pool_vs_balance", "pool",
  "match", "balance", "reach", "cost", "weather", "students"]);

type Json = string | number | boolean | null | Json[] | { [k: string]: Json };

function pyNumber(n: number, floatTyped: boolean): string {
  if (Number.isInteger(n)) {
    return floatTyped ? `${n}.0` : String(n);
  }
  return String(n); // both runtimes use shortest round-trip repr
}

function canonical(value: Json, parentKey: string | null,
                   inWeights: boolean): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    const floatTyped =
      (parentKey !== null && inWeights && FLOAT_KEYS.has(parentKey)) ||
      parentKey === "pool_vs_match" || parentKey === "pool_vs_balance";
    return pyNumber(value, floatTyped);
  }
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return "[" + value.map((v) => canonical(v, parentKey, inWeights)).join(",") + "]";
  }
  const keys = Object.keys(value).sort();
  const parts = keys.map((k) => {
    const nested = inWeights || k === "weights";
    return JSON.stringify(k) + ":" + canonical(value[k], k, nested);
  });
  return "{" + parts.join(",") + "}";
}

export interface RankBody {
  self: { sex: string; age: number; education?: string; race_ethnicity?: string };
  seeking: {
    sex?: string;
    age: [number, number];
    marital: string[];
    education_min?: string;
    income_min?: number;
    race_ethnicity?: string[];
  };
  weights?: Record<string, number>;
  size_vs_odds?: number;
  pool_vs_balance?: number; // deprecated alias, decoded and re-expressed
  pool_vs_match?: number;
  importance?: Record<string, string>;
  sort?: string;
  data_version?: string;
  model_version?: string;
}

export function canonicalCore(body: RankBody): string {
  // size_vs_odds left the contract in m2.1.0 — old tokens still DECODE
  // (the /r/ page routes them to the earlier-edition path) but nothing
  // encodes it anymore, mirroring the Python core keys exactly
  const core: Record<string, Json> = {};
  for (const k of ["self", "seeking", "weights",
                   "pool_vs_match", "importance"] as const) {
    if (body[k] !== undefined) core[k] = body[k] as unknown as Json;
  }
  // the deprecated alias encodes as the canonical control (Python does
  // the same), so one search has one permalink whichever name was sent
  if (core.pool_vs_match === undefined && body.pool_vs_balance !== undefined) {
    core.pool_vs_match = body.pool_vs_balance;
  }
  return canonical(core, null, false);
}

export function encodePermalink(dataVersion: string, modelVersion: string,
                                body: RankBody): string {
  const blob = canonicalCore(body);
  const b64 = Buffer.from(blob, "utf-8").toString("base64url");
  return `/r/${dataVersion}/${modelVersion}/${b64}`;
}

export function decodeToken(token: string): RankBody {
  const json = Buffer.from(token, "base64url").toString("utf-8");
  return JSON.parse(json) as RankBody;
}

export function decodePermalink(path: string): {
  dataVersion: string; modelVersion: string; body: RankBody;
} {
  const m = path.match(/^\/r\/([^/]+)\/([^/]+)\/([^/]+)$/);
  if (!m) throw new Error(`not a permalink path: ${path}`);
  return { dataVersion: m[1], modelVersion: m[2], body: decodeToken(m[3]) };
}
