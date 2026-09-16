"""Scoring, m1.2.0 — five pillars over the cubes plus the static feature
matrix; pure numpy over a loaded Build.

Normalisation (§7.2), per request, across the RANKED SET FOR THIS QUERY
(never the build's full ranked set — suppression shrinks the query's set
and normalizing over the wrong one is a silent bias):
  extensive (pool):       winsorize 1/99 -> log10 -> min-max -> [0,100]
  intensive (everything): percentile rank -> [0,100], direction from the
                          registry (via the manifest features_block)

Attribution (ADR 0003): the FEATURE is the primitive. Each stat's
contribution is w_pillar_eff x weight_in_pillar_eff x (z_f - ref_f), where
ref_f is the median of that normalized feature across this query's ranked
set — defined once, at feature level, because the median of a weighted sum
is not the weighted sum of medians and two reference points would break
§7.5's exact additivity. A pillar's contribution is the sum of its
features'; the sum identity is asserted on every request.

Missing features (registry missing_data_policy): a metro missing a static
feature has its pillar-internal weights renormalized over what it has; a
metro missing an entire pillar has that pillar's weight redistributed
pro-rata; flags name what was missing. Missing never becomes zero.

Suppression (ADR 0002): the gate is n alone — min(n_alloc, kish) < 100,
empty pool, or empty rival set. No CV rule ranks or demotes anything;
shown_unranked is a permanently empty array kept for contract stability.

Every metro row (ranked or suppressed) carries a stats block, so the metro
and compare pages render from one /v1/rank response and never renormalize
over a smaller set. score_moe is a first-order propagation from the served
(upper-bound) intervals with the query's normalisation frozen — a
documented approximation that belongs in the detail, not the row.
"""
from __future__ import annotations

import numpy as np

from atlas.model.explain import format_value, render_explanation
from atlas.model.loader import Build
from atlas.model.preferences import (PILLARS, RACE_LEVELS, SEX_LEVELS,
                                     Request, pool_mask, resolve_weights,
                                     rival_spec)
from atlas.model.suppression import (PURITY_FLAG_BAR, suppression_reason,
                                     tier_masks)


def scored_features(build: Build) -> list[dict]:
    """Scored features in canonical order: pillar order (§7.5), registry
    order within a pillar. Derived from the manifest, never hardcoded."""
    feats = []
    for p in PILLARS:
        for fid, e in build.legend.items():
            if (e["pillar"] == p and e.get("status", "active") == "active"
                    and float(e["weight_in_pillar"]) > 0):
                feats.append({"id": fid, "pillar": p,
                              "u": float(e["weight_in_pillar"]),
                              "direction": int(e["direction"]),
                              "kind": e["kind"]})
    assert feats[0]["id"] == "pool_size" and feats[1]["id"] == "partners_per_rival"
    return feats


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
    import pandas as pd
    out = np.full(x.shape, np.nan)
    ok = ~np.isnan(x)
    v = x[ok]
    if len(v) == 0:
        return out
    if len(v) == 1:
        out[ok] = 50.0
        return out
    r = pd.Series(v).rank(method="average").to_numpy() - 1.0
    out[ok] = r / (len(v) - 1) * 100.0
    return out


def _pct_rank_interp(base: np.ndarray, moved: np.ndarray) -> np.ndarray:
    """Percentile of `moved` values within the fixed `base` distribution."""
    base = base[~np.isnan(base)]
    order = np.sort(base)
    n = len(order)
    if n <= 1:
        return np.full(np.shape(moved), 50.0)
    pos = np.searchsorted(order, moved, side="right") - 0.5
    return np.clip(pos, 0, n - 1) / (n - 1) * 100.0


