"""Scoring and ranking — pure numpy over a loaded Build; no I/O.

Queries are masked matrix-vector products over the flattened cubes:

    est_m   = pool_cube[m]  @ mask        (one BLAS sgemv for all metros)
    n_m     = count_cube[m] @ mask        (allocated respondents, fractional)
    kish_m  = est_m^2 / (sumw2_cube[m] @ mask)
    n_gate  = min(n_m, kish_m)            (Phase 1 correction 2)

Scoring (m1.0.0, pool + balance pillars): per-request normalisation —
winsorize at the 1st/99th percentile across the ranked metros for this
query, log10 for the pool pillar, min-max to [0,1]; linear score with exact
attribution w_k * (z_k(c) - median(z_k)).

Rivals (Phase 1 correction 4, symmetric crude kernel): same sex as the
seeker, seeker's age +/-5 (clamped to 18-70), the pool's education floor,
and the pool's marital screen. No income floor on rivals (rivals compete
for the pool regardless of their own income) and no race screen (the crude
kernel is race-blind; the empirical pairing kernel is Phase 3). Both
decisions are deliberate and documented here and in PHASE1.md.

No modeled MOE or CV ships in responses under m1.0.0 (see suppression.py).
"""
from __future__ import annotations

import numpy as np

from atlas.model.loader import Build
from atlas.model.preferences import SEX_LEVELS, mask_vector
from atlas.model.suppression import suppression_reason, tier_masks


def _winsor_minmax(x: np.ndarray, log: bool) -> np.ndarray:
    lo, hi = np.percentile(x, [1, 99])
    x = np.clip(x, lo, hi)
    if log:
        x = np.log10(np.maximum(x, 1.0))
    span = x.max() - x.min()
    if span <= 0:
        return np.full_like(x, 0.5)
    return (x - x.min()) / span


def rank(build: Build, seeker_sex: str, seeker_age: int, pool: dict,
         weights: dict | None = None) -> dict:
    """The /v1/rank computation. `pool` keys: sex (optional; default opposite
    of seeker), age_min, age_max, marital, education_min, income_min, race."""
    pool_sex = pool.get("sex") or SEX_LEVELS[1 - SEX_LEVELS.index(seeker_sex)]
    mask_p = mask_vector(pool_sex, pool["age_min"], pool["age_max"],
                         pool["marital"], pool.get("education_min"),
                         pool.get("income_min"), pool.get("race"))
    mask_r = mask_vector(seeker_sex, seeker_age - 5, seeker_age + 5,
                         pool["marital"], pool.get("education_min"), None, None)

    est = build.pool_flat @ mask_p
    n_alloc = build.count_flat @ mask_p
    sumw2 = build.sumw2_flat @ mask_p
    rivals = build.pool_flat @ mask_r

    with np.errstate(divide="ignore", invalid="ignore"):
        kish = np.where(sumw2 > 0, est.astype(np.float64) ** 2 / sumw2, 0.0)
    n_gate = np.minimum(n_alloc, kish)

    universe = build.ranked_set
    suppressed, middle, ranked = tier_masks(universe, est, n_gate, rivals)

    w = weights or {}
    wp, wb = float(w.get("pool", 0.5)), float(w.get("balance", 0.5))
    tot = wp + wb
    assert tot > 0, "weights must not both be zero"
    wp, wb = wp / tot, wb / tot

    out = {"counts": {"universe": int(universe.sum()), "ranked": int(ranked.sum()),
                      "shown_unranked": int(middle.sum()),
                      "suppressed": int(suppressed.sum())},
           "weights": {"pool": wp, "balance": wb},
           "ranked": [], "shown_unranked": [], "suppressed": []}

    ridx = np.where(ranked)[0]
    if len(ridx):
        ratio = est[ridx] / rivals[ridx]
        z_pool = _winsor_minmax(est[ridx].astype(np.float64), log=True)
        z_bal = _winsor_minmax(ratio.astype(np.float64), log=False)
        score = wp * z_pool + wb * z_bal
        med_p, med_b = float(np.median(z_pool)), float(np.median(z_bal))
        order = np.argsort(-score, kind="stable")
        for k in order:
            i = ridx[k]
            out["ranked"].append({
                "cbsa": build.metro_levels[i], "title": build.titles[build.metro_levels[i]],
                "pool": round(float(est[i])),
                "n_alloc": round(float(n_alloc[i]), 1),
                "n_kish": round(float(kish[i]), 1),
                "rivals": round(float(rivals[i])),
                "ratio": round(float(ratio[k]), 4),
                "score": round(float(score[k]), 6),
                "attribution": {
                    "pool": round(float(wp * (z_pool[k] - med_p)), 6),
                    "balance": round(float(wb * (z_bal[k] - med_b)), 6),
                },
            })
    for i in np.where(middle)[0]:
        out["shown_unranked"].append({
            "cbsa": build.metro_levels[i], "title": build.titles[build.metro_levels[i]],
            "pool": round(float(est[i])),
            "n_alloc": round(float(n_alloc[i]), 1),
            "rivals": round(float(rivals[i])),
            "ratio": round(float(est[i] / rivals[i]), 4) if rivals[i] > 0 else None,
        })
    for i in np.where(suppressed)[0]:
        out["suppressed"].append({
            "cbsa": build.metro_levels[i],
            "title": build.titles[build.metro_levels[i]],
            "reason": suppression_reason(float(est[i]), float(n_gate[i]))})
    return out
