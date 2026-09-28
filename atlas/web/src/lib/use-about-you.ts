"use client";

import { useLayoutEffect, useState } from "react";
import { migrateLegacy, releasePending, type AboutYou } from "./about-you";
import { PREFS_COOKIE, PREFS_COOKIE_MAX_AGE } from "./prefs";

/** The "about you" details for a page that shows a variant (the city and
 * compare pages; the home page keeps its own copy of this logic because
 * it also re-asks the API). The server renders the default variant; this
 * reads the browser's details after hydration, then lifts the pre-paint
 * veil. An old link that named no sought sex meant the opposite of its
 * self_sex: the address is corrected and the page reloaded for it, since
 * the search itself changes (the veil stays up meanwhile). */
export function useAboutYou(): AboutYou {
  const [about, setAbout] = useState<AboutYou>({});
  const [ready, setReady] = useState(false);
  useLayoutEffect(() => {
    const { about: stored, soughtSex } = migrateLegacy(PREFS_COOKIE, PREFS_COOKIE_MAX_AGE);
    if (soughtSex) {
      // migrateLegacy wrote the corrected address; the server renders it
      window.location.replace(window.location.href);
      return;
    }
    setAbout(stored);
    setReady(true);
  }, []);
  useLayoutEffect(() => {
    if (ready) releasePending();
  }, [ready]);
  return about;
}