def _feature_weights(z: np.ndarray, pillar_idx: np.ndarray, u: np.ndarray,
                     w_pillar: np.ndarray) -> np.ndarray:
    """Per-metro effective feature weights: within-pillar weights renormalize
    over available features; a fully-missing pillar's weight is redistributed
    pro-rata. Rows sum to 1 wherever any pillar is available."""
    avail = ~np.isnan(z)
    uu = np.where(avail, u[None, :], 0.0)
    n_pillars = int(pillar_idx.max()) + 1
    onehot = np.eye(n_pillars)[pillar_idx]              # (F, P)
    psum = uu @ onehot                                   # (n, P)
    denom = psum[:, pillar_idx]
    with np.errstate(invalid="ignore", divide="ignore"):
        uu = np.where(denom > 0, uu / denom, 0.0)
    wp = (psum > 0) * w_pillar[None, :]
    tot = wp.sum(axis=1, keepdims=True)
    wp = np.where(tot > 0, wp / tot, 0.0)
    return uu * wp[:, pillar_idx]


def score_components(build: Build, ridx: np.ndarray, est: np.ndarray,
                     ratio: np.ndarray, weights: dict[str, float]) -> dict:
    """z, raw values, effective weights, score, feature-level reference and
    contributions for the ranked metros. Shared by rank() and the
    validation suite's replicate resampling."""
    feats = scored_features(build)
    n, F = len(ridx), len(feats)
    z = np.full((n, F), np.nan)
    raw = np.full((n, F), np.nan)
    for j, f in enumerate(feats):
        if f["id"] == "pool_size":
            raw[:, j] = est
            z[:, j] = _winsor_log_minmax(est)
        elif f["id"] == "partners_per_rival":
            raw[:, j] = ratio
            z[:, j] = _pct_rank(ratio)
        else:
            raw[:, j] = build.static[f["id"]][ridx]
            z[:, j] = _pct_rank(raw[:, j] * f["direction"])
    pillar_idx = np.array([PILLARS.index(f["pillar"]) for f in feats])
    u = np.array([f["u"] for f in feats])
    w_pillar = np.array([weights[p] for p in PILLARS])
    w_eff = _feature_weights(z, pillar_idx, u, w_pillar)

    avail = ~np.isnan(z)
    z_filled = np.where(avail, z, 0.0)
    score = (w_eff * z_filled).sum(axis=1)
    # Feature-level reference: median of each normalized feature across the
    # query's ranked set, defined ONCE (ADR 0003).
    ref = np.array([np.nanmedian(z[:, j]) if avail[:, j].any() else 0.0
                    for j in range(F)])
    contrib = w_eff * np.where(avail, z - ref[None, :], 0.0)
    # §7.5 exactness, asserted on every request: the decomposition adds up.
    ref_score = (w_eff * np.where(avail, ref[None, :], 0.0)).sum(axis=1)
    assert np.allclose(contrib.sum(axis=1), score - ref_score, atol=1e-9), (
        "feature-level attribution does not sum to score - reference")
    return {"feats": feats, "z": z, "raw": raw, "w_eff": w_eff,
            "score": score, "ref": ref, "contrib": contrib,
            "pillar_idx": pillar_idx}


def score_vector(build: Build, ridx: np.ndarray, est: np.ndarray,
                 ratio: np.ndarray, weights: dict[str, float]) -> np.ndarray:
    """Score only — the validation suite's replicate-resampling entry."""
    return score_components(build, ridx, est, ratio, weights)["score"]


