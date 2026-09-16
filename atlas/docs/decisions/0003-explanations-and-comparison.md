# ADR 0003 — Explanations lead with the stats that moved the score; the comparator is retired

**Status:** decided 2026-09-16 by Nathan. Retires **D10**, amends **§9**'s explanation
design and the §9 metric-record contract Phase 2a pinned, and replaces the user-facing
terminology of the `balance` pillar. Implemented in Phase 2b.

## Context

Phase 2a's explanation layer renders, per ranked metro, the top two positive and top two
negative **pillar** contributions plus a comparator sentence ("Compared with Phoenix — the
closest metro by population that lands somewhere else — this is the trade you are making").
Read as a panel of 33 rows, that design has three problems. Pillars are too coarse to answer
"what actually makes this city fit me": a pillar is an aggregate of stats, and the reader
wants the stats. The full picture is nowhere: a row states four contributions and nothing
else, so there is no way to see everything the site knows about a metro. And the automatic
comparator answers a question the ranking already answers, using a metro the reader did not
choose.

## Decision

1. **Attribution becomes feature-level, and the feature level is the primitive.** A stat's
   contribution is `w_pillar × weight_in_pillar × (z_feature − reference_feature)`; a pillar's
   contribution is the sum of its features'. The reference is defined **once**, at feature
   level, as the median of each normalized feature across the query's own ranked set. It has
   to be defined once because the median of a weighted sum is not the weighted sum of medians:
   two independently-computed reference points would produce a decomposition that does not add
   up, and §7.5's exactness is the whole reason the explanation can be stated rather than
   inferred.

2. **A result leads with the handful of stats that moved it.** The top two or three stats by
   absolute contribution, each with its value in real units and what it did to the score. This
   list depends on the weight vector, so it changes as the size-versus-odds slider moves —
   which is the point: it answers "why this city, for the way *I* weighted things."

3. **Every stat is available for every city** — on the metro page, and by expanding a result
   row: display name, value in real units, standing across the ranked set, weight under the
   current preferences, and contribution. With no preferences set, values and standing show
   and contributions do not; there is nothing to attribute yet.

4. **The automatic comparator is retired (D10 reversed).** `comparator()`, `MIN_RANK_GAP`,
   `POPULATION_DISTANCE`, the `comparator` response field, and every comparator sentence go.
   The ranking is the comparison. A reader who wants a specific pair gets the compare page.

5. **A dedicated compare page.** Two metros chosen by the reader, side by side: rank, pool with
   its margin, odds, and every stat with both values, the difference, and each one's
   contribution under the current weights. The URL carries both metros and the preference
   vector, so a comparison is shareable and reproducible like every other view.

## Terminology

"Partners per rival" is retired. §12.3 already ruled that "market", "supply" and "inventory"
are accurate modelling terms and corrosive product copy; "rival" belongs in that family and
should never have reached a rendered string.

| Concept | Internal key (unchanged) | User-facing |
|---|---|---|
| `balance` pillar | `balance` | **Odds** |
| pool ÷ rivals | `ratio` | **matches per 10 people looking** (stored ratio × 10, one decimal) |
| rival set | `rivals` | never named directly; described as "people looking for the same kind of match" |

Long form, where a sentence is wanted: "For every 10 people looking for the same kind of
match, this metro has 9." Alternates considered and available by changing one registry value:
"available matches per 10 searchers", or the inverse framing "people looking per match".

Internal names do not change — the spreadsheet stays under the hood. And **no user-facing label
lives in code**: every registry feature gains `display_name`, `unit` and a one-line
`definition`, every pillar gains a `display_name`, the registry loader asserts they exist, and
every rendered string reads from the registry. Terminology then becomes a data change.

## Consequences

- `model/explain.py` loses the comparator and gains feature-level records; `model/scoring.py`
  emits feature contributions; `model/templates/` is rewritten; `api` drops `comparator` and
  carries a full stat block per metro.
- The §9 metric record — which Phase 2a pinned as the contract for the deferred build-time
  narratives — changes shape. Nothing consumes it yet, which is why this is cheap now and
  would not have been after those narratives were generated and reviewed.
- `model_version` bumps and goldens regenerate with a commit note, alongside the `m1.2.0`
  suppression change from ADR 0002.
- The compare page must render from a single `/v1/rank` response. Normalization is per query
  across that query's ranked set, so any endpoint that scored two metros in isolation would
  renormalize over a set of two and report numbers that disagree with the ranking page for the
  same preferences.
- The proposal's §5.3 mock row, §9 comparator rule, and D10 are superseded by this record.
