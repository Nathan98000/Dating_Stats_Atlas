/** Server-side API access. The FastAPI process binds loopback with no CORS
 * and no public surface (D04): the browser NEVER calls it. Server
 * components and the /api/rank proxy route are the only callers, so the
 * licensing posture (rendered site, not a data feed) holds. */
import "server-only";
import { cache } from "react";
import type { Meta, PoliticalLeanResponse, ProfileResponse, VariantResponse } from "./types";
import type { RankBody } from "./permalink";

export const API_BASE = process.env.ATLAS_API_URL ?? "http://127.0.0.1:8000";

export class RankError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`rank ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

/** m4.0.0 (ADR 0018): the response carries every "about you" variant;
 * lib/variants selects one. */
export async function apiRank(body: RankBody): Promise<VariantResponse> {
  const res = await fetch(`${API_BASE}/v1/rank`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* keep statusText */
    }
    throw new RankError(res.status, detail);
  }
  return res.json();
}

/** The legend, policy strings and metro list change only with the build;
 * cached per server process per request tree. */
export const apiMeta = cache(async (): Promise<Meta> => {
  const res = await fetch(`${API_BASE}/v1/meta`, { cache: "no-store" });
  if (!res.ok) throw new RankError(res.status, "meta unavailable");
  return res.json();
});

/** Phase 4d (ADR 0019): every metro's 2024 presidential vote, as the city
 * and compare pages show it. Fetched here, server-side, apart from the
 * rank response — political lean is never part of a search. Changes only
 * with the build. An API from before the feature answers 404, and the
 * pages then show no political lean rather than fail (web and API can be
 * a release apart for a moment); any other failure is an error. */
export const apiPoliticalLean = cache(async (): Promise<PoliticalLeanResponse> => {
  const res = await fetch(`${API_BASE}/v1/political_lean`, { cache: "no-store" });
  if (res.status === 404) return { data_version: "", year: "", metros: {} };
  if (!res.ok) throw new RankError(res.status, "political lean unavailable");
  return res.json();
});

/** One metro's profile — its stat cards and crime block — for ANY metro of
 * the build, the 194 below the ranked set's population floor included,
 * which no search returns. Request-independent, fetched server-side apart
 * from the rank response (which stays as it was). The metro travels in the
 * body, as a search does, so no access line says which city a page showed.
 * An API from before the endpoint answers 404, and the pages then fall
 * back to the rank row's copy of the same blocks (the old behaviour); any
 * other failure is an error. */
export const apiProfile = cache(async (cbsa: string): Promise<ProfileResponse | null> => {
  const res = await fetch(`${API_BASE}/v1/profile`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ cbsa }),
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new RankError(res.status, "profile unavailable");
  return res.json();
});

/** Phase 6 (F32): the registry's metadata as a page hands it to its client
 * components — only the metros the page shows (the full list's 387
 * descriptions travelled in every city page's HTML) and none of the
 * licences, What-we-measure layout, technical strings or provenance,
 * which no client component reads. Everything kept is unchanged. */
export function clientMeta(meta: Meta, cbsas: string[]): Meta {
  const keep = new Set(cbsas);
  return {
    ...meta,
    metros: meta.metros.filter((m) => keep.has(m.cbsa)),
    licenses: {},
    measure_page: [],
    technical_strings: {},
    features: Object.fromEntries(Object.entries(meta.features).map(([k, f]) =>
      [k, { ...f, provenance: {} }])),
  };
}
