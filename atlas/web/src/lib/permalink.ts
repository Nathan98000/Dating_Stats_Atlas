/** Permalink encode/decode, byte-compatible with atlas.model.preferences
 * .permalink(): canonical JSON (recursively sorted keys, compact
 * separators) over {self, seeking, weights, size_vs_odds}, base64url with
 * padding stripped, under /r/<data_version>/<model_version>/<token>.
 *
 * One asymmetry matters: Python renders integral floats as "1.0" while
 * JSON.stringify renders 1. The §8.2 float-typed fields (size_vs_odds and
 * the pillar weights) are therefore formatted Python-style. The shared
 * test (tests/permalink.test.ts) asserts byte equality against cases
 * emitted by the Python model, so a drift here fails CI rather than
 * shipping two permalink dialects. */

const FLOAT_KEYS = new Set(["size_vs_odds", "pool_vs_balance", "pool",
  "balance", "reach", "cost", "lifestyle"]);

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
      parentKey === "size_vs_odds" || parentKey === "pool_vs_balance";
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
  pool_vs_balance?: number;
  importance?: Record<string, string>;
  sort?: string;
  data_version?: string;
  model_version?: string;
}

export function canonicalCore(body: RankBody): string {
  const core: Record<string, Json> = {};
  for (const k of ["self", "seeking", "weights", "size_vs_odds",
                   "pool_vs_balance", "importance"] as const) {
    if (body[k] !== undefined) core[k] = body[k] as unknown as Json;
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
