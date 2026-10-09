# ADR 0003 — Explanations lead with the stats that moved the score; the comparator is retired

**Status:** decided 2026-09-16 by Nathan. Retires **D10**, amends **§9**'s explanation
design and the §9 metric-record contract Phase 2a pinned, and replaces the user-facing
terminology of the `balance` pillar. Implemented in Phase 2b. Amended 2026-10-03
(m4.1.1, after Nathan's report from the live site): decision 2's list, the last section.

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
   *[Amended in m4.1.1: the two price levels are one item, and no stat is named against its
   city's card — the last section.]*

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

## Amended in m4.1.1 (2026-10-03): everyday prices is one item, and no stat is named against its card

Nathan found two errors on the live site, both in decision 2's list as the movers line names it.

- **A phrase named twice.** Goods prices and services prices are two scored stats, and both
  carry the mover phrase "everyday prices", the card that shows them together. A row could read
  "Biggest pluses: ..., everyday prices, everyday prices", or name everyday prices as a plus and
  as the minus at once. They are now one item: their contributions are added before the top
  three are picked, and the sum's sign names it once (`explain.mover_units`).
- **A minus its card contradicted.** Austin read "Walkable neighbourhoods counts against it"
  while its card said "More walkable than most". Each was right on its own terms. The score
  measures a stat against the middle of the cities ranked for the search (decision 1's
  reference); the card measures it against every city of the build. In a narrower search the
  ranked cities are mostly big, walkable metros, and a city walkable by the national yardstick
  can sit below their middle. The line now never names a stat as a minus where the city's card
  says better than most (its two upper bands, read in the score's direction), nor as a plus
  where the card says worse than most; the next item takes its place
  (`explain.mover_sides`, `pick_movers`). The price pair answers to the everyday-prices card.

The reference, the attribution's exactness and every score are unchanged; only which items a
line names, and `top_stats` with them, which now lists both price ids for the everyday-prices
item. Over the 518 ADR 0011 test searches on build 2dbd9ebfa7ff, every /v1/rank response is
identical to m4.1.0's but for its explanations, and so are all 1,036 single-seeker rankings.
13,022 of the default variants' 98,415 lines change: those repeating a phrase fall from 11 to
0, and those naming a stat against its card from 182 to 0
(`results/movers_fix/served_numbers_check.json`).

## Amended in m4.2.1 (Phase 5, 8 October 2026): two pluses, then the biggest minus

The design audit of 8 October 2026 found two more problems in the line, and Nathan approved a
new shape (Phase 5 brief, decision 4).

- **It could hide the main downside.** The line named the top three items whatever their sign,
  so a city with three large pluses named no minus at all: San Francisco's line was three pluses,
  though rent cost it 3.6 points. The pick is now at most two pluses, largest first, then the
  single biggest eligible minus (`explain.pick_movers`, `MAX_PLUSES`, `MAX_MINUSES`). The m4.1.1
  sides rule, `TOP_STATS_MIN_POINTS` and the merged price levels are unchanged.
- **Its grammar.** "· Z counts against it" disagreed with plural phrases ("Walkable
  neighbourhoods counts against it"). The line now reads "Biggest pluses: X, Y · Biggest minus:
  Z", or "Biggest minus: Z" when nothing is a plus; the middle-of-the-pack sentence is unchanged.

The pick is also served as data, `movers: [{key, sign}]`, beside `top_stats` and `summary_line`
on every explanation (key: the item's first stat id; its registry `chip_label` names it), so the
result chips never re-derive it. No score, rank, figure, band or suppression moves: over the 518
ADR 0011 test searches on build 63c4e5fa51bf every /v1/rank response is identical to m4.2.0's
without its explanations, as are all 1,036 single-seeker rankings and all 387 profiles
(`results/phase5/served_numbers_commit_c.json`).

## Amended in m4.3.0 (Phase 6, 9 October 2026): the chips name lifestyle items only

DRAFT for Nathan's approval (Phase 6, commit B; his decision 5). The round-3 review (F12) found
the result chips repeating: in the default search 8 of the top 10 read "▲ Dating pool
▲ Compatibility ▼ Rent", so they did not tell cities apart, and the pool and the compatibility
figure already have their own column and tile. Each explanation now also carries
`lifestyle_movers: [{key, sign}]`, from `explain.pick_lifestyle_movers`: the same rule as the
line (the m4.1.1 sides rule, `TOP_STATS_MIN_POINTS`, at most two pluses largest first, then the
single biggest eligible minus, the two price levels one item) over the lifestyle items only —
those whose pillar is one the visitor weights with the importance controls (cost, social life,
student life, weather). A row with no eligible lifestyle item serves `[]` and shows no chips.
The chips read `lifestyle_movers`; `summary_line` and `movers` are unchanged, and screen readers
keep the full line. Over the 518 ADR 0011 test searches every /v1/rank response is identical to
m4.2.1's without its explanations, every default-variant line, `top_stats` and `movers` is
unchanged, and so are all 1,036 single-seeker rankings (`results/phase6/served_numbers_commit_b.json`).