def _pairing_rates(build: Build, sex: str, race_levels: tuple[str, ...]
                   ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(rate, moe, n_gate) per metro for the sought sex x selected race
    groups: the share of partnered people in any selected group whose
    partner is outside their OWN group. The margin is measured directly
    from the 80 replicate sums (V = (4/80) * sum((r_i - r)^2))."""
    p = build.pairing
    si = SEX_LEVELS.index(sex)
    ri = [RACE_LEVELS.index(r) for r in race_levels]
    num = p.num[:, si, ri].sum(axis=-1)
    den = p.den[:, si, ri].sum(axis=-1)
    n_alloc = p.n_alloc[:, si, ri].sum(axis=-1)
    sumw2 = p.sumw2[:, si, ri].sum(axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        kish = np.where(sumw2 > 0, den ** 2 / sumw2, 0.0)
        rate = np.where(den > 0, num / np.maximum(den, 1e-9), np.nan)
    gate = np.minimum(n_alloc, kish)
    nr = p.num_r[:, si, ri, :].astype(np.float64).sum(axis=1)   # (n, 80)
    dr = p.den_r[:, si, ri, :].astype(np.float64).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rr = np.where(dr > 0, nr / np.maximum(dr, 1e-9), rate[:, None])
    var = 4.0 / 80.0 * np.nansum((rr - rate[:, None]) ** 2, axis=1)
    moe = 1.645 * np.sqrt(var)
    return rate, moe, gate


def _row_flags(build: Build, i: int) -> list[str]:
    f = []
    if build.purity[i] < PURITY_FLAG_BAR:
        f.append("low_allocation_purity")
    if build.gq_flag[i]:
        f.append("gq_flag")
    missing = build.feature_flags[i]
    if missing:
        f.append(f"missing_features:{missing}")
    return f


def _context_stats(build: Build, i: int, ranked_rates: np.ndarray | None) -> list[dict]:
    """Metro-level context entries (never weighted, never scored): the
    interim cross-group pairing composition with its replicate-measured
    margin."""
    le = build.legend["cross_group_pairing_rate"]
    rate = build.pairing_metro["rate"][i]
    if np.isnan(rate):
        return [{"id": "cross_group_pairing_rate", "value": None,
                 "suppressed": "n_below_100"}]
    entry = {"id": "cross_group_pairing_rate",
             "value": round(float(rate), 4),
             "display": format_value(float(rate), le),
             "moe": round(float(build.pairing_metro["moe"][i]), 4),
             "moe_display": format_value(float(build.pairing_metro["moe"][i]), le),
             "n_unweighted": round(float(build.pairing_metro["n"][i]))}
    if ranked_rates is not None and len(ranked_rates):
        entry["standing"] = round(float(
            _pct_rank_interp(ranked_rates, np.array([rate]))[0]), 1)
    return [entry]


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

    universe = build.ranked_set
    suppressed, ranked = tier_masks(universe, est, n_gate, r_est)

    weights = resolve_weights(req, build.manifest["model_defaults"])
    reasons = {}
    for i in np.where(suppressed)[0]:
        r = suppression_reason(float(est[i]), float(n_gate[i]))
        reasons[r] = reasons.get(r, 0) + 1
    out = {"counts": {"universe": int(universe.sum()),
                      "ranked": int(ranked.sum()),
                      "shown_unranked": 0,
                      "suppressed": int(suppressed.sum()),
                      "suppressed_by_reason": reasons},
           "weights": weights,
           "few_metros_notice": bool(ranked.sum() < 40),
           "ranked": [], "shown_unranked": [], "suppressed": []}

    pairing = None
    if req.seeking.race_cube_levels:
        pairing = _pairing_rates(build, req.seeking.sex,
                                 req.seeking.race_cube_levels)

    ridx = np.where(ranked)[0]
    ranked_raw_by_feat: dict[str, np.ndarray] = {}
    ranked_metro_rates = None
    if len(ridx):
        ratio = est[ridx] / r_est[ridx]
        sc = score_components(build, ridx, est[ridx], ratio, weights)
        feats, z, raw, w_eff, score, contrib = (
            sc["feats"], sc["z"], sc["raw"], sc["w_eff"], sc["score"],
            sc["contrib"])
        for j, f in enumerate(feats):
            ranked_raw_by_feat[f["id"]] = raw[:, j]
        ranked_metro_rates = build.pairing_metro["rate"][ridx]
        ranked_metro_rates = ranked_metro_rates[~np.isnan(ranked_metro_rates)]

        # first-order score interval from the served pool/rival bounds,
        # normalisation frozen at the point estimates
        r_moe_rel = np.sqrt(rse[ridx] ** 2 + r_rse[ridx] ** 2)
        lo, hi = np.percentile(est[ridx], [1, 99])
        span = (np.log10(np.maximum(np.clip(est[ridx], lo, hi), 1)).max()
                - np.log10(np.maximum(np.clip(est[ridx], lo, hi), 1)).min())
        if span > 0:
            dz_pool = (np.log10(np.maximum(np.clip(est[ridx] + moe[ridx], lo, hi), 1))
                       - np.log10(np.maximum(np.clip(est[ridx] - moe[ridx], lo, hi), 1))
                       ) / span * 100.0 / 2
        else:
            dz_pool = np.zeros(len(ridx))
        ratio_hi = ratio * (1 + r_moe_rel)
        ratio_lo = ratio / (1 + r_moe_rel)
        dz_bal = np.abs(_pct_rank_interp(ratio, ratio_hi)
                        - _pct_rank_interp(ratio, ratio_lo)) / 2
        score_moe = w_eff[:, 0] * dz_pool + w_eff[:, 1] * dz_bal

        # standing = percentile of the raw value among this query's ranked
        # set, ascending — direction-free; the registry says which way is
        # scored as better.
        standing = np.column_stack([_pct_rank(raw[:, j])
                                    for j in range(raw.shape[1])])

        order = np.argsort(-score, kind="stable")
        for pos, k in enumerate(order):
            i = int(ridx[k])
            stats = []
            for j, f in enumerate(feats):
                le = build.legend[f["id"]]
                if np.isnan(z[k, j]):
                    stats.append({"id": f["id"], "pillar": f["pillar"],
                                  "value": None, "missing": True,
                                  "weight": 0.0, "contribution": None})
                    continue
                stats.append({
                    "id": f["id"], "pillar": f["pillar"],
                    "value": round(float(raw[k, j]), 4),
                    "display": format_value(float(raw[k, j]), le),
                    "standing": round(float(standing[k, j]), 1),
                    "z": round(float(z[k, j]), 2),
                    "weight": round(float(w_eff[k, j]), 4),
                    "contribution": round(float(contrib[k, j]), 2),
                })
            stats += _context_stats(build, i, ranked_metro_rates)
            pillar_contrib = {}
            for j, f in enumerate(feats):
                if not np.isnan(z[k, j]):
                    pillar_contrib[f["pillar"]] = (
                        pillar_contrib.get(f["pillar"], 0.0)
                        + float(contrib[k, j]))
            row = {
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
                "ratio_moe": round(float(ratio[k] * r_moe_rel[k]), 4),
                "rivals": round(float(r_est[i])),
                "allocation_purity": round(float(build.purity[i]), 3),
                "flags": _row_flags(build, i),
                "stats": stats,
                # pillar contributions are SUMS of their features' (ADR 0003)
                "contributions": [
                    {"pillar": p, "value": round(v, 2)}
                    for p, v in pillar_contrib.items()],
            }
            if pairing is not None:
                p_rate, p_moe, p_gate = pairing
                if p_gate[i] >= 100 and not np.isnan(p_rate[i]):
                    row["cross_group_pairing_rate"] = round(float(p_rate[i]), 4)
                    row["cross_group_pairing_moe"] = round(float(p_moe[i]), 4)
                    row["cross_group_pairing_n"] = round(float(p_gate[i]))
                else:
                    row["cross_group_pairing_rate"] = None
                    row["cross_group_pairing_suppressed"] = "n_below_100"
            else:
                row["cross_group_pairing_rate"] = None
            out["ranked"].append(row)
        for row in out["ranked"]:
            row["explanation"] = render_explanation(row, build.legend)

    for i in np.where(suppressed)[0]:
        stats = []
        for fid in ("median_gross_rent", "rpp_goods", "rpp_services_other",
                    "venues_per_100k", "resident_walkability_index",
                    "pleasant_days", "students_per_1k_adults"):
            v = float(build.static[fid][i])
            if np.isnan(v):
                stats.append({"id": fid,
                              "pillar": build.legend[fid]["pillar"],
                              "value": None, "missing": True})
                continue
            entry = {"id": fid, "pillar": build.legend[fid]["pillar"],
                     "value": round(v, 4),
                     "display": format_value(v, build.legend[fid])}
            base = ranked_raw_by_feat.get(fid)
            if base is not None and len(base):
                entry["standing"] = round(float(
                    _pct_rank_interp(base, np.array([v]))[0]), 1)
            stats.append(entry)
        stats += _context_stats(build, i, ranked_metro_rates)
        out["suppressed"].append({
            "cbsa": build.metro_levels[i],
            "name": build.titles[build.metro_levels[i]],
            "reason": suppression_reason(float(est[i]), float(n_gate[i])),
            "n_unweighted": round(float(n_gate[i])),
            "flags": _row_flags(build, i),
            "stats": stats,
        })
    return out
