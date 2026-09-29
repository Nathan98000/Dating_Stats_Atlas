# Phase 4b deviations

One line each; PHASE4B.md's list is kept identical.

- Change 3 (the markup): each section is a fieldset whose legend holds a level-2 heading, so a screen reader gets both the group and the heading (the brief offered either); the dividing rule sits on a wrapper, because a fieldset's own top border would run through its legend.
- The new registry keys are named `panel_about_you_heading`, `panel_looking_for_heading` and `overall_score_label`; the brief named none.
- Change 1 (the disabled look): the site's drawn select had no disabled style, so the race select set aside on a same-sex search gets one (grey text on the paper background, a not-allowed cursor) — CSS only.
- Change 1 (the migration): a stored m4.0.0 object is rewritten in the new shape the first time it is read, and one with the switch off, or on with no group chosen, reads as no race — exactly what m4.0.0 used; a unit test holds every m4.0.0 shape to m4.0.0's rule.
- The shared variant cases (`web/tests/variant_cases.json`) are regenerated in the new stored shape: all three API responses are byte-identical, every m4.0.0 race-on case selects the same rows, the one old case with a race but no switch now means race on, and a tenth case is added.
- The served strings live in the build's manifest, so `cube.build` refreshed build 5b780e4f2444's manifest in place (data identical, id kept) and `make_fixture` rebuilt the test fixture from it; goldens.json came out byte-identical, so MODEL_VERSION stays m4.0.0 — `versions.py` asks for a bump only when a golden moves, and a display-only patch bump like m2.3.1's would rewrite goldens.json's version line, which the brief holds byte-identical.
- The new e2e tests read the registry strings from the test API (`/v1/meta` on port 8600) and name the exact variant a page must show by running the browser's own selector over that API's response — requests made by the test, never by a page.
- The Phase 2d and Phase 3 screenshot scripts (`web/scripts/shoot_phase2d.mjs`, `shoot_phase3.mjs`) still name the figure's removed information box; they record those phases' screenshots and are not tests, so they are left as they are.
