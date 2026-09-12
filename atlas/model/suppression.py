"""Suppression policy, m1.1.0 — the full D08 three-tier policy, computable
again because Gate 0 shipped a served CV (the one-sided calibrated bound):

    suppressed        n_gate < 100, or served CV > 30%, or empty pool/rivals
    shown_unranked    20% < served CV <= 30%
    ranked            served CV <= 20% and n_gate >= 100

The served CV is an upper bound (it can overstate, never understate on
97.5% of validated points), so the CV rules err toward NOT ranking — the
conservative direction for a product called Stats. Reason strings follow
the §8.2 contract vocabulary.

Purity (Phase 1 open item 4, measured in Phase 2a): interval coverage does
not degrade at low purity and calibration agreement drops only ~5pp in the
worst bin, so purity is a FLAG, not a gate — metros below PURITY_FLAG_BAR
carry "low_allocation_purity" in every response.
"""
from __future__ import annotations

import numpy as np

N_GATE_MIN = 100.0
CV_SUPPRESS = 0.30
CV_UNRANKED = 0.20
PURITY_FLAG_BAR = 0.5
FEW_METROS_NOTICE = 40


def tier_masks(universe: np.ndarray, est: np.ndarray, n_gate: np.ndarray,
               rivals: np.ndarray, served_cv: np.ndarray
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    suppressed = universe & ((n_gate < N_GATE_MIN) | (served_cv > CV_SUPPRESS)
                             | (est <= 0) | (rivals <= 0))
    middle = universe & ~suppressed & (served_cv > CV_UNRANKED)
    ranked = universe & ~suppressed & ~middle
    return suppressed, middle, ranked


def suppression_reason(est: float, n_gate: float, served_cv: float) -> str:
    if est <= 0:
        return "empty_pool"
    if n_gate < N_GATE_MIN:
        return "n_below_100"
    if served_cv > CV_SUPPRESS:
        return "cv_above_30"
    return "no_rivals"


# Fixed strings keyed to the policy table (§5.2) — rendered verbatim, never
# improvised per request. Versioned with MODEL_VERSION.
POLICY_STRINGS = {
    "n_below_100": "Too few people in this sample to estimate.",
    "cv_above_30": "The estimate is too imprecise to publish.",
    "cv_above_20": "Shown with its margin of error, but too imprecise to rank.",
    "empty_pool": "No one in this sample matches.",
    "no_rivals": "No comparable rival population in this sample.",
    "ranked": "Precise enough to support an ordering; the margin of error is "
              "shown beside the figure.",
    "interval": "Every margin shown is 'at least this wide': the true margin "
                "of error is at or below the shown margin on at least 95% of "
                "held-out validation queries (measured: 97.5%), and the shown "
                "margin overstates the true one by 23% at the median "
                "(gate: at most 25%). Margins are calibrated upper bounds, "
                "never plus-or-minus.",
    "low_allocation_purity": "A large share of this metro's estimate arrives "
                             "through PUMAs it shares with other areas; "
                             "systematic allocation error is likelier here.",
}
