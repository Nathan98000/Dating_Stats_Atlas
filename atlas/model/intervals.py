"""Served intervals — the Gate 0 Option 2 mechanism, pure numpy.

served_RSE = exp( X·beta + metro_offset ) × inflation[race stratum]

where X = [1, log n_alloc, log(kish/n_alloc), log share, marital_never,
marital_any, race dummies]. The inflation factors are the one-sided
calibration (97.5th train percentile of true/central per race stratum);
validated coverage and overstatement ship in the manifest and the
methodology page. The served MOE can overstate, by design; it must not
understate — product copy says "at least this wide", never "±".

Conservative composition rules for query shapes outside the calibration
grid: a multi-select race filter takes the elementwise MAX served RSE over
the selected levels; a non-canonical marital subset takes the MAX over the
three canonical screens. Both err wide, never narrow.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MARITAL_CANONICAL = {frozenset([0]): "never",
                     frozenset([0, 1]): "not_married",
                     frozenset([0, 1, 2]): "any"}


@dataclass
class IntervalModel:
    feature_names: list[str]
    coef: np.ndarray                # aligned to feature_names
    race_levels: list[str]          # order of the race dummy block
    offsets: np.ndarray             # (n_metros,) shrunk per-metro offsets
    inflation: dict[str, float]     # race stratum -> one-sided factor
    meta: dict                      # measured coverage / overstatement etc.

    def _x(self, n_alloc, kish, share, marital_key: str, race_key: str):
        n = len(n_alloc)
        cols = [np.ones(n), np.log(np.maximum(n_alloc, 1e-9)),
                np.log(np.maximum(kish, 1e-9) / np.maximum(n_alloc, 1e-9)),
                np.log(np.maximum(share, 1e-12)),
                np.full(n, 1.0 if marital_key == "never" else 0.0),
                np.full(n, 1.0 if marital_key == "any" else 0.0)]
        for rl in self.race_levels:
            cols.append(np.full(n, 1.0 if race_key == rl else 0.0))
        return np.column_stack(cols)

    def _served_one(self, n_alloc, kish, share, marital_key, race_key):
        x = self._x(n_alloc, kish, share, marital_key, race_key)
        central = np.exp(x @ self.coef + self.offsets)
        return central * self.inflation.get(race_key,
                                            max(self.inflation.values()))

    def served_rse(self, n_alloc: np.ndarray, kish: np.ndarray,
                   share: np.ndarray, marital_levels: frozenset[int],
                   race_keys: list[str] | None) -> np.ndarray:
        """Upper-bound RSE per metro. race_keys are CUBE level names
        (nh_black, ...) or None for no filter."""
        marital = MARITAL_CANONICAL.get(frozenset(marital_levels))
        marital_opts = [marital] if marital else ["never", "not_married", "any"]
        race_opts = race_keys if race_keys else ["none"]
        out = None
        for mk in marital_opts:
            for rk in race_opts:
                s = self._served_one(n_alloc, kish, share, mk, rk)
                out = s if out is None else np.maximum(out, s)
        bad = (n_alloc <= 0) | (kish <= 0) | (share <= 0)
        out = np.where(bad, np.inf, out)
        return out
