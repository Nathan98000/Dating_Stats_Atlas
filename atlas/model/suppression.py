"""Suppression policy, m1.2.0 — the gate is sample size alone (ADR 0002):

    suppressed    min(n_alloc, kish) < 100, or an empty pool, or an empty
                  rival set (the odds ratio has no denominator)
    ranked        everything else in the ranked set

The CV tiers are removed. Measured basis: over the 480-shape battery's
served region (n_gate >= 100, 23,028 metro-points), true 81-replicate CV
maxes at 11.8% (p99 9.8%) — the 20%/30% rules could not fire on the data,
while computing them on the served CV (a bound that overstates by 23% at
the median) let the interval model's conservatism demote metros, which
nobody decided. `shown_unranked` remains in the response contract as a
permanently empty array; the `cv_above_20` / `cv_above_30` reason strings
can no longer be produced.

The served margin is UNAFFECTED: every population figure still carries its
margin in the row, in the exact words of POLICY_STRINGS["interval"]. This
module decides which metros get a rank, never what is shown beside a
number.

Purity (measured in Phase 2a): interval coverage does not degrade at low
purity and calibration agreement drops only ~5pp in the worst bin, so
purity is a FLAG, not a gate. GQ_SHARE_FLAG_BAR mirrors the adversarial
validation gate: metros where dorm/barracks residents are a large share of
the adult population carry a visible flag rather than being dropped.
"""
from __future__ import annotations

import numpy as np

N_GATE_MIN = 100.0
PURITY_FLAG_BAR = 0.5
GQ_SHARE_FLAG_BAR = 0.15
FEW_METROS_NOTICE = 40


def tier_masks(universe: np.ndarray, est: np.ndarray, n_gate: np.ndarray,
               rivals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(suppressed, ranked). No middle tier exists in m1.2.0."""
    suppressed = universe & ((n_gate < N_GATE_MIN) | (est <= 0) | (rivals <= 0))
    ranked = universe & ~suppressed
    return suppressed, ranked


def suppression_reason(est: float, n_gate: float) -> str:
    if est <= 0:
        return "empty_pool"
    if n_gate < N_GATE_MIN:
        return "n_below_100"
    return "no_rivals"


# Fixed strings keyed to the policy table (§5.2) — rendered verbatim, never
# improvised per request or in the frontend. Versioned with MODEL_VERSION.
# "interval" carries the required margin wording: "at least this wide",
# never a bare plus-or-minus.
POLICY_STRINGS = {
    "n_below_100": "Too few people in this sample to estimate.",
    "empty_pool": "No one in this sample matches.",
    "no_rivals": "No one in this sample is looking for the same kind of "
                 "match, so the odds ratio has no denominator here.",
    "ranked": "Enough sample to support an ordering; the margin of error is "
              "shown beside the figure.",
    "suppression_policy": "A metro is suppressed when fewer than 100 "
                          "effective respondents (the smaller of the "
                          "allocated count and the Kish effective sample "
                          "size) sit in the queried range, or when its pool "
                          "or comparison set is empty. No precision rule "
                          "beyond that: a rule keyed to the coefficient of "
                          "variation was measured unable to fire on this "
                          "data and was removed rather than carried "
                          "(ADR 0002).",
    "interval": "Every margin shown is 'at least this wide': the true margin "
                "of error is at or below the shown margin on at least 95% of "
                "held-out validation queries (measured: 97.5%), and the shown "
                "margin overstates the true one by 23% at the median "
                "(gate: at most 25%). Margins are calibrated upper bounds, "
                "never plus-or-minus.",
    "margin_row": "margin at least",
    "cv_detail": "The precision figure shown here is the served coefficient "
                 "of variation — an upper bound from the same calibrated "
                 "mechanism as the margin. It overstates the true CV by 23% "
                 "at the median and it decides nothing: no rule ranks or "
                 "suppresses on it.",
    "score_moe_detail": "The score margin is a first-order approximation "
                        "stacked on the one-sided pool and odds bounds, with "
                        "this query's normalization frozen — an "
                        "approximation, labelled as one, and shown here "
                        "rather than in the ranking row.",
    "pairing_interval": "The pairing-rate margin is measured directly from "
                        "the survey's 80 replicate weights (90% confidence) "
                        "— the same machinery every other margin here is "
                        "calibrated against, computed exactly for this "
                        "figure rather than bounded by a model.",
    "pairing_framing": "This is how couples here actually pair — observed "
                       "couples describe who matched, not who was available, "
                       "and never what people here want.",
    "low_allocation_purity": "A large share of this metro's estimate arrives "
                             "through PUMAs it shares with other areas; "
                             "systematic allocation error is likelier here.",
    "gq_flag": "A notable share of this metro's adults live in group "
               "quarters such as dormitories or barracks; pools here can "
               "lean on those populations.",
    "missing_features": "One or more context stats are unavailable for this "
                        "metro; the remaining stats carry their weight, and "
                        "nothing missing was counted as zero.",
    "few_metros": "Fewer than 40 metros have enough sample to rank for this "
                  "query. What is shown is what the data supports — a "
                  "narrower list is the product working correctly.",
}
