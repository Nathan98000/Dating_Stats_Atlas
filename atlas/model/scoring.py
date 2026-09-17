"""Scoring, m2.1.0 — six pillars over the cubes plus the static feature
matrix; pure numpy over a loaded Build.

ADR 0004's model change: the balance pillar scores DATING POOL BALANCE,
the plain sex ratio of single adults in the searched age range —
count(sought sex) / count(seeker sex), same ages, same marital selection,
never filtered by race, education or income. One quantity, computed once,
here: the pillar scores it and the UI displays it. The pool÷rivals ratio
and the rival mask are gone from the serving path.

Balance is gated separately from the pool (its two counts are whole
age-by-sex slices, so they clear the n-gate almost everywhere even when
the filtered pool does not): the city page and the narrow-search state can
still show balance when the pool has nothing to say.

Normalisation (§7.2), per request, across the RANKED SET FOR THIS QUERY:
  extensive (pool):       winsorize 1/99 -> log10 -> min-max -> [0,100]
  intensive (everything): percentile rank -> [0,100], direction from the
                          registry (via the manifest features_block)

Attribution stays feature-level (ADR 0003) with the reference defined once
as the feature-level median over the query's ranked set; the sum identity
is asserted on every request. Margins keep being computed and returned
(pool_moe, cv) — they no longer render anywhere, which is the display
decision, not a change to the mechanism (ADR 0004 item 3).
"""
from __future__ import annotations

from bisect import bisect_right

import numpy as np

from atlas.model.explain import format_value, summary_line, top_stats
from atlas.model.loader import Build
from atlas.model.preferences import (PILLARS, Request, balance_masks,
                                     pool_mask, resolve_weights)
from atlas.model.suppression import (N_GATE_MIN, POLICY_STRINGS,
                                     PURITY_FLAG_BAR, suppression_reason,
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
    assert feats[0]["id"] == "pool_size" and feats[1]["id"] == "pool_balance"
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
                     balance: np.ndarray, weights: dict[str, float]) -> dict:
    """z, raw values, effective weights, score, feature-level reference and
    contributions for the ranked metros. Shared by rank() and the
    validation suite's replicate resampling. `balance` is the sex ratio
    (sought/seeker), NaN where its own gate failed."""
    feats = scored_features(build)
    n, F = len(ridx), len(feats)
    z = np.full((n, F), np.nan)
    raw = np.full((n, F), np.nan)
    for j, f in enumerate(feats):
        if f["id"] == "pool_size":
            raw[:, j] = est
            z[:, j] = _winsor_log_minmax(est)
        elif f["id"] == "pool_balance":
            raw[:, j] = balance
            z[:, j] = _pct_rank(balance)
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
                 balance: np.ndarray, weights: dict[str, float]) -> np.ndarray:
    """Score only — the validation suite's replicate-resampling entry."""
    return score_components(build, ridx, est, balance, weights)["score"]


def _balance_block(build: Build, i: int, bal: dict, sought_word: str,
                   seeker_word: str) -> dict:
    """The one balance quantity, served per metro with its own gate
    (ADR 0004): value (ratio), per-100 integer, composed display strings.
    Never a bare number without its gate having passed — and never the
    degenerate "100 per 100" of a same-sex search, where both sides are
    the same people and the quantity does not exist."""
    if bal["same_sex"]:
        return {"available": False,
                "note": POLICY_STRINGS["balance_same_sex"]}
    if not bal["ok"][i]:
        return {"available": False,
                "note": POLICY_STRINGS["balance_unavailable"]}
    ratio = float(bal["ratio"][i])
    per_100 = int(round(ratio * 100))
    return {
        "available": True,
        "value": round(ratio, 4),
        "per_100": per_100,
        "display": POLICY_STRINGS["balance_row_caption"].format(
            ratio=per_100, sought=sought_word, seekers=seeker_word),
        "sought_word": sought_word,
        "seeker_word": seeker_word,
        "standing": (round(float(bal["standing"][i]), 1)
                     if bal["standing"] is not None
                     and not np.isnan(bal["standing"][i]) else None),
    }


def _band_of(build: Build, fid: str, i: int) -> dict | None:
    """Five-band standing across all 387 cities, cut on national quintiles
    (registry thresholds, registry labels; m2.1.0). The label states the
    POSITION; the tone comes from the registry's band_direction — cheap
    rent colours good, a big student share colours nothing. A feature with
    registry band_edges bands by ABSOLUTE value instead of percentile —
    population's case, where quantiles over mostly-small metros would call
    a 700k city 'one of the biggest'."""
    sa = build.standing_all.get(fid)
    le = build.legend.get(fid, {})
    if sa is None or np.isnan(sa[i]) or not le.get("band_labels"):
        return None
    pct = float(sa[i])
    bands = build.manifest["standing_bands"]
    edges = le.get("band_edges")
    # bisect on the manifest's plain lists: this runs ~3,000 times per
    # request (193 rows x 16 banded figures), and a numpy conversion per
    # call cost ~12 ms of the p50 before this was caught
    if edges:
        k = bisect_right(edges, float(build.static[fid][i]))
    else:
        k = bisect_right(bands["edges"], pct)
    return {"key": bands["keys"][k],
            "standing_all": round(pct, 1),
            "label": le["band_labels"][k],
            "tone": le["band_tones"][k]}


