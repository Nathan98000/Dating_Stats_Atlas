# ADR 0017 — Race and sex inputs never feed ads, listings, referrals, or housing, credit or job uses

Date: 2026-09-28 (Phase 4, Stage 5)
Status: accepted. **Nathan's decision** (decision 6 of the Phase 4 brief),
committed before the rest of Stage 5 so that everything built after it is
built under it.

## The rule

The site's race and sex inputs never feed:

- **advertising** of any kind, or its targeting;
- **listings** — the selection or ordering of anything offered for sale,
  rent or hire;
- **referrals** to anyone else;
- **any housing, credit or job use** — no decision, eligibility, pricing,
  screening or marketing.

"Race and sex inputs" means all of them: the visitor's own sex and race
(their "about you" details) and the sex and the race groups of the people
they search for. They are used for one thing only — computing the figures
on the page the visitor asked for.

## How the build holds it

- **No page makes a third-party request.** An e2e test visits every page
  shape and fails on any request to another origin: no advertising, no
  tracker, no analytics, no embedded third-party content. Fonts are
  self-hosted at build time.
- **The "about you" details never leave the browser** (ADR 0018). The
  partner filters travel only to the site's own server, which uses them to
  build the page and keeps nothing.
- **There is no advertising, listing, referral, housing, credit or job
  feature.** Adding any such feature needs a new ADR, and that ADR has to
  keep this rule.

## Consequences

- A feature that would send a race or sex input anywhere but the page
  that computes the figures is out of scope by construction, not by
  review.
- The privacy page (`docs/privacy.md`) says there are no analytics,
  advertising or third-party trackers; this rule and its test are why
  that sentence stays true.
