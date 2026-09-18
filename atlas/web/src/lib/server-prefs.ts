import "server-only";
import { cookies } from "next/headers";
import {
  cookieSearchParams,
  isDefaultSearch,
  PREFS_COOKIE,
  type SearchParams,
} from "./prefs";

/** Phase 2f item 2 (ADR 0007): the effective preference params for a
 * server page. EXPLICIT PARAMETERS ALWAYS WIN — a shared link, a
 * permalink or a /r/ reproduction is never overridden; the cookie is
 * read only when the URL carries no preference parameter at all. Every
 * caller is a force-dynamic page, so no visitor's cookie-shaped render
 * can be cached into another's. */
export async function effectiveSearchParams(
  sp: SearchParams,
): Promise<{ sp: SearchParams; fromCookie: boolean }> {
  if (!isDefaultSearch(sp)) return { sp, fromCookie: false };
  const jar = await cookies();
  const parsed = cookieSearchParams(jar.get(PREFS_COOKIE)?.value);
  if (parsed) return { sp: parsed, fromCookie: true };
  return { sp, fromCookie: false };
}