CRIME_RATE_IDS = ("violent_crime_rate", "property_crime_rate")


def _crime_block(build: Build, i: int) -> dict:
    """Crime context (Phase 2d item 5; D01: never scored). Rates render
    ONLY with their coverage figure and the FBI's caution attached, and
    only where coverage clears the registry floor — the reporting panel
    differs by metro, so a rate without its coverage would invite exactly
    the comparison the FBI cautions against. Everything here is composed
    from registry strings and legend fields; the rates' denominator is the
    covered population (never the metro's), which the adapter enforced."""
    strings = build.manifest["strings"]
    cfg = build.manifest["crime"]
    city = build.display_names[i].split(",")[0]
    vals = {fid: float(build.crime[fid][i]) for fid in
            (*CRIME_RATE_IDS, "crime_coverage")}
    coverage = vals["crime_coverage"]
    available = (not any(np.isnan(v) for v in vals.values())
                 and coverage >= float(cfg["coverage_floor"]))
    out: dict = {"available": available,
                 "caution": strings["crime_caution"]}
    if not available:
        out["note"] = strings["crime_blank"].format(city=city)
        return out
    cov_le = build.legend["crime_coverage"]
    cov_display = format_value(coverage, cov_le) + "%"
    out["coverage_line"] = strings["crime_coverage_line"].format(
        coverage=cov_display, year=int(cfg["year"]))
    out["coverage_pct"] = round(coverage * 100, 1)
    out["stats"] = []
    for fid in CRIME_RATE_IDS:
        le = build.legend[fid]
        out["stats"].append({
            "id": fid,
            "label": le["display_name"],
            "value": round(vals[fid], 1),
            "display": format_value(vals[fid], le),
            "unit_line": le["unit"],
        })
    return out


def _card_stats(build: Build, i: int) -> list[dict]:
    """The v3 city-page cards, straight from the artifact: value, display
    string, unit line, band. Every figure the card shows is composed here."""
    out = []
    for fid in build.manifest["city_cards"]:
        le = build.legend[fid]
        v = float(build.static[fid][i]) if fid in build.static else np.nan
        entry: dict = {"id": fid}
        if np.isnan(v):
            entry["value"] = None
            entry["missing"] = True
        else:
            entry["value"] = round(v, 4)
            if fid == "who_lives_here":
                # spoken figures, per the board: 700,000 people, of whom
                # 430,000 are adults — never precision to the person
                from atlas.model.explain import format_pop
                entry["display"] = format_pop(v)
                adults = float(build.pool_pop[i])
                entry["unit_line"] = le["unit_template"].format(
                    adults=format_pop(adults))
            else:
                entry["display"] = format_value(v, le)
                entry["unit_line"] = le.get("unit", "")
            band = _band_of(build, fid, i)
            if band:
                entry["band"] = band
        out.append(entry)
    return out


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


