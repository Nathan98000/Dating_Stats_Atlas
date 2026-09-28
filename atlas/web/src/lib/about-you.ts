/** The visitor's "about you" details — their own sex, education and race
 * or ethnicity — live in this browser only (ADR 0018, Nathan's decision).
 * They are never sent: not in the query string, a request body, the cookie
 * or any header. The server returns every variant of a search and
 * lib/variants selects the one these details name. They are kept in
 * localStorage under one key; every read and write is guarded, and with
 * storage blocked the details last for the page only. Plain module:
 * importable from both sides of the server/client boundary (the server
 * only ever uses the empty default). */

export const ABOUT_YOU_KEY = "dsa_about_you";
/** the query parameters that carried these details before m4.0.0: moved
 * into storage on load and stripped from the address bar */
export const LEGACY_ABOUT_YOU_PARAMS = ["self_sex", "self_edu", "self_race"] as const;
/** set by the pre-paint script while a stored variant is pending, so the
 * server-rendered default is never shown in the wrong order */
export const PENDING_ATTR = "data-about-you";

const EDU = ["hs_or_less", "some_college", "bachelors", "graduate"] as const;
const RACES = ["hispanic", "white_nh", "black_nh", "asian_nh", "aian_nh",
  "nhpi_nh", "two_or_more_nh", "other_nh"] as const;
type Sex = "male" | "female";

export interface AboutYou {
  sex?: Sex;
  edu?: (typeof EDU)[number];
  /** the race switch: off unless the visitor turns it on */
  raceOn?: boolean;
  race?: string;
}

/** Runs in <head> before the first paint: when this browser holds details
 * (or an old link or cookie carries them), the parts of the page a
 * variant changes stay hidden until the client has selected the stored
 * variant — a blank for a moment rather than a list that reorders under
 * the visitor. The timeout un-hides them if scripts never arrive. */
export const PRE_PAINT_SCRIPT = `(function(){try{var d=document.documentElement,s=localStorage.getItem(${JSON.stringify(ABOUT_YOU_KEY)}),a=s?JSON.parse(s):null,u=new URLSearchParams(location.search);if((a&&(a.sex||a.edu||a.raceOn))||${JSON.stringify(LEGACY_ABOUT_YOU_PARAMS)}.some(function(k){return u.has(k)})||/(?:^|;\\s*)dsa_prefs=[^;]*self_/.test(document.cookie)){d.setAttribute(${JSON.stringify(PENDING_ATTR)},"pending");setTimeout(function(){d.removeAttribute(${JSON.stringify(PENDING_ATTR)})},4000)}}catch(e){}})();`;

export function opposite(sex: Sex): Sex {
  return sex === "male" ? "female" : "male";
}

/** A visitor who has not said: the opposite of the sought sex. */
export function effectiveSex(a: AboutYou, sought: Sex): Sex {
  return a.sex ?? opposite(sought);
}

/** The race the figure uses: only with the switch on and a group chosen. */
export function raceUsed(a: AboutYou): string | undefined {
  return a.raceOn && a.race ? a.race : undefined;
}

export function parseAboutYou(raw: unknown): AboutYou {
  const out: AboutYou = {};
  if (!raw || typeof raw !== "object") return out;
  const r = raw as Record<string, unknown>;
  if (r.sex === "male" || r.sex === "female") out.sex = r.sex;
  if ((EDU as readonly unknown[]).includes(r.edu)) out.edu = r.edu as AboutYou["edu"];
  if (r.raceOn === true) {
    out.raceOn = true;
    if ((RACES as readonly unknown[]).includes(r.race)) out.race = r.race as string;
  }
  return out;
}

export function readAboutYou(): AboutYou {
  try {
    const s = window.localStorage.getItem(ABOUT_YOU_KEY);
    return s ? parseAboutYou(JSON.parse(s)) : {};
  } catch {
    return {};
  }
}

export function writeAboutYou(a: AboutYou): void {
  try {
    const clean = parseAboutYou(a);
    if (Object.keys(clean).length) {
      window.localStorage.setItem(ABOUT_YOU_KEY, JSON.stringify(clean));
    } else {
      window.localStorage.removeItem(ABOUT_YOU_KEY);
    }
  } catch {
    /* storage blocked: the details last for this page only */
  }
}

function legacyInto(a: AboutYou, get: (k: string) => string | null): {
  about: AboutYou; sex: Sex | undefined;
} {
  const next = { ...a };
  const sex = get("self_sex");
  const legacySex = sex === "male" || sex === "female" ? sex : undefined;
  if (legacySex && !next.sex) next.sex = legacySex;
  const edu = get("self_edu");
  if (!next.edu && (EDU as readonly (string | null)[]).includes(edu)) {
    next.edu = edu as AboutYou["edu"];
  }
  const race = get("self_race");
  if (!next.raceOn && (RACES as readonly (string | null)[]).includes(race)) {
    next.raceOn = true;
    next.race = race as string;
  }
  return { about: next, sex: legacySex };
}

/** Old links and cookies (before m4.0.0) carried the details as
 * self_sex / self_edu / self_race. On load they move into storage —
 * filling only what storage does not already hold — and leave the
 * address bar (history.replaceState) and the cookie. Such a link or
 * cookie without an explicit sought sex meant the opposite of self_sex;
 * `soughtSex` says so, so the page can keep the search it named. */
export function migrateLegacy(cookieName: string, cookieMaxAge: number): {
  about: AboutYou; soughtSex?: Sex; changed: boolean;
} {
  let about = readAboutYou();
  let soughtSex: Sex | undefined;
  let changed = false;
  try {
    const url = new URL(window.location.href);
    if (LEGACY_ABOUT_YOU_PARAMS.some((k) => url.searchParams.has(k))) {
      const got = legacyInto(about, (k) => url.searchParams.get(k));
      about = got.about;
      if (got.sex && !url.searchParams.has("sex")) {
        soughtSex = opposite(got.sex);
        url.searchParams.set("sex", soughtSex);
      }
      for (const k of LEGACY_ABOUT_YOU_PARAMS) url.searchParams.delete(k);
      const qs = url.searchParams.toString();
      window.history.replaceState(null, "", `${url.pathname}${qs ? `?${qs}` : ""}${url.hash}`);
      changed = true;
    }
  } catch {
    /* an unreadable address leaves nothing to move */
  }
  try {
    const m = document.cookie.match(new RegExp(`(?:^|;\\s*)${cookieName}=([^;]*)`));
    if (m) {
      const usp = new URLSearchParams(decodeURIComponent(m[1]));
      if (LEGACY_ABOUT_YOU_PARAMS.some((k) => usp.has(k))) {
        const got = legacyInto(about, (k) => usp.get(k));
        about = got.about;
        if (got.sex && !usp.has("sex")) usp.set("sex", opposite(got.sex));
        for (const k of LEGACY_ABOUT_YOU_PARAMS) usp.delete(k);
        document.cookie = `${cookieName}=${encodeURIComponent(usp.toString())}; ` +
          `path=/; max-age=${cookieMaxAge}; samesite=lax`;
        changed = true;
      }
    }
  } catch {
    /* a blocked cookie jar holds nothing to move */
  }
  if (changed) writeAboutYou(about);
  return { about, soughtSex, changed };
}

export function releasePending(): void {
  try {
    document.documentElement.removeAttribute(PENDING_ATTR);
  } catch {
    /* no document */
  }
}
