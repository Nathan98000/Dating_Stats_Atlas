# Phase 4b — the side panel and the city rows

Every number here is read from a file under `results/phase4b/`; nothing
was recomputed for the report. Every change recorded here is **Nathan's
decision**, from his review of the home page.

**In plain words, for Nathan.** The side panel now reads as two short
forms with a line between them: "About you" (your sex, age, education and
race or ethnicity) and "Who you're looking for" (everything about the
people you're searching for), with "What matters more to you?" after them
as before. Race is one dropdown that starts on "Prefer not to say", which
means race isn't used. Picking a group is how a visitor turns it on, so
there's no switch and no small print beside it. The notes about where your
details go are gone from the panel; the Privacy page covers that. The "i"
beside Compatibility and the words under its number ("Above most cities"
and so on) are gone everywhere. The one explanation is now the "i" beside
"What matters more to you?", in your new wording, and on a same-sex search
it also says race isn't used there. Each city's big number is labelled
"Overall score". No number moved: the site shows the same figures in a new
layout, and every check on the numbers reads exactly as it did at
m4.0.0. Three things are yours: approve the wording (the two headings are
drafts), look at two points in your slider sentence (§2), and decide
whether three sentences on the Privacy and About us pages that still
mention the old switch should change (§2).

Commits: `bf6e57b` (the change), then this report. Nothing is deployed,
pushed or sent.

## 1. What changed on the page

1. **Race is one dropdown, off by default.** "My race or ethnicity" sits
   in About you. Its first option, "Prefer not to say", is selected by
   default and means race is not used; the eight groups follow. Choosing a
   group turns race on at once, with no request, because the page already
   holds every variant. The switch, its note and its "Choose one" option
   are gone. The browser stores a race only when one is chosen. A
   visitor's m4.0.0 details (`{raceOn, race}`) read as the same choice
   and are rewritten without the switch the first time they are read. On
   a same-sex search the dropdown is greyed out and keeps its value.
2. **No "about you" note.** It is gone from the panel and the registry.
   Education keeps "Prefer not to say" as its default.
3. **Two sections.** "About you" holds I'm a, My age, My education and My
   race or ethnicity. "Who you're looking for" holds I'm looking for, the
   age range, Single means, and the Education, Earning at least and Race &
   ethnicity filters. Each section is a fieldset whose caption is a
   level-2 heading, so a screen reader meets the same two groups and can
   jump between them. A rule divides them, and "What matters more to
   you?" follows as before.
4. **The slider's box** reads your text verbatim. On a same-sex search
   only, the served same-sex sentence (`match.note`) follows it in the
   box. The loader still holds that sentence to the kernel's same-sex
   components.
5. **No box beside Compatibility** on the result rows or the city card.
   The compare table never had one.
6. **No band words under Compatibility** on the rows, the city card and
   the compare table. Every other figure keeps its band words, and the
   API still sends the band.
7. **"Overall score"** sits above each row's score and its "out of 100".
   The compare table's "Score out of 100" row is now "Overall score". The
   overall score appears nowhere else: the city page's card shows the
   city's place in the results, not its score, and a permalink shows the
   same rows as the home page.

For you, as consequences of these changes:

- The city and compare pages have no side panel. On those pages the
  compatibility figure now has no explanation, and a same-sex visitor no
  longer sees the same-sex sentence. The box's link to the account on
  About us went with it; About us is still in the nav.
- The compare table's score cells now show only the number: "out of 100"
  was in the row's old label.
- Noticed, not changed: the caption of the "Race & ethnicity" filter
  group sits inside a div instead of first in its fieldset, so screen
  readers get no name for that group. It predates this phase, and axe
  does not flag it.

## 2. Copy for Nathan's approval

Every string added, changed or removed, old → new
(`results/phase4b/copy_changes.json`). They live in the registry and
reach the page through `/v1/meta`.

**Added**

- `strings.panel_about_you_heading` (the first section's heading; draft): "About you"
- `strings.panel_looking_for_heading` (the second section's heading; draft): "Who you're looking for"
- `strings.overall_score_label` (each result row and the compare table): "Overall score"

**Changed**

- `strings.slider_info` (the "What matters more to you?" box)
  - old: Leaning towards size favors larger cities with the most possible matches. Leaning towards compatibility favors cities where the people who match your search line up more closely with you on age and education, and on background if you include yours, based on historical Census marriage data.
  - new: Leaning towards size favors larger cities with the most possible matches. Leaning towards compatibility favors cities with people who match your search more closely on age, education, and background, based on historical Census couples data.
- The compare table's score row (typed in code until now; now `strings.overall_score_label`)
  - old: Score out of 100
  - new: Overall score

**Removed**

- `strings.self_race_switch_label`: "Include my race or ethnicity"
- `strings.self_race_switch_note`: "Off unless you turn it on. Your answer stays in this browser and is never sent to us."
- `strings.self_race_choose`: "Choose one"
- `strings.self_race_same_sex_note`: "Not used in a same-sex search."
- `strings.about_you_note`: "Your sex, education and race or ethnicity stay in this browser and are never sent to us. Education is optional and feeds only the compatibility figure; leave it unset and the average for people of your age and sex is used instead."
- `strings.match_info`: "This compares the people who match your search against the pattern of who actually forms couples in Census data: the age gaps and the education pairings that occur, and the racial and ethnic pairings too if you include your race or ethnicity. A higher number means the people here are more like the people who typically pair with someone in your situation."
- `strings.match_how_link`: "How this is measured"

**No longer shown with the figure** (kept in the registry, still sent by
the API): the five band labels of Compatibility — "Far below most
cities", "Below most cities", "About average", "Above most cities", "Far
above most cities".

**Moved, wording unchanged:** `strings.match_same_sex_note` moves from
the figure's box to the slider's box, on a same-sex search only.
**Reused, wording unchanged:** "Prefer not to say" is also the race
dropdown's default, and "My race or ethnicity" labels the one race
dropdown.

**The two section headings** (drafts): "About you" and "Who you're
looking for".

**The "marriage data" note.** Your sentence says "historical Census
couples data", not "marriage data". Couples is what the figure is fitted
on: opposite-sex spouses and unmarried partners (RELSHIPP 21 and 22), and
same-sex ones (23 and 24) for a same-sex search. So the concern the brief
raised doesn't arise with this wording, and the sentence ships verbatim.
"Historical" fits too: the fit uses every couple in the 2020–2024
survey, with recent unions weighted most. Two points in the same
sentence, for you (not reworded):

- "on age, education, and background": by default the figure uses no
  background. Race or ethnicity counts only if the visitor picks one; the
  m4.0.0 text said "and on background if you include yours".
- "cities with people who match your search more closely": the figure
  measures how closely the people who match the search resemble the
  people who actually pair with someone like the visitor. It doesn't
  measure how closely they match the search.

**The Privacy page and About us.** Both still describe the behaviour: the
details stay in the browser, the server works out every answer, the
cookie holds none of them, and race is never used on a same-sex search.
Three sentences name the switch that is gone. They are listed here and
not rewritten:

- Privacy, "About you": "Your race or ethnicity is used only if you switch it on."
- About us, "Compatibility": "Your race or ethnicity is used only if you switch it on, and then only for this figure; with it off, the figure uses no racial or ethnic pairing at all."
- About us, "What do the race and ethnicity boxes do?": "Your own race or ethnicity is a separate setting: it is off unless you switch it on, stays in your browser, and affects only the compatibility figure."

## 3. Gate check

| The brief's gate | Reading | |
| --- | --- | --- |
| No served number changes | build 5b780e4f2444 keeps its id: every data file matches its manifest hash, and only the manifest's strings and timestamp changed. goldens.json is byte-identical (sha256 `76f8d408…`), the persona snapshot equals m4.0.0's record byte for byte, and the three variant-case responses are identical (`served_numbers_check.json`) | pass |
| `build.validate`, every hard gate | 11 of 11 on 5b780e4f2444. Stability reads 1.0 (nothing touched), 2,065 explanations are checked, and the variant gate checks 1,620 selections and 185,850 rows. The report equals the m4.0.0 ship record except its git stamp, time and the gate's run time (`validation_report.json`) | pass |
| pytest | 122 passed (`test_counts.json`) | pass |
| Playwright | 102 passed, 0 flaky: 94 before, plus 8 new in `e2e/phase4b.spec.ts` | pass |
| vitest | 91 passed: 84 before, plus 7 new in `tests/about-you.test.ts` | pass |
| Axe | no serious or critical issue in 12 runs: the 11 page shapes, plus a same-sex search with the dropdown set aside and the slider's box open | pass |
| Banned vocabulary | none in the registry (loader), every served line (the validate gates above) or 12 page shapes (e2e) | pass |
| The Phase 4 network test | passes with the new dropdown: no request, cookie, link or permalink carries a detail | pass |
| Your slider text, verbatim | the API test holds `/v1/meta`'s string to it; the e2e test holds the box's text to the registry's | pass |
| Nothing deployed, pushed or sent | local commits only | pass |

The new tests cover the two labelled sections and their fields; the
dropdown's default and a chosen group selecting exactly the variant the
API computed, with no request; none of the removed notes anywhere on the
home page, in the markup or on screen; the slider's box against the
registry, with the same-sex sentence only on a same-sex search; no box and
no band words with the figure on the rows, the city card and compare;
"Overall score" on every row, both sort orders, and in compare; and the
m4.0.0 migration, in the browser and as a unit test of every stored shape.

## 4. Deviations

One line each; `results/phase4b/deviations.md` is identical.

- Change 3 (the markup): each section is a fieldset whose legend holds a level-2 heading, so a screen reader gets both the group and the heading (the brief offered either); the dividing rule sits on a wrapper, because a fieldset's own top border would run through its legend.
- The new registry keys are named `panel_about_you_heading`, `panel_looking_for_heading` and `overall_score_label`; the brief named none.
- Change 1 (the disabled look): the site's drawn select had no disabled style, so the race select set aside on a same-sex search gets one (grey text on the paper background, a not-allowed cursor) — CSS only.
- Change 1 (the migration): a stored m4.0.0 object is rewritten in the new shape the first time it is read, and one with the switch off, or on with no group chosen, reads as no race — exactly what m4.0.0 used; a unit test holds every m4.0.0 shape to m4.0.0's rule.
- The shared variant cases (`web/tests/variant_cases.json`) are regenerated in the new stored shape: all three API responses are byte-identical, every m4.0.0 race-on case selects the same rows, the one old case with a race but no switch now means race on, and a tenth case is added.
- The served strings live in the build's manifest, so `cube.build` refreshed build 5b780e4f2444's manifest in place (data identical, id kept) and `make_fixture` rebuilt the test fixture from it; goldens.json came out byte-identical, so MODEL_VERSION stays m4.0.0 — `versions.py` asks for a bump only when a golden moves, and a display-only patch bump like m2.3.1's would rewrite goldens.json's version line, which the brief holds byte-identical.
- The new e2e tests read the registry strings from the test API (`/v1/meta` on port 8600) and name the exact variant a page must show by running the browser's own selector over that API's response — requests made by the test, never by a page.
- The Phase 2d and Phase 3 screenshot scripts (`web/scripts/shoot_phase2d.mjs`, `shoot_phase3.mjs`) still name the figure's removed information box; they record those phases' screenshots and are not tests, so they are left as they are.

## After the phase (2026-09-29)

Nathan approved the copy in §2 for now, including the two section headings
and his slider sentence as written. The three sentences that still name the
removed switch are flagged for rewording before launch (PHASE4.md, "After
the phase"). On 2026-09-30, at Nathan's request, they were reworded to
"used only if you include it", and he approved them (PHASE4.md, "After
the phase").