def rank(build: Build, req: Request) -> dict:
    mask_p = pool_mask(req.seeking)
    m_sought, m_seeker = balance_masks(req)

    est = (build.pool_flat @ mask_p).astype(np.float64)
    n_alloc = (build.count_flat @ mask_p).astype(np.float64)
    sumw2 = (build.sumw2_flat @ mask_p).astype(np.float64)

    b_sought = (build.pool_flat @ m_sought).astype(np.float64)
    b_sought_n = (build.count_flat @ m_sought).astype(np.float64)
    b_sought_w2 = (build.sumw2_flat @ m_sought).astype(np.float64)
    b_seeker = (build.pool_flat @ m_seeker).astype(np.float64)
    b_seeker_n = (build.count_flat @ m_seeker).astype(np.float64)
    b_seeker_w2 = (build.sumw2_flat @ m_seeker).astype(np.float64)

    with np.errstate(divide="ignore", invalid="ignore"):
        kish = np.where(sumw2 > 0, est ** 2 / sumw2, 0.0)
        k_sought = np.where(b_sought_w2 > 0, b_sought ** 2 / b_sought_w2, 0.0)
        k_seeker = np.where(b_seeker_w2 > 0, b_seeker ** 2 / b_seeker_w2, 0.0)
    n_gate = np.minimum(n_alloc, kish)
    share = est / np.maximum(build.pool_pop, 1.0)

    # the served margin: computed, returned, never rendered (ADR 0004)
    im = build.intervals
    rse = im.served_rse(n_alloc, kish, share, req.seeking.marital_levels,
                        list(req.seeking.race_cube_levels)
                        if req.seeking.race_cube_levels else None)
    with np.errstate(invalid="ignore"):
        moe = np.where(est > 0, 1.645 * rse * est, 0.0)

    # dating pool balance, gated separately per quantity (ADR 0004). For a
    # same-sex search the two counts are the same count and the ratio is 1
    # by construction — the quantity does not exist, so it is served as
    # not-applicable and its pillar weight redistributes (the check that
    # caught this: rank stability collapsed to 0.05 on the same-sex persona
    # because a constant pillar left the top-10 boundary to noise).
    same_sex = req.seeking.sex == req.self_sex
    bal_ok = ((np.minimum(b_sought_n, k_sought) >= N_GATE_MIN)
              & (np.minimum(b_seeker_n, k_seeker) >= N_GATE_MIN)
              & (b_seeker > 0)
              & (not same_sex))
    with np.errstate(divide="ignore", invalid="ignore"):
        bal_ratio = np.where(bal_ok, b_sought / np.maximum(b_seeker, 1e-9),
                             np.nan)

    universe = build.ranked_set
    suppressed, ranked = tier_masks(universe, est, n_gate)

    weights = resolve_weights(req, build.manifest["model_defaults"])
    reasons: dict[str, int] = {}
    for i in np.where(suppressed)[0]:
        r = suppression_reason(float(est[i]), float(n_gate[i]))
        reasons[r] = reasons.get(r, 0) + 1

    sought_word = "men" if req.seeking.sex == "male" else "women"
    seeker_word = "men" if req.self_sex == "male" else "women"

    out = {"counts": {"universe": int(universe.sum()),
                      "ranked": int(ranked.sum()),
                      "shown_unranked": 0,
                      "suppressed": int(suppressed.sum()),
                      "suppressed_by_reason": reasons},
           "weights": weights,
           "few_metros_notice": bool(ranked.sum() < 40),
           "balance_applies": not same_sex,
           "balance_words": {"sought": sought_word, "seeker": seeker_word},
           "ranked": [], "shown_unranked": [], "suppressed": []}

    ridx = np.where(ranked)[0]
    bal = {"ratio": bal_ratio, "ok": bal_ok, "standing": None,
           "same_sex": same_sex}
    if len(ridx):
        # standing of a metro's balance among the query's ranked set
        ranked_bal = bal_ratio[ridx]
        st = np.full(len(bal_ratio), np.nan)
        st[ridx] = _pct_rank(ranked_bal)
        off = np.where(~ranked & bal_ok)[0]
        if len(off):
            st[off] = _pct_rank_interp(ranked_bal, bal_ratio[off])
        bal["standing"] = st

        balance_scored = np.where(bal_ok[ridx], bal_ratio[ridx], np.nan)
        sc = score_components(build, ridx, est[ridx], balance_scored, weights)
        feats, z, raw, w_eff, score, contrib = (
            sc["feats"], sc["z"], sc["raw"], sc["w_eff"], sc["score"],
            sc["contrib"])

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
                entry = {
                    "id": f["id"], "pillar": f["pillar"],
                    "value": round(float(raw[k, j]), 4),
                    "display": format_value(float(raw[k, j]), le),
                    "standing": round(float(standing[k, j]), 1),
                    "z": round(float(z[k, j]), 2),
                    "weight": round(float(w_eff[k, j]), 4),
                    "contribution": round(float(contrib[k, j]), 2),
                }
                band = _band_of(build, f["id"], i)
                if band:
                    entry["band"] = band
                stats.append(entry)
            pillar_contrib: dict[str, float] = {}
            for j, f in enumerate(feats):
                if not np.isnan(z[k, j]):
                    pillar_contrib[f["pillar"]] = (
                        pillar_contrib.get(f["pillar"], 0.0)
                        + float(contrib[k, j]))
            row = {
                "cbsa": build.metro_levels[i],
                "name": build.titles[build.metro_levels[i]],
                "display_name": build.display_names[i],
                "slug": build.slugs[i],
                "rank": pos + 1,
                "score": round(float(score[k]), 1),
                "score_display": str(int(round(float(score[k])))),
                "pool": round(float(est[i])),
                "pool_moe": round(float(moe[i])),
                "cv": round(float(rse[i]), 3),
                "n_unweighted": round(float(n_gate[i])),
                "tier": "measured",
                "balance": _balance_block(build, i, bal, sought_word,
                                          seeker_word),
                "allocation_purity": round(float(build.purity[i]), 3),
                "flags": _row_flags(build, i),
                "stats": stats,
                "cards": _card_stats(build, i),
                "crime": _crime_block(build, i),
                "contributions": [
                    {"pillar": p, "value": round(v, 2)}
                    for p, v in pillar_contrib.items()],
            }
            row["top_stats"] = [s["id"] for s in top_stats(row["stats"])]
            row["summary_line"] = summary_line(row, build.legend)
            out["ranked"].append(row)

    for i in np.where(suppressed)[0]:
        out["suppressed"].append({
            "cbsa": build.metro_levels[i],
            "name": build.titles[build.metro_levels[i]],
            "display_name": build.display_names[i],
            "slug": build.slugs[i],
            "reason": suppression_reason(float(est[i]), float(n_gate[i])),
            "n_unweighted": round(float(n_gate[i])),
            "flags": _row_flags(build, i),
            # balance usually survives the pool's suppression — that is the
            # point of gating it separately (ADR 0004)
            "balance": _balance_block(build, i, bal, sought_word,
                                      seeker_word),
            "cards": _card_stats(build, i),
            "crime": _crime_block(build, i),
        })
    return out
