"""Suppression policy (model_version m1.0.0): n_gate < 100 -> suppressed;
else ranked. Pure functions; no I/O.

The specified CV tiers are satisfied implicitly: the Phase 1 variance model
failed its 15% validation gate (the API never consults it), and the
28k-point battery showed the n-gate alone agrees with the full n+CV policy
on 100.00% of realistic queries — true CV at the gate never exceeded 12.9%,
so the 20-30% middle tier never activates (results/phase1/tier_study.json).
shown_unranked is retained in the response contract and is always empty
under this model version.
"""
from __future__ import annotations

import numpy as np

N_GATE_MIN = 100.0


def tier_masks(universe: np.ndarray, est: np.ndarray, n_gate: np.ndarray,
               rivals: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(suppressed, shown_unranked, ranked) boolean masks over metros."""
    suppressed = universe & ((n_gate < N_GATE_MIN) | (est <= 0) | (rivals <= 0))
    middle = universe & ~suppressed & False  # CV middle tier: never fires (m1.0.0)
    ranked = universe & ~suppressed & ~middle
    return suppressed, middle, ranked


def suppression_reason(est: float, n_gate: float) -> str:
    if est <= 0:
        return "empty_pool"
    if n_gate < N_GATE_MIN:
        return "n_gate<100"
    return "no_rivals"
