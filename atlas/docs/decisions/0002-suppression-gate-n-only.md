# ADR 0002 — Suppression gates on sample size alone; the CV tiers are removed

**Status:** decided 2026-09-12 by Nathan. Amends **D08** of the proposal and supersedes the
two CV rows of the §5.2 display-policy table. Implemented in `m1.2.0` (Phase 2b).

## Decision

A metro is suppressed when `min(n_alloc, n_kish) < 100`, or when its pool or rival set is
empty. Everything else in the ranked set receives a rank. **No coefficient-of-variation rule
suppresses a metro, and none demotes one to a shown-but-unranked tier.** `shown_unranked`
remains in the response contract as a permanently empty array so that clients are unaffected;
the `cv_above_20` and `cv_above_30` reason strings are retired from the code.

The served margin of error is **unchanged** and still renders beside every population figure
in the required words. This decision governs which metros are ranked, never what is shown next
to a number.

## Why

Three findings, in the order they arrived:

1. **The middle tier never fired on the data.** Phase 1's tier study, over 23,262 ranked-set
   battery points with true 81-replicate CVs: once `min(n_alloc, kish) ≥ 100` holds, true CV
   never exceeded **12.9%** (p50 4.4%, p99 9.8%). The 20–30% tier fired on **zero** points, the
   CV > 30% rule fired on zero points the n-gate had not already caught, and the n-gate alone
   agreed with the full specified policy on **100.00%** of points. Phase 1 recommended removal;
   `m1.0.0` implemented it.

2. **Phase 2a reinstated the tiers against a padded number.** Gate 0 shipped a deliberately
   one-sided interval: the served margin is calibrated to sit at or above the true margin
   (coverage 97.5%), overstating it by a median **23.4%** and a p90 **51.5%**. D08's tiers were
   then computed on that served CV, on the reasoning that every rule should err toward not
   ranking. Each half of that is defensible; the composition was not chosen by anyone.

3. **The composition moves a published threshold.** Dividing the 20% cutoff by the padding
   puts the effective cutoff at a true CV of **16.2%** at median overstatement and **13.2%** at
   p90 — against a true-CV distribution that tops out near 12.9%. So the tier is either inert,
   or it fires only where the padding is loosest, in which case every demotion it produces is a
   property of the interval model rather than of the metro — while the visitor reads "too
   imprecise to order." On the 12 pinned golden vectors it is inert today (`shown_unranked: 0`
   on all twelve).

Removing the rule is therefore the honest option in both branches: it deletes a rule that
cannot fire on the data, and with it the possibility of a demotion nobody intended. It also
returns the project to Phase 1's measured recommendation, which had evidence behind it.

## What this commits to

- `model_version` bumps to `m1.2.0`; goldens regenerate with a commit note (§5.4 versions the
  suppression policy, and D08's thresholds are covered by golden tests).
- `docs/methodology.md` drops the two CV rows and states plainly why a rule that never fired
  was removed rather than carried. The suppression policy remains **ours, not Census's** — the
  point of §5.2 is that the threshold is a published product judgment, and this is that
  judgment being revised on measurement.
- The "fewer than 40 metros ranked" notice (§5.2, final row) is unaffected.
- D11's design intent is preserved: honesty rests on the bar plus a visible margin in every
  row, and the bar now means exactly what the methodology page says it means.

## Evidence still to be recorded

Phase 2b must report **the p99 and maximum true CV in the served region of the 480-shape
battery** (n_gate ≥ 100). If that maximum is below 20%, the removed rule provably could not
have fired on this build's data, and that number becomes the whole justification — to be added
here and to the methodology page. If it exceeds 20%, the premise of this decision is wrong and
the removal must stop and be reported instead; this ADR was taken on the assumption, inherited
from Phase 1's smaller battery, that it does not.

## Re-open trigger

Lower `MIN_METRO_POP` to 100,000 (D03, Phase 5) and the ranked set roughly doubles with the
thinnest-sample metros in the country. Re-run the tier study then: a 250k floor is what makes
true CV top out near 13%, and that is the assumption this decision rests on.
