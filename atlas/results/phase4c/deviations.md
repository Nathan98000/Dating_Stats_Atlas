# Phase 4c deviations

One line each; PHASE4C.md's list is kept identical.

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
- Noticed, not changed: `pipeline/build/score_snapshot._exact_scores`, a Phase 2d instrument that `split_equivalence.py` and `race_change_report.py` use, still passes the balance ratio where `score_vector` now takes the compatibility figure; it feeds no served number and runs only by hand, but its "exact scores" have been wrong since m3.0.0.
