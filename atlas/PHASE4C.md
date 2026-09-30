# Phase 4c — same-sex searches: own race selectable, balance shown

Every number here is read from a file under `results/phase4c/`; nothing
was recomputed for the report. Both changes are **Nathan's decisions**.

## 1. In plain words, for Nathan

On a same-sex search, "My race or ethnicity" can now be changed. It looks
greyed out, and pointing at it, or tabbing to it with the keyboard, shows
your sentence saying why it isn't used; on a phone, where nothing can be
pointed at, a small "i" beside the label shows the same sentence. A choice made there changes nothing on that
search, is remembered, and counts as soon as the visitor looks for the
opposite sex. A same-sex search now also shows the dating pool balance: a
man looking for men aged 27–38 sees how many single men there are per 100
single women of those ages — the number a woman looking for the same men
sees (124 per 100 in San Francisco, 113 in New York). Nothing else moved:
every city's score and place is exactly what it was, on all 518 test
searches. Because a number the site shows changed, the model's version
goes from m4.0.0 to m4.1.0, as the project's rule asks; the data are the
same. Three things are yours: approve the name of the small "i" button (a
draft), confirm that the old "balance doesn't apply" note can go, and
decide whether one About us sentence, which still says balance doesn't
apply to same-sex searches, should change (§3).

Commits: `00a0938` (the change), then this report. Nothing is deployed,
pushed or sent.

## 2. The two changes

### Own race stays selectable on a same-sex search (ADR 0018 amended)

- **Operable.** The select is neither disabled nor aria-disabled. A choice
  is stored in the browser as usual and changes nothing on the same-sex
  search, because every race selects the same variant there (the figure
  uses no race; ADR 0018 §3). When the search turns opposite-sex the rows
  become that race's variant at once. The e2e test checks all three,
  including that choosing a race sends nothing.
- **Muted within WCAG AA.** Grey text on the paper background, a grey
  label and a dashed grey border (`muted_contrast.json`): text 4.83:1 on
  its fill, label 5.13:1 on the panel, border 5.13:1 against the panel and
  4.83:1 against its fill (4.5 and 3 needed). The e2e test reads the
  colours off the rendered page and holds them to AA. axe finds nothing.
- **The info box.** Nathan's sentence, `strings.self_race_same_sex_tip`,
  arrives through `/v1/meta`. It shows while the pointer is over the field
  (the pointer can move onto the box) and while the select has keyboard
  focus, and Escape dismisses it. It is always the select's description
  (`aria-describedby`), so a screen reader announces it on focus.
- **Touch screens.** Under `(hover: none)` an information button beside
  the label opens the same text (the existing `InfoTip`). Wherever a
  pointer can hover, the button is hidden and the box does the job.
- **Opposite-sex searches** show the plain field — the same colours as the
  education select beside it — with no box and no button.

### Dating pool balance on same-sex searches (ADR 0004 amended)

- **The definition.** Balance is the single people of the sought sex per
  100 single people of the other sex, in the search's ages and marital
  statuses, before any other filter. On an opposite-sex search the other
  sex is the visitor's own, so the figure is unchanged. On a same-sex
  search it is the figure an opposite-sex search for the same people
  shows. A man seeking men 27–38 sees, on the real build: San Francisco
  124 men per 100 women, Los Angeles 119, San Jose 155, New York 113,
  Seattle 139 (`served_numbers_check.json`).
- **In code.** `balance_masks_for` builds the second mask from the
  opposite of the sought sex. `_balance_block` has no same-sex branch; the
  sample gate still applies, so on the same-sex view 99,771 of the 99,974
  rows across the test searches show a figure and the rest show the gate's
  note. `balance_applies` is gone: only the home footnote read it.
- **Sent once.** Balance no longer depends on the visitor, so the response
  carries it once (`variants.balance`: the words and every row's block,
  aligned to the rows) instead of once per own sex (`variants.by_sex`).
  Every test search's response is smaller: the default search's goes from
  1,527,926 to 1,496,326 bytes, and from 229,408 to 229,011 gzipped
  (`served_numbers_check.json`, `layout_check.json`).
- **Every "doesn't apply" display is gone.** The note under the slider,
  the home footnote's same-sex alternative (the footnote is always
  `balance_caption`), and the tally's note (the tally shows only the
  sample gate's note now). `balance_same_sex` is retired.
- **Shown everywhere balance appears.** The home rows, the city card, a
  left-out city's surviving balance and compare, for a same-sex visitor
  exactly as for an opposite-sex one (e2e).

## 3. Copy for Nathan's approval

Every string added, retired or reused, old → new
(`results/phase4c/copy_changes.json`). Registry strings reach the page
through `/v1/meta`.

**Added**

