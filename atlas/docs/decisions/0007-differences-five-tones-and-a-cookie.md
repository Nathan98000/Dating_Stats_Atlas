# ADR 0007 — Pools get a difference, the tones widen to five, and preferences persist in a cookie

Date: 2026-09-18 (Phase 2f, model m2.3.1 — display only)
Status: accepted

Phase 2f is Nathan's line-by-line review of the running site. Three of its
changes touch recorded decisions — two reversals and one addition — and this
note records all three. No number moved: every score, rank, pool, balance and
card value is byte-identical to m2.3.0, asserted across all fifteen golden
vectors by `pipeline/build/display_only_diff.py` and across the full build by
the m2.3.0/m2.3.1 snapshot comparison (max |Δ| = 0.00e+00 over 1,032 exact
scores).

## 1. The compare page's differences (reverses part of ADR 0003)

ADR 0003 said pools get no difference on the compare page — the API computes
per-city figures, not pairs, and the one sanctioned piece of client arithmetic
was the static-stat subtraction. Nathan's review reverses the abstention: a
side-by-side that shows two pool counts and refuses to subtract them reads as
coyness, not caution.

Every row now carries a difference, under one rule: **plain subtraction of the
two displayed values**, computed by parsing the display strings themselves —
never a recomputation from raw values — so the equality with what the visitor
sees holds by construction and to the displayed precision. An em dash renders
whenever either side is missing or suppressed. Rent's difference carries `$`
after the sign.

The colour of a difference says whether A − B favours the left-hand city for
this visitor: green when it does, red when it does not, with the direction
taken from the registry's `direction` field (+1/−1), never from the band
tones. Grey — no judgement — in exactly three cases: the feature's pillar
importance is set to Not much (which still carries weight 0.4: the legend line
under the table says "matters least to you", never "excluded"); Who lives
here, always (population is a fact, not a virtue); and anything without a
direction. Everyday prices is the average of the two scored cost features, so
the importance control that covers it is Cost of living even though its own
pillar field reads `context` — a rule the compare page applies explicitly and
this note records. One observed consequence of "direction, never band tones":
the Students difference colours green/red through its registry direction (+1,
a documented judgment) even though its band tones are deliberately neutral.

## 2. Five tones instead of three (extends ADR 0005's band derivation)

The band-tone vocabulary widens from good/neutral/poor to
good_strong/good/neutral/poor/poor_strong: the extreme bands of a directed
feature read harder than the middles. The derivation is unchanged in kind —
band position crossed with the registry's `band_direction`, in
`pipeline/registry/loader.py`, never judgment per label — and neutral features
(students, population, both crime rates) stay neutral in every band.

Colours: `--good-strong #1B5E4B`, `--poor-strong #8A2B18`, joining the
unchanged light pair. Measured contrast is 7.19:1/8.11:1 on paper and
7.64:1/8.61:1 on white for the strong pair; the light pair measures **below
AA on the tint background** (4.19:1/4.27:1), so no tone label may sit on tint
— nothing does, and `web/tests/tones.test.ts` pins both the passing table and
the tint exclusion. Colour is never the only signal: the band phrase carries
the meaning (WCAG 1.4.1).

Tone strings ride in responses and manifests, so this is the display-only
model bump to **m2.3.1**: goldens regenerated (the diff is exactly the
version line), fixture manifest refreshed, permalink cases re-emitted.

## 3. Preferences persist in a cookie (new)

A visit to What we measure used to lose the visitor's search. Preferences now
follow the visitor: the panel writes a `dsa_prefs` cookie (SameSite=Lax,
path=/, ~180 days) alongside the existing `replaceState`, the nav links carry
the current preference query string when the page has one, and the
pref-consuming server pages fall back to the cookie for a bare URL.

**The precedence rule, stated explicitly: explicit parameters always win.**
The cookie is read only when the URL carries no preference parameter at all,
so a shared link, a permalink, and a `/r/[dv]/[mv]/[token]` reproduction are
never overridden by whatever the visitor last searched — asserted end-to-end
with a conflicting cookie set. The query string remains the shareable form;
the cookie is never one. Pages that read it are force-dynamic, so no
visitor's cookie-shaped render can be cached into another's. One consequence:
the compare page's "stated default search" label shows only when the figures
really are the stated default — a cookie-filled page is the visitor's own
search, so the label stays off.
