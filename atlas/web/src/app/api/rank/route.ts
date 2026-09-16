/** Same-origin proxy for POST /v1/rank (D04: the browser never reaches the
 * FastAPI process). Status codes pass through untouched — a 409 pin
 * mismatch or a 422 validation error is the API speaking, not this file. */
import { API_BASE } from "@/lib/api";

export async function POST(request: Request): Promise<Response> {
  const body = await request.text();
  const upstream = await fetch(`${API_BASE}/v1/rank`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
    cache: "no-store",
  });
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { "content-type": "application/json" },
  });
}
