/** Server-side API access. The FastAPI process binds loopback with no CORS
 * and no public surface (D04): the browser NEVER calls it. Server
 * components and the /api/rank proxy route are the only callers, so the
 * licensing posture (rendered site, not a data feed) holds. */
import "server-only";
import { cache } from "react";
import type { Meta, RankResponse } from "./types";
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

export async function apiRank(body: RankBody): Promise<RankResponse> {
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
