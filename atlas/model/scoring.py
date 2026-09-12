"""Scoring, m1.1.0 — five pillars over the cubes plus the static feature
matrix; pure numpy over a loaded Build.

Normalisation (§7.2), per request, across the RANKED SET FOR THIS QUERY
(never the build's full ranked set — suppression shrinks the query's set
and normalizing over the wrong one is a silent bias):
  extensive (pool):       winsorize 1/99 -> log10 -> min-max -> [0,100]
  intensive (everything): percentile rank -> [0,100], direction from the
                          registry (baked into the build's feature matrix
                          as a sign)

Missing features (registry missing_data_policy): a metro missing a static
feature has its pillar-internal weights renormalized over what it has; a
metro missing an entire pillar has that pillar's weight redistributed
pro-rata; flags name what was missing. Missing never becomes zero.

Score = 100-scaled linear combination; contributions are exact:
w_k * (z_k(c) - median over ranked of z_k), in score points (§7.5).

score_moe is a first-order propagation: z recomputed at the served interval
endpoints with the query's normalisation frozen — documented approximation,
built from served (upper-bound) intervals so it inherits their
conservatism.
"""
from __future__ import annotations

import numpy as np

from atlas.model.loader import Build
from atlas.model.preferences import (PILLARS, Request, pool_mask, resolve_weights,
                                     rival_spec)
from atlas.model.suppression import (PURITY_FLAG_BAR, suppression_reason,
                                     tier_masks)

STATIC_PILLAR_FEATURES = {
    "cost": ["median_gross_rent", "rpp_goods", "rpp_services_other"],
    "reach": ["venues_per_100k", "resident_walkability_index"],
    "lifestyle": ["pleasant_days", "students_per_1k_adults"],
}


def _winsor_log_minmax(x: np.ndarray, lo_hi=(1, 99)) -> np.ndarray:
    lo, hi = np.percentile(x, lo_hi)
    x = np.clip(x, lo, hi)
    x = np.log10(np.maximum(x, 1.0))
    span = x.max() - x.min()
    if span <= 0:
        return np.full_like(x, 50.0)
    return (x - x.min()) / span * 100.0


def _pct_rank(x: np.ndarray) -> np.ndarray:
    """Average-rank percentile in [0,100]; NaNs stay NaN."""
    out = np.full(x.shape, np.nan)
    ok = ~np.isnan(x)
    v = x[ok]
    if len(v) == 1:
        out[ok] = 50.0
        return out
    order = np.argsort(v, kind="stable")
    ranks = np.empty(len(v))
    ranks[order] = np.arange(len(v), dtype=float)
    # average ties
    import pandas as pd
    r = pd.Series(v).rank(method="average").to_numpy() - 1.0
    out[ok] = r / (len(v) - 1) * 100.0
    return out


def _pillar_z(build: Build, ridx: np.ndarray, z_pool: np.ndarray,
              z_bal: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[list[str]]]:
    """(z matrix [n_ranked, 5 pillars], effective weight matrix same shape
    normalized per metro by the missing-data policy, flags per metro)."""
    n = len(ridx)
    z = np.full((n, len(PILLARS)), np.nan)
    z[:, 0], z[:, 1] = z_pool, z_bal
    for pj, pillar in enumerate(PILLARS[2:], start=2):
        feats = STATIC_PILLAR_FEATURES[pillar]
        cols, wts = [], []
        for f in feats:
            raw = build.static[f][ridx] * build.static_direction[f]
            cols.append(_pct_rank(raw))
            wts.append(build.static_weight[f])
        fz = np.column_stack(cols)
        w = np.array(wts)
        avail = ~np.isnan(fz)
        wsum = (avail * w).sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            z[:, pj] = np.where(wsum > 0,
                                np.nansum(fz * w, axis=1) / wsum, np.nan)
    flags = []
    for k in range(n):
        f = []
        i = ridx[k]
        if build.purity[i] < PURITY_FLAG_BAR:
            f.append("low_allocation_purity")
        missing = build.feature_flags[i]
        if missing:
            f.append(f"missing_features:{missing}")
        flags.append(f)
    return z, flags


