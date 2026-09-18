# Phase 2f — Nathan's line-by-line review, shipped and measured

Build `98dcbb161236` (data bit-identical to Phase 2e's), model **m2.3.1 —
display only**. Suites at close: **41 pytest, 49 vitest, 65 Playwright**, axe
zero serious/critical across the nine page shapes, banned-vocabulary sweep
zero across eleven. `/v1/rank` p50 29.0 ms / p95 39.2 ms over 40 runs (dev
machine, dev stack running beside it; the API code path did not change this
phase).

## The two things that belong at the top

**The hero photograph.** The home page now opens on Carol M. Highsmith's
*View of the Burlington Marketplace* (2017) — Church Street's pedestrian
block, people small, city legible, which is the HomeV3 art direction almost
verbatim. It was sourced through the Phase 2e pipeline and licence gate with
a stricter bar for this one slot: **public domain / CC0 only**, enforced by
`pipeline/build/hero_image.py`, because the hero renders as a cropped band
and a crop of a CC-BY-SA image is an adaptation that would drag ShareAlike
onto the page. It cleared as **public domain** (the photographer's Library of
Congress dedication), read live from the Commons API — so the band crop
carries no licence implication at all. Manifest row at
`results/phase2f/hero_image.csv`; attribution renders under the band and is
bound to the file by SHA-256, so Nathan's drop-in override at
`web/public/hero.jpg` still renders but can never wear the sourced image's
credit. A row was added to the counsel packet's source table beside the city
images.

**What this phase took off the site.** Each was there for a reason once;
none is quietly gone:

- *The per-city crime coverage sentence* ("Police agencies covering X of the
  people here reported a full year") left the crime card's popover — Nathan's
  caution box replaces it — and now appears **nowhere on the card**. The
  string stays in the registry; the blank state keeps its own why-blank
  sentence (about police reporting, deliberately not "not enough reliable
  data"); coverage as a concept lives on in the crime explainer's prose, but
  the per-city figure itself no longer renders anywhere.
- *The band labels on the stat lists* (all seven pages, shared component) —
  the ordering already said it and the distribution strip carries the spread.
  Rows no longer ship a band at all in the build JSON.
- *The deleted intro paragraphs*: `stat_page_intro` ("Every city this site
  can rank, ordered by one measure…", all seven stat pages) and
  `measure_page_intro` ("Everything this site measures, in plain words…") are
  deleted key, build field and paragraph. The brief counts three; the third
  candidate — the compare landing's old subheading — was **replaced** by
  Nathan's new one (item 7) rather than deleted, so it is accounted here
  rather than listed as removed.

## 1. Four tones instead of two — measured

`BAND_DIRECTION_TONES` in the registry loader now derives five tones —
`good_low: (good_strong, good, neutral, poor, poor_strong)`, mirrored for
`good_high`, neutral unchanged — still position × direction and nothing else.
Contrast, measured (WCAG relative luminance, `web/tests/tones.test.ts` pins
every row):

| Token | Hex | on paper #FDF7F3 | on white | on tint #F7E9EE |
|---|---|---|---|---|
| `--good-strong` | `#1B5E4B` | 7.19:1 | 7.64:1 | 6.49:1 |
| `--good` | `#2E7D6B` | 4.64:1 | 4.93:1 | **4.19:1 — below AA** |
| `--poor` | `#B0543E` | 4.73:1 | 5.02:1 | **4.27:1 — below AA** |
| `--poor-strong` | `#8A2B18` | 8.11:1 | 8.61:1 | 7.32:1 |

Every surface a tone label actually sits on is paper or white; **no tone
label sits on tint**, and the vitest suite pins both the passing table and
the tint exclusion (with the strong tones as the documented escape hatch if
one ever must). The lit indicator segment takes its label's colour; the
phrase always carries the meaning (WCAG 1.4.1). e2e asserts the computed
colour of all four coloured tones plus neutral on real cards (Provo's
walkability dark green, nice days dark red, rent light red, students grey;
Austin's walkability light green — and Austin's rent shows the *label and
segment* both dark red).

The brief named three tone→class maps; the stat-list's map was **deleted with
the band labels** (item 9.4), so two page maps remain (city cards, compare),
now fed from one shared `lib/tones.ts`.

**MODEL_VERSION m2.3.1, display only — the no-number proof, twice:**

- `pipeline/build/display_only_diff.py` ran all fifteen golden vectors
  against the pinned m2.3.0 fixture and the regenerated m2.3.1 fixture:
  **10,935 numeric fields compared, all bitwise identical**; every string
  difference classified into exactly the approved set (544 tone strings under
  the position map, 165 rent unit lines, 165 crime cautions, 165 compare
  banners; zero unexplained). `results/phase2f/no_number_moved.json`.
- Full-build snapshot vs the committed m2.3.0 snapshot: **1,032 exact scores
  across 11 personas, max |Δ| = 0.00e+00; ranks and pools identical.**
  `results/phase2f/m2_3_1_snapshot.json`.
- The regenerated `goldens.json` differs from m2.3.0's in **exactly one
  line** — the model_version string. The fixture's data files re-wrote
  byte-identically.
- The Phase 2e validation battery attaches to build `98dcbb161236`, whose
  data files are untouched (data_version hashes data only; the refresh
  rewrote manifest display metadata in place). The battery was not re-run:
  the bytes it validated are the bytes being served.

## 2. The search follows the visitor — measured

`dsa_prefs` cookie (SameSite=Lax, path=/, 180 days) written on every panel
change beside the existing `replaceState`; nav links (and the brand link)
carry the preference subset of the current query; the three pref-consuming
pages fall back to the cookie **only when the URL carries no preference
parameter at all**. e2e walks the loop: set Cost of living to A lot → What we
measure → Compare cities → Browse cities, the control still checked at every
stop; then a **bare** `/` restores it from the cookie alone; then `/?ic=n`
proves explicit parameters beat the cookie. A `/r/` reproduction link loaded
with a deliberately conflicting cookie serves the token's search and the
token's ranking, byte for byte (`my-age` shows the token's 33, first ranked
row matches the API's own response). The permalink dialect cases were
regenerated under m2.3.1 and pass unchanged — they are pure encode/decode and
carry no cookie surface, so "the cases pass with a conflicting cookie" is
witnessed by the e2e reproduction test above. The compare page's "stated
default search" label now renders only when the figures really are the
stated default: a cookie-filled page is the visitor's own search (ADR 0007).

## 3. The popover stays open long enough to use — measured

Rebuilt on the wrapper: the note's container starts flush with the button's
bottom edge (the visual 8px gap is padding **inside** the hover target), so
the pointer's trip from button to note crosses no dead space; `focusout`
closes only when focus leaves the wrapper; Escape closes and returns focus to
the button; pointerdown outside closes; click still opens rather than
toggling. The three commissioned tests pass: pointer into the note leaves it
open and its link navigates; Tab from the button lands on "See more details"
(and tabbing on out closes); Escape restores focus to the button. One repair
found during verification: a last-column card's centred 290px note **clipped
its link off the right viewport edge**, so the note now clamps itself inside
the viewport (measured in-pane: right edge 1012 at a 1024 viewport).

## 4. The home page — items measured

- **4.1** hero above, with attribution rendered as the stat pages do.
- **4.2/4.3** headline and subhead are registry strings (`home_title`,
  `home_subtitle`), asserted verbatim in e2e.
- **4.4** slider note is Nathan's new copy, asserted in e2e — note it says
  "Leaning towards … favors", a British/American mix shipped verbatim as
  instructed.
- **4.5** the slider block moved out of the panel's top into one bordered
  group immediately above "How much do these matter?"; the field order above
  it (you, looking for, ages, marital, education, income, race) untouched;
  e2e asserts race sits above the slider and the slider above the importance
  rows.
- **4.6** `excluded_count` replaced in `model/suppression.py` (typographic
  apostrophe per that file's convention); e2e asserts "make a reliable
  estimate" and "Widen your search to see more cities."

## 5. City pages — items measured

- **5.1** rent's unit line: "median 1-bedroom monthly rent, with utilities".
- **5.2** every card (crime included) is a subgrid over six shared rows
  (name / value / unit / segments / band label / link) with its own 10px row
  gap; browsers without subgrid fall back to the old flex column with a
  two-line minimum on the unit row. Screenshots at 1280 / 1024 / 375
  (`03_…png`–`05_…png`) show the indicators on one line across every row
  while "Places to go out" wraps and its neighbours don't.
- **5.3** the crime popover is the caution + "See more details." exactly;
  the blank card's popover keeps its why-blank sentence *ahead of* the
  caution (the sibling reading), verified live on Raleigh (coverage below
  floor). Flagged above: the coverage figure now appears nowhere on the card.
- **5.4** "Not enough reliable data available." ships as `card_missing`,
  used by the city cards and the compare table's value cells; crime blanks
  keep their own reporting-specific wording.
- **5.5** the class maps carry all five tones; nothing else page-specific.

## 6. Comparing two cities — items measured

Every row now has a difference, computed by **parsing the two displayed
strings and subtracting** — never from raw values — so gate 5's equality
holds by construction; e2e sweeps every `data-diff-for` row (eleven of them)
and re-derives each shown difference from the two cells it sits beside, to
the displayed precision, including population's "2.4 million" spelling. Spot
in your results (direction −1), score, people who match, balance (per-100
integers), and who-lives-here all fill their formerly blank cells; rent's
difference reads `−$322` with the dollar after the sign; either side missing
or suppressed gives an em dash (asserted under the stress search, where both
cities' pools suppress and rank/score/pool all dash while balance — which
survives its own gate — still subtracts). Colours from the registry
`direction` through the light pair; grey (`--ink-3`) for population always,
for `direction: 0`/none, and for a pillar set to Not much — asserted live:
`ic=n` greys rent **and** everyday prices while venues stays coloured
(everyday prices is the two scored cost features' average, so Cost of living
is the control that covers it — recorded in ADR 0007). The registry legend
line under the table names the two cities and says grey means "matters least
to you", never "excluded". One observed consequence, flagged: **Students'
difference colours** green/red through its registry direction (+1, a
documented judgment) even though its band tones are deliberately neutral —
the brief's rule ("direction, never band tones") decides it.

The crime block keeps two plain numbers and one banner — Nathan's new
wording with "See more details." — and each row label now carries the unit
"reported per 100,000 people a year" under it (the row-label placement reads
cleaner at 375px than repeating it under both figures; screenshot
`08_…png`). Zero-difference edge: a zero renders unsigned in grey (favours
neither side).

## 7–8. The compare landing and What we measure — items measured

The landing subheading is `compare_page_subtitle`, verbatim. What we measure
opens straight into "The people" (intro deleted), every card is name + body +
link with **no unit aside**, all ten bodies are Nathan's table verbatim
(including his mixed punctuation — three end in periods, seven don't — and
American "theaters" an inch from the site's older British "favours" in the
untouched movers line), walkability's link reads "See all cities by
walkability" via `stat_page_name`, and the cost group shows Rent and
Everyday prices with the two RPP component cards gone from this page only —
they remain the scored features, asserted untouched by the no-number proof.
The page composes nothing: the registry's `measure_page:` block (group →
ordered ids) drives section order, headings and card order through
`/v1/meta`, with "Also on every city page" itself moved from a component
literal into the registry.

## 9. The statistic pages — items measured

Standing intro deleted everywhere (key, build field, paragraph — e2e asserts
its absence). Every page carries a live source line under its subheading,
driven by a new registry `sources:` block keyed by `source_id` and joined
through each feature's existing `provenance.source` (loader-asserted for
every stat page; the links match Nathan's verified `docs/sources.md`).
Rent's reads exactly "Source: U.S. Census Bureau's American Community Survey
5-Year Data" → census.gov/programs-surveys/acs/; the other six carry their
vintages, which is where nice days gets its 1991–2020 on the page
(e2e-asserted). The rent caution box is Nathan's new two-sentence note. Band
labels are gone from all seven lists. The header row: the list **stays an
`<ol>`** with an aria-hidden header strip on the same grid ("City Name" over
the names, the statistic's display name over the values) — chosen over a
`<table>` because each row's link already announces its position via the
sr-only prefix that the sort toggle's semantics hang on, and a table would
announce position twice while re-plumbing that for no reader gain; the
sr-only prefix stays either way, and each row's value carries its unit in
words.

## Deviations, findings and judgment calls

1. **InfoTip viewport clamp** — added beyond the brief after verification
   showed last-column notes clipping their new link (item 3's purpose).
2. **`layout.tsx` metadata description** still carries the old headline
   ("Where would you meet more people you'd actually click with?…") — it is
   pre-existing approved board copy in the HTML `<meta>`, not one of the
   fifty changes, so it was left; flagged for Nathan since the H1 it echoed
   is gone.
3. **Grandfathered literals** remain in components from earlier approved
   boards ("What matters more to you?", "Change search", the slider's two
   end labels, "Difference", "Not covered"); the literal sweep's contract —
   every **changed or new** string arrives from the registry or build JSON —
   passes with zero hits, and the em dash / "·" separators are treated as
   punctuation, as the attribution line already does.
4. **Display-only bumps vs old permalinks**: `/r/` pins are exact-match, so
   any m2.3.0 permalink would land on the earlier-edition page, whose copy
   ("the way we count has been improved") would overstate a tones-only bump.
   No such link exists — the site is undeployed — but a compat policy for
   display-only bumps should be decided before launch.
5. **Blank-crime popover** keeps its why-blank sentence before the caution —
   my reading of "the blank state still needs its sibling"; the alternative
   (caution alone) would leave a blank card whose popover never says why.
6. **British/American forms shipped verbatim** as instructed: new American
   "favors"/"theaters"/"Note:" beside surviving British "favours" (movers
   line), "stabilised" (rent note), "neighbourhoods" (mover phrase) — one
   sentence, `slider_info`, mixes "towards" with "favors" exactly as given.
7. **pytest count moved 41→41** (one API vocabulary test updated: it pinned
   the deleted `stat_page_intro`; it now pins the new keys AND the two
   deletions). e2e moved 54→65 (eleven new phase-2f specs); vitest 38→49
   (the contrast suite).
8. **Nathan's `docs/sources.md`** stays untracked (his file, like the
   prompts); the registry `sources:` block now carries the shipping subset
   of it.

## Screenshots (results/phase2f/)

01 home hero + headline · 02 the weighting group · 03/04/05 card alignment
at 1280/1024/375 · 06 crime popover with "See more details" · 07 compare
differences + legend · 08 compare crime with per-100k units · 09 What we
measure (full page) · 10 rent stat page (source line, caution, header row,
no band labels).

## Gate check

1. **No number moves** — 10,935 fixture fields bitwise; 1,032 full-build
   exact scores at 0.00e+00; goldens diff is the version line. ✓
2. Four tones × every direction render (e2e computed-colour assertions);
   measured ≥4.5:1 on every background actually used; meaning never colour
   alone. ✓
3. Round trip through every nav destination; explicit params never
   overridden; reproduction-with-conflicting-cookie passes; dialect cases
   regenerated and green. ✓
4. Pointer into the note, link clickable and keyboard-reachable, Escape
   returns focus. ✓ (plus the clamp repair)
5. Every difference equals the displayed-value subtraction to displayed
   precision (e2e re-derivation sweep); `$` on rent; grey rules asserted;
   em dashes under suppression. ✓
6. Indicators aligned at 1280/1024/375, screenshots above. ✓
7. Literal sweep zero on changed/new strings; banned-vocabulary sweep zero
   across eleven shapes. ✓
8. Live source lines everywhere; rent page has header row, new caution, no
   band labels; intros gone from every page that carried them. ✓
9. axe: zero serious/critical on home, results, city, narrow, compare,
   compare landing, stat page, what-we-measure, how-it-works. ✓