- `strings.self_race_same_sex_tip` (the race field's box on a same-sex search; your wording, verbatim): "This information is not used to calculate compatibility for same-sex couples because not enough data is available to make a reliable estimate."
- `strings.self_race_same_sex_tip_label` (**draft**; the name a screen reader gives the touch screen's "i" button): "Why race or ethnicity isn't used here"

**Retired**

- `policy_strings.balance_same_sex`: "In a same-sex search everyone is on both sides of the comparison, so balance doesn’t apply — the other measures carry its weight."

**Reused, wording unchanged:** `balance_caption` is now the home
footnote on every search; the tally's caption reads "124 men per 100
women" on a same-sex search too.

**About us and Privacy.** One sentence no longer fits. It is listed here
and not rewritten:

- About us, "What does balance compare?": "In a same-sex search everyone is on both sides of the comparison, so balance doesn't apply."

The paragraph before it ("all single men per 100 single women (or the
mirror, if you're looking for women)") still reads true, and so does the
registry's definition of balance. The Privacy page says nothing about
balance, and nothing on it is made untrue by this phase. The three
Phase 4b sentences that name the old race switch are still waiting for
you (PHASE4B.md §2). (Reworded on 2026-09-30; PHASE4.md, "After the
phase".)

## 4. Gate check and test counts

| The brief's gate | Reading | |
| --- | --- | --- |
| Balance is displayed and not scored (checked before any change) | The loader refuses a build whose `pool_balance` is not context-only with weight 0; no score function takes balance (the score reads pool size, compatibility and the static features); `test_balance_displayed_never_scored` | pass |
| Scores and ranks identical, every search | All 518 ADR 0011 test searches (51 same-sex): every variant's ranks, scores, figures and explanations byte-identical in the API response, balance aside; `rank()` for both own sexes, 1,036 of 1,036 identical (`served_numbers_check.json`) | pass |
| The ADR 0011 gate against the m4.0.0 reference | 1.0, no search touched (`validation_report.json`) | pass |
| Opposite-sex balance byte-identical | 518 of 518 searches, in the API response and in `rank()` | pass |
| Same-sex balance equals the opposite-sex figure | 518 of 518; before, all 518 same-sex views were "not applicable" | pass |
| What moved | The same-sex balance blocks only. Goldens: only `same_sex_pool`'s `balance_per_100` (empty → 155, 113, 111, 126, 133, 127, 108, 128, 150) and its two left-out cities' balance (now shown), beside the version line, so MODEL_VERSION is m4.1.0. The persona snapshot equals m4.0.0's but for its version line. In each shared variant case, the three same-sex selections moved in balance only | as expected |
| The response must not grow | 518 of 518 smaller: gzipped 0.989–0.998 of m4.0.0's size, raw 0.947–0.979 (`layout_check.json`) | pass |
| `build.validate`, every hard gate | 11 of 11. 2,065 explanations checked; the variant gate checks 1,620 selections and 185,850 rows. The report equals Phase 4b's except for the version, stamps, run time, the differential's float noise (1.98e-07 → 2.09e-07), and the same-sex persona's rows now showing balance | pass |
| pytest | 123 passed: 122 before, plus 1 new API test; one engine test rewritten (`test_counts.json`) | pass |
| vitest | 92 passed: 91 before, plus 1 new | pass |
| Playwright | 110 passed, 0 flaky: 102 before, plus 8 new in `e2e/phase4c.spec.ts` | pass |
| axe | No serious or critical issue in 14 runs: the 12 before, plus the same-sex search with the tip open from the keyboard and the touch screen's box open | pass |
| Banned vocabulary | None in the registry (checked at load), in any served line (the validate gates) or on 17 page shapes (e2e: the 12 before, plus 5 in Phase 4c — a same-sex search's home page with the tip open, city card, left-out city and compare, and the default search) | pass |
| The Phase 4 privacy guarantees | The network test passes unchanged; choosing a race on a same-sex search sends no request; the search change's request carries only the visitor's age | pass |
| No user-facing string in code | Both new strings are in the registry; the retired one left `model/suppression.py` | pass |
| Nothing deployed, pushed or sent | Local commits only | pass |

## 5. Deviations

One line each; `results/phase4c/deviations.md` is identical.

- Balance is sent once, column by column, in `variants.balance` (m4.0.0's `by_sex` cut to one copy); putting the block back in every row, tried first, made every test search's gzipped response 0.35–1.04% larger (`layout_check.json`), which the brief rules out.
- The block keeps its field `seeker_word` (and `balance_words` its key `seeker`), which now names the other sex: renaming either would change every opposite-sex block, which the brief holds byte-identical.
- MODEL_VERSION is m4.1.0 because the golden fixture's same-sex vector gained its balance (`versions.py`: a moved golden needs a bump); minor, not a display-only patch like m2.3.1, since a served figure changed, and not major, since no score moved; the build keeps its id, its manifest refreshed in place.
- `balance_same_sex` lived only in `model/suppression.py`'s policy strings (served through `/v1/meta`), not in the registry file; it is removed there, and the registry loader now refuses the key.
- A second registry string, `self_race_same_sex_tip_label` (drafted, then approved by Nathan after the report, §6), names the touch screen's "i" button: `InfoTip` needs an accessible name and no user-facing string lives in code; the brief named only the tip.
- The box opens on keyboard focus (`:focus-visible`), not on the focus a click or a tap gives: a click is already a hover and a touch screen has the button; as the select's description the sentence is announced on every focus.
- The muted border is dashed and dark grey (ink-3): the site's usual control border is 1.31:1 on white (`muted_contrast.json`), below the 3:1 AA asks of a control's edge, and the brief holds the muted border to AA; the usual border is noticed, not changed.
- Phase 4b's disabled style for selects (`select.ctl:disabled`) goes, since no select is disabled now; the muted style replaces it.
- The build gate's SQL mirror of the balance masks (`validate._spec_to_sql`) follows the new definition, so the cube-vs-SQL differential still compares two implementations of one definition (worst relative error 2.09e-07; it was 1.98e-07).
- Three older e2e checks that the race select is disabled on a same-sex search (two in `phase4b.spec.ts`, one in `phase3b.spec.ts`) now check that it is enabled (the Phase 3b one also that it is muted); the engine test `test_same_sex_balance_is_not_applicable` becomes `test_same_sex_balance_is_the_opposite_sex_figure`; the Phase 4 network test is unchanged.
- The home footnote loses its `data-variant` veil, since it no longer depends on the visitor; the city and compare pages' balance cells keep theirs, which is harmless.
- The About us sentence saying balance doesn't apply stayed, as the brief's Records section asks, until Nathan decided (§3); he removed it after the report (§6), and the "no 'doesn't apply' anywhere" test now reads About us too, beside `/v1/meta`, the rank response and the home, city and compare pages.
- The shared web test cases are regenerated: `variant_cases.json` (the response's shape and, in each case, the same-sex selections' balance) and `permalink_cases.json` (only the model version in each link).
- The m4.1.0 persona snapshot (`results/phase4c/snapshot_m4_1_0.json`) is committed as the ship record; it equals m4.0.0's but for its version line.
- Noticed, then retired on Nathan's call after the report (§6): `pipeline/build/score_snapshot._exact_scores`, a Phase 2d instrument that `split_equivalence.py` and `race_change_report.py` used, passed the balance ratio where `score_vector` now takes the compatibility figure; it fed no served number and ran only by hand, but its "exact scores" had been wrong since m3.0.0.

## 6. Nathan's calls after the report (2026-09-29)

Nathan answered §3, then made one more call:

1. **The "i" button's name is approved.** "Why race or ethnicity isn't
   used here" (`strings.self_race_same_sex_tip_label`) is no longer a
   draft. Nothing served changes; the registry's comment and ADR 0018 say
   so.
2. **Retiring `balance_same_sex` is confirmed.**
3. **The About us sentence is removed.** "In a same-sex search everyone
   is on both sides of the comparison, so balance doesn't apply." leaves
   `docs/methodology.md` (the About us page), removed rather than
   rewritten; the paragraph before it reads true for both kinds of search.
   ADR 0004's amendment records it, and the Phase 4c test that no "doesn't
   apply" is served or shown now reads About us too.
4. **The stale helper is retired.** Nathan weighed fixing or retiring
   `score_snapshot._exact_scores` (§5) and chose to retire it:
   `pipeline/build/score_snapshot.py` and the two Phase 2d and 2e scripts
   that imported it, `split_equivalence.py` and `race_change_report.py`,
   are deleted. Their original checks cannot be re-run under today's
   engine (the m2-era builds they compared no longer load), and the
   release snapshot (`phase3b_snapshot.py`), the ADR 0011 gate and this
   phase's `served_numbers_check.py` do the same work. What they produced
   stays: `results/phase2d/split_equivalence.json` and its m2.0.0 and
   m2.1.0 snapshots, `results/phase2e/race_change_report.json` and its
   m2.3.0 snapshot, and the reports and ADRs that cite them. The code is
   in git history at `62117f4`; the two docstrings that named the scripts
   say so.

After these calls (`test_counts.json`, regenerated): pytest 123 and
vitest 92 pass, and Playwright passes 110 of 110 with none flaky, the
About us sweep included (the retirement changed no web file, so only
pytest ran again after it). `cube.build` finds build 5b780e4f2444
unchanged (the registry change is a comment), so every served number is
as §4 records. The copy record (`copy_changes.json`) marks the button's
name approved, the retirement confirmed and the sentence removed.

