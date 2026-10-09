/** Phase 6 (F18): the visitor's place in a list of results, kept for this
 * tab in sessionStorage under one key, `dsa_place`, as {from, to, visible,
 * cbsa} — the results URL, the city page it opened, how many rows showed
 * and the city's metro code. Never an "about you" detail (ADR 0018): the
 * results URL carries only the search, as it always has. Storage that is
 * blocked or empty simply means no place to restore. */
export const PLACE_KEY = "dsa_place";

export interface Place {
  from: string;
  to: string;
  visible: number;
  cbsa: string;
}

export function readPlace(): Place | null {
  try {
    const raw = window.sessionStorage.getItem(PLACE_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as Partial<Place>;
    if (typeof p.from !== "string" || typeof p.to !== "string" || typeof p.cbsa !== "string"
        || typeof p.visible !== "number") return null;
    return p as Place;
  } catch {
    return null;
  }
}

export function writePlace(p: Place): void {
  try {
    window.sessionStorage.setItem(PLACE_KEY, JSON.stringify({
      from: p.from, to: p.to, visible: p.visible, cbsa: p.cbsa }));
  } catch {
    /* storage blocked: the way back still works, from the top */
  }
}

/** Whether "Back to your results" should go back in history: this page was
 * opened from a results page's city link in this tab, and there is an
 * entry to go back to. */
export function cameFromResults(): boolean {
  const p = readPlace();
  return !!p && p.to === window.location.pathname + window.location.search && window.history.length > 1;
}