def _effective_weights(z: np.ndarray, w_pillar: dict[str, float]) -> np.ndarray:
    """Per-metro pillar weights with missing pillars redistributed pro-rata."""
    w = np.array([w_pillar[p] for p in PILLARS])
    have = ~np.isnan(z)
    ww = have * w
    tot = ww.sum(axis=1, keepdims=True)
    return np.where(tot > 0, ww / tot, 0.0)


def rank(build: Build, req: Request) -> dict:
    mask_p = pool_mask(req.seeking)
    rspec = rival_spec(req)
    mask_r = pool_mask(rspec)

    est = (build.pool_flat @ mask_p).astype(np.float64)
    n_alloc = (build.count_flat @ mask_p).astype(np.float64)
    sumw2 = (build.sumw2_flat @ mask_p).astype(np.float64)
    r_est = (build.pool_flat @ mask_r).astype(np.float64)
    r_alloc = (build.count_flat @ mask_r).astype(np.float64)
    r_sumw2 = (build.sumw2_flat @ mask_r).astype(np.float64)

    with np.errstate(divide="ignore", invalid="ignore"):
        kish = np.where(sumw2 > 0, est ** 2 / sumw2, 0.0)
        r_kish = np.where(r_sumw2 > 0, r_est ** 2 / r_sumw2, 0.0)
    n_gate = np.minimum(n_alloc, kish)
    share = est / np.maximum(build.pool_pop, 1.0)
    r_share = r_est / np.maximum(build.pool_pop, 1.0)

    im = build.intervals
    rse = im.served_rse(n_alloc, kish, share, req.seeking.marital_levels,
                        list(req.seeking.race_cube_levels)
                        if req.seeking.race_cube_levels else None)
    r_rse = im.served_rse(r_alloc, r_kish, r_share, rspec.marital_levels, None)
    with np.errstate(invalid="ignore"):
        moe = np.where(est > 0, 1.645 * rse * est, 0.0)
        r_moe = np.where(r_est > 0, 1.645 * r_rse * r_est, 0.0)

    universe = build.ranked_set
    suppressed, middle, ranked = tier_masks(universe, est, n_gate, r_est, rse)

    weights = resolve_weights(req, build.manifest["model_defaults"])
    out = {"counts": {"universe": int(universe.sum()), "ranked": int(ranked.sum()),
                      "shown_unranked": int(middle.sum()),
                      "suppressed": int(suppressed.sum())},
           "weights": weights,
           "few_metros_notice": bool(ranked.sum() < 40),
           "ranked": [], "shown_unranked": [], "suppressed": []}

    ridx = np.where(ranked)[0]
    if len(ridx):
        ratio = est[ridx] / r_est[ridx]
        z_pool = _winsor_log_minmax(est[ridx])
        z_bal = _pct_rank(ratio)
        z, flags = _pillar_z(build, ridx, z_pool, z_bal)
        w_eff = _effective_weights(z, weights)
        score = np.nansum(z * w_eff, axis=1)
        med = np.nanmedian(z, axis=0)
        contrib = w_eff * (z - med[None, :])

        # first-order score interval from the served pool/rival bounds,
        # normalisation frozen at the point estimates
        lo, hi = np.percentile(est[ridx], [1, 99])
        span = (np.log10(np.maximum(np.clip(est[ridx], lo, hi), 1)).max()
                - np.log10(np.maximum(np.clip(est[ridx], lo, hi), 1)).min())
        if span > 0:
            dz_pool = (np.log10(np.maximum(np.clip(est[ridx] + moe[ridx], lo, hi), 1))
                       - np.log10(np.maximum(np.clip(est[ridx] - moe[ridx], lo, hi), 1))
                       ) / span * 100.0 / 2
        else:
            dz_pool = np.zeros(len(ridx))
        ratio_rel = np.sqrt(rse[ridx] ** 2 + r_rse[ridx] ** 2)
        ratio_hi = ratio * (1 + ratio_rel)
        ratio_lo = ratio / (1 + ratio_rel)
        dz_bal = np.abs(_pct_rank_interp(ratio, ratio_hi)
                        - _pct_rank_interp(ratio, ratio_lo)) / 2
        score_moe = w_eff[:, 0] * dz_pool + w_eff[:, 1] * dz_bal

        order = np.argsort(-score, kind="stable")
        rank_of = {int(ridx[k]): int(pos + 1) for pos, k in enumerate(order)}
        pops = build.pool_pop
        from atlas.model.explain import comparator
        comp = comparator({int(ridx[k]): float(pops[ridx[k]]) for k in range(len(ridx))},
                          rank_of)
        for pos, k in enumerate(order):
            i = int(ridx[k])
            out["ranked"].append({
                "cbsa": build.metro_levels[i],
                "name": build.titles[build.metro_levels[i]],
                "rank": pos + 1,
                "score": round(float(score[k]), 1),
                "score_moe": round(float(score_moe[k]), 1),
                "pool": round(float(est[i])),
                "pool_moe": round(float(moe[i])),
                "cv": round(float(rse[i]), 3),
                "n_unweighted": round(float(n_gate[i])),
                "tier": "measured",
                "ratio": round(float(ratio[k]), 4),
                "ratio_moe": round(float(ratio[k] * ratio_rel[k]), 4),
                "rivals": round(float(r_est[i])),
                "cross_group_pairing_rate": None,   # Phase 3 (pairing kernel)
                "allocation_purity": round(float(build.purity[i]), 3),
                "flags": flags[k],
                "comparator": (build.metro_levels[comp[i]]
                               if comp.get(i) is not None else None),
                "contributions": [
                    {"pillar": p, "value": round(float(contrib[k, j]), 2)}
                    for j, p in enumerate(PILLARS) if not np.isnan(z[k, j])],
            })
    if out["ranked"]:
        from atlas.model.explain import metric_record, render_explanation
        rows_by_cbsa = {r["cbsa"]: r for r in out["ranked"]}
        midx = {c: k for k, c in enumerate(build.metro_levels)}
        for r in out["ranked"]:
            comp_row = rows_by_cbsa.get(r["comparator"]) if r["comparator"] else None
            statics = {f: float(build.static[f][midx[r["cbsa"]]])
                       for f in build.static}
            rec = metric_record(r, comp_row, statics)
            r["explanation"] = render_explanation(
                rec, r["name"], comp_row["name"] if comp_row else None)

    for i in np.where(middle)[0]:
        out["shown_unranked"].append({
            "cbsa": build.metro_levels[i],
            "name": build.titles[build.metro_levels[i]],
            "reason": "cv_above_20",
            "pool": round(float(est[i])), "pool_moe": round(float(moe[i])),
            "cv": round(float(rse[i]), 3),
            "n_unweighted": round(float(n_gate[i])),
            "allocation_purity": round(float(build.purity[i]), 3),
        })
    for i in np.where(suppressed)[0]:
        out["suppressed"].append({
            "cbsa": build.metro_levels[i],
            "reason": suppression_reason(float(est[i]), float(n_gate[i]),
                                         float(rse[i])),
            "n_unweighted": round(float(n_gate[i])),
        })
    return out


def _pct_rank_interp(base: np.ndarray, moved: np.ndarray) -> np.ndarray:
    """Percentile of `moved` values within the fixed `base` distribution."""
    order = np.sort(base)
    n = len(order)
    if n <= 1:
        return np.full(len(moved), 50.0)
    pos = np.searchsorted(order, moved, side="right") - 0.5
    return np.clip(pos, 0, n - 1) / (n - 1) * 100.0
