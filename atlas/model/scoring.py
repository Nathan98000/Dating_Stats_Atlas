"""Scoring, m3.0.0 — six pillars over the cubes plus the static feature
matrix; pure numpy over a loaded Build.

ADR 0009's model change: the match pillar scores CHANCES OF MATCHING
(match_propensity) — the kernel-weighted share of the visitor's own
matched pool, sum_c w(seeker, c) n_c / sum_c n_c over the search-masked
cells, served as an index where 100 is the national average for that same
search (the cube summed over every metro). A RATE, not a count, so it
trades against pool size rather than duplicating it. The weights are the
shipped assortative kernel's (preferences.seeker_weights); the sum runs
over the loader's reduced cubes with the same axis vectors the pool mask
uses (match_index below). Its margin comes from sumw2 with the weights
squared — the delta-method variance of the ratio,
Var(R) = sum_c s2_c (w_c - R)^2 / D^2 — computed and returned, never
rendered (ADR 0004 still). Suppression gates on the UNWEIGHTED n exactly
as before: the kernel can neither rescue nor condemn a cell. Balance is
computed exactly as in m2.x and served on every row (its own gate), but
it is a displayed statistic now, out of the pillar set.

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

m4.1.0 (ADR 0004 amended, Nathan's decision): the second count is the
OTHER sex — the opposite of the sought sex — rather than the seeker's own.
An opposite-sex search's figure is unchanged; a same-sex search shows the
figure an opposite-sex search for the same people shows, where m4.0.0
served it as not applicable. Balance no longer depends on who is
searching, so a search has one balance, whatever the visitor's details.

Normalisation (§7.2), per request, across the RANKED SET FOR THIS QUERY:
  extensive (pool):       winsorize 1/99 -> log10 -> min-max -> [0,100]
  intensive (everything): percentile rank -> [0,100], direction from the
                          registry (via the manifest features_block)
  chances of matching:    the manifest's normalization.match_scoring rule
                          (ADR 0013, match_normalised): N0 the percentile
                          rank above; V1/V2/V3 the value, ln(index / 100)
                          min-max scaled after outlier handling

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
from atlas.model.loader import Build, reduced_key
from atlas.model.preferences import (INCOME_FLOORS, PILLARS, SEX_LEVELS, Request,
                                     axis_vectors, balance_masks_for, pool_mask,
                                     resolve_weights, seeker_weights)
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
    assert feats[0]["id"] == "pool_size" and feats[1]["id"] == "match_propensity"
    return feats


def _match_parts(build: Build, req: Request) -> dict:
    """The search's side of match_index — everything that does not depend
    on who is searching: the reduced cubes for the marital selection and
    income floor, the per-axis vectors the pool mask is built from, and
    the denominators. m4.0.0: computed once per request, shared by every
    "about you" variant (ADR 0018)."""
    seek = req.seeking
    _, a, _, e, _, r = axis_vectors(seek.sex, seek.age_min, seek.age_max,
                                    seek.marital_levels, seek.education_min,
                                    seek.income_min, seek.race_cube_levels)
    a, e, r = a.astype(np.float64), e.astype(np.float64), r.astype(np.float64)
    mi, fi = reduced_key(seek.marital_levels,
                         INCOME_FLOORS[seek.income_min] if seek.income_min else 0)
    tau = SEX_LEVELS.index(seek.sex)
    R = build.reduced_pool[mi, fi, :, tau].astype(np.float64)       # (n, 53, 4, 8)
    S2 = build.reduced_sumw2[mi, fi, :, tau].astype(np.float64)
    er = e[:, None] * r[None, :]                                     # (4, 8)
    return {"R": R, "S2": S2, "a": a, "er": er,
            "den": np.einsum("maer,a,er->m", R, a, er),
            "s2": np.einsum("maer,a,er->m", S2, a, er)}


def _age_sums(parts: dict, age_vec: np.ndarray) -> dict:
    """The age-weighted cube sums for one seeker age curve — the heavy
    part, shared by every variant with the same curve (m4.0.0)."""
    av = age_vec * parts["a"][None, :]                               # (n, 53)
    return {"Q": np.einsum("maer,ma->mer", parts["R"], av),
            "Q1": np.einsum("maer,ma->mer", parts["S2"], av),
            "Q2": np.einsum("maer,ma->mer", parts["S2"], av ** 2)}


def _match_from(parts: dict, sums: dict, W: np.ndarray) -> dict:
    """match_propensity from the shared parts, the seeker's age sums and
    the seeker's education x race factors W (n, 4, 8)."""
    Wm = W * parts["er"][None, :, :]                                 # (n, 4, 8)
    den, s2 = parts["den"], parts["s2"]
    num = np.einsum("mer,mer->m", sums["Q"], Wm)
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(den > 0, num / np.maximum(den, 1e-300), np.nan)
    den_nat, num_nat = float(den.sum()), float(num.sum())
    nat_rate = num_nat / den_nat if den_nat > 0 else np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        index = 100.0 * rate / nat_rate
    # margin: Var(N/D) ~ [Var N - 2R Cov(N,D) + R^2 Var D] / D^2 with the
    # cell sums of squared record weights standing in for the variances:
    # Var N = sum s2 w^2, Cov = sum s2 w, Var D = sum s2 — i.e.
    # sum_c s2_c (w_c - R)^2 / D^2
    s2w2 = np.einsum("mer,mer->m", sums["Q2"], Wm ** 2)
    s2w = np.einsum("mer,mer->m", sums["Q1"], Wm)
    with np.errstate(invalid="ignore", divide="ignore"):
        var = np.where(den > 0, (s2w2 - 2.0 * rate * s2w + rate ** 2 * s2)
                       / np.maximum(den, 1e-300) ** 2, np.nan)
        moe = 1.645 * np.sqrt(np.maximum(var, 0.0)) * 100.0 / nat_rate
    return {"index": index, "moe": moe, "rate": rate, "national_rate": nat_rate,
            "num": num, "den": den}


def match_index(build: Build, req: Request) -> dict:
    """match_propensity for every metro (ADR 0009): the kernel-weighted
    share of the search-masked pool, as an index with 100 = the national
    average for this search, plus its delta-method margin in index
    points. Reads the reduced cubes keyed on the marital selection and
    income floor, applies the SAME per-axis vectors the pool mask is
    built from, and the seeker's per-metro kernel factors.

        num_m = sum_{a,e,r} R_m[a,e,r] * age_vec_m[a] * W_m[e,r]
        den_m = sum_{a,e,r} R_m[a,e,r]            (masked cells only)
        rate_m = num_m / den_m ;  index_m = 100 * rate_m / (sum num / sum den)

    With unit weights num == den == pool_flat @ mask (the weighted path's
    mask-axis test). m4.0.0: the sum over partner ages runs first
    (_age_sums), so every "about you" variant with the same age curve
    shares it; this single-variant path runs the same arithmetic, which
    is what makes a selected variant equal this result exactly."""
    k = build.kernel
    assert k is not None, "build carries no kernel"
    parts = _match_parts(build, req)
    age_vec, W = seeker_weights(k, req.self_sex, req.self_age, req.self_edu,
                                req.self_race, same_sex=(req.seeking.sex == req.self_sex))
    return _match_from(parts, _age_sums(parts, age_vec), W)


def _winsor_log_minmax(x: np.ndarray, lo_hi=(1, 99)) -> np.ndarray:
    lo, hi = np.percentile(x, lo_hi)
    x = np.clip(x, lo, hi)
    x = np.log10(np.maximum(x, 1.0))
    span = x.max() - x.min()
    if span <= 0:
        return np.full_like(x, 50.0)
    return (x - x.min()) / span * 100.0


def _average_ranks(v: np.ndarray) -> np.ndarray:
    """1-based average ranks (ties share the mean of their positions) —
    pandas' rank(method="average"), computed in numpy: every value is a
    whole or half number, exact in floating point, so the two agree bit
    for bit (m4.0.0 dropped pandas from the request path for speed)."""
    sorter = np.argsort(v, kind="mergesort")
    inv = np.empty(sorter.size, dtype=np.intp)
    inv[sorter] = np.arange(sorter.size)
    sv = v[sorter]
    obs = np.r_[True, sv[1:] != sv[:-1]]
    dense = obs.cumsum()[inv]
    count = np.r_[np.nonzero(obs)[0], len(obs)]
    return 0.5 * (count[dense] + count[dense - 1] + 1)


def _pct_rank(x: np.ndarray) -> np.ndarray:
    """Average-rank percentile in [0,100]; NaNs stay NaN."""
    out = np.full(x.shape, np.nan)
    ok = ~np.isnan(x)
    v = x[ok]
    if len(v) == 0:
        return out
    if len(v) == 1:
        out[ok] = 50.0
        return out
    r = _average_ranks(v) - 1.0
    out[ok] = r / (len(v) - 1) * 100.0
    return out


MATCH_SCORING_DEFAULT = "N0"


def match_scoring_spec(build: Build) -> tuple[str, dict]:
    """ADR 0013: the rule the build's manifest names for scoring chances
    of matching and its parameters; a build without the block (m3.4.0 and
    earlier) is N0, the percentile rank."""
    block = build.manifest.get("normalization") or {}
    return str(block.get("match_scoring", MATCH_SCORING_DEFAULT)), block


def match_normalised(match: np.ndarray, rule: str, spec: dict) -> np.ndarray:
    """The match feature's normalised value in [0, 100] (ADR 0013).

    N0: the average-rank percentile every intensive feature takes (the
    same call, so it reproduces the percentile-ranked build bit for bit).
    V1, V2, V3: x = ln(index / 100), so 2x and 1/2x the national average
    sit equally far from it; then one layer of outlier handling — V1
    winsorizes x at the registry's winsor_percentiles of the ranked set,
    V2 clips x to [Q1 - k IQR, Q3 + k IQR] of the ranked set (k =
    match_fence_iqr), V3 clips the INDEX to [match_value_floor,
    match_value_cap] before the log — and min-max scaling to 0-100 across
    the ranked set. A one-city set or identical values score 50; a
    missing value stays missing. Monotone in the index for every rule."""
    if rule == "N0":
        return _pct_rank(match)
    out = np.full(match.shape, np.nan)
    ok = ~np.isnan(match)
    v = match[ok].astype(np.float64)
    if len(v) == 0:
        return out
    if len(v) == 1:
        out[ok] = 50.0
        return out
    if rule == "V3":
        v = np.clip(v, float(spec["match_value_floor"]), float(spec["match_value_cap"]))
    x = np.log(np.maximum(v, 1e-300) / 100.0)
    if rule == "V1":
        lo, hi = np.percentile(x, list(spec["winsor_percentiles"]))
        x = np.clip(x, lo, hi)
    elif rule == "V2":
        q1, q3 = np.percentile(x, [25.0, 75.0])
        k = float(spec["match_fence_iqr"])
        x = np.clip(x, q1 - k * (q3 - q1), q3 + k * (q3 - q1))
    elif rule != "V3":
        raise ValueError(f"unknown match scoring rule {rule!r}")
    span = x.max() - x.min()
    out[ok] = 50.0 if span <= 0 else (x - x.min()) / span * 100.0
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
                     match: np.ndarray, weights: dict[str, float]) -> dict:
    """z, raw values, effective weights, score, feature-level reference and
    contributions for the ranked metros. Shared by rank() and the
    validation suite's replicate resampling. `match` is the
    match_propensity index (100 = national average for the search)."""
    feats = scored_features(build)
    n, F = len(ridx), len(feats)
    z = np.full((n, F), np.nan)
    raw = np.full((n, F), np.nan)
    rule, spec = match_scoring_spec(build)
    for j, f in enumerate(feats):
        if f["id"] == "pool_size":
            raw[:, j] = est
            z[:, j] = _winsor_log_minmax(est)
        elif f["id"] == "match_propensity":
            raw[:, j] = match
            z[:, j] = match_normalised(match, rule, spec)
        else:
            raw[:, j] = build.static[f["id"]][ridx]
            z[:, j] = _pct_rank(raw[:, j] * f["direction"])
    pillar_idx = np.array([PILLARS.index(f["pillar"]) for f in feats])
    u = np.array([f["u"] for f in feats])
    w_pillar = np.array([weights[p] for p in PILLARS])
    w_eff = _feature_weights(z, pillar_idx, u, w_pillar)
    return {"feats": feats, "z": z, "raw": raw, "w_eff": w_eff,
            **score_from(z, w_eff), "pillar_idx": pillar_idx}


def feature_reference(z: np.ndarray, j: int) -> float:
    """Feature-level reference: median of one normalized feature across the
    query's ranked set, defined ONCE (ADR 0003)."""
    col = z[:, j]
    return float(np.nanmedian(col)) if (~np.isnan(col)).any() else 0.0


def score_from(z: np.ndarray, w_eff: np.ndarray, ref: np.ndarray | None = None) -> dict:
    """Score, feature-level reference and contributions from the
    normalised features and the effective weights (m4.0.0: the variant
    path calls this per "about you" variant with only the match column
    changed, so both paths run the same arithmetic; it passes the
    reference with the unchanged features' medians carried over, each the
    same number feature_reference returns)."""
    F = z.shape[1]
    avail = ~np.isnan(z)
    z_filled = np.where(avail, z, 0.0)
    score = (w_eff * z_filled).sum(axis=1)
    if ref is None:
        ref = np.array([feature_reference(z, j) for j in range(F)])
    contrib = w_eff * np.where(avail, z - ref[None, :], 0.0)
    # §7.5 exactness, asserted on every request: the decomposition adds up.
    ref_score = (w_eff * np.where(avail, ref[None, :], 0.0)).sum(axis=1)
    assert np.allclose(contrib.sum(axis=1), score - ref_score, atol=1e-9), (
        "feature-level attribution does not sum to score - reference")
    return {"score": score, "ref": ref, "contrib": contrib}


def score_vector(build: Build, ridx: np.ndarray, est: np.ndarray,
                 match: np.ndarray, weights: dict[str, float]) -> np.ndarray:
    """Score only — the validation suite's replicate-resampling entry."""
    return score_components(build, ridx, est, match, weights)["score"]


def _balance_block(build: Build, i: int, bal: dict) -> dict:
    """The one balance quantity, served per metro with its own gate
    (ADR 0004): value (ratio), per-100 integer, composed display strings.
    Never a bare number without its gate having passed. m4.1.0: the same
    block on every search, same-sex included (the two sides are the sought
    sex and the other sex, never the same people)."""
    if not bal["ok"][i]:
        return {"available": False,
                "note": POLICY_STRINGS["balance_unavailable"]}
    ratio = float(bal["ratio"][i])
    per_100 = int(round(ratio * 100))
    sought_word, seeker_word = bal["sought_word"], bal["seeker_word"]
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


def _band_from_standing(build: Build, fid: str, standing: float) -> dict | None:
    """Five-band position of a PER-REQUEST statistic within the query's
    ranked set (m3.0.0: match_propensity), cut on the registry's standing
    edges with the feature's registry labels and direction-derived
    tones — the same rule the national bands use, applied to the
    standing this request computed."""
    le = build.legend.get(fid, {})
    if not le.get("band_labels") or standing is None or np.isnan(standing):
        return None
    bands = build.manifest["standing_bands"]
    k = bisect_right(bands["edges"], float(standing))
    return {"key": bands["keys"][k], "standing_all": round(float(standing), 1),
            "label": le["band_labels"][k], "tone": le["band_tones"][k]}


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
    """The crime block of metro i — request-independent, made once per
    metro and kept (m4.0.0); _crime_block_made composes it."""
    key = ("crime", i)
    if key not in build.memo:
        build.memo[key] = _crime_block_made(build, i)
    return build.memo[key]


def _crime_block_made(build: Build, i: int) -> dict:
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
                 "caution": strings["crime_caution"],
                 # the compact strings the Phase 2e crime CARDS render:
                 # face stays plain, everything about reporting lives in
                 # the info popover
                 "card_blank": strings["crime_card_blank"],
                 "card_info_label": strings["crime_card_info"],
                 "compare_banner": strings["crime_compare_banner"]}
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
        entry = {
            "id": fid,
            "label": le["display_name"],
            "value": round(vals[fid], 1),
            "display": format_value(vals[fid], le),
            "unit_line": le["unit"],
        }
        band = _band_of(build, fid, i)
        if band:
            entry["band"] = band
        out["stats"].append(entry)
    return out


def _card_stats(build: Build, i: int) -> list[dict]:
    """The v3 city-page cards, straight from the artifact: value, display
    string, unit line, band. Every figure the card shows is composed here.
    No request changes them: made once per metro and kept (m4.0.0)."""
    key = ("cards", i)
    if key not in build.memo:
        build.memo[key] = _card_stats_made(build, i)
    return build.memo[key]


def _card_stats_made(build: Build, i: int) -> list[dict]:
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


def match_display(value: float, build: Build) -> tuple[str, bool]:
    """THE formatting helper for the chances-of-matching figure (m3.1.0,
    Phase 3b A3): the registry's display spec, capped at the registry's
    ceiling with its token appended — "250+" — wherever the figure
    renders (result rows, the city page, the compare table, the stats
    entry). Presentational only: no score, rank, standing or band ever
    reads the display (asserted in test_match_display_cap_is_presentational;
    since ADR 0013 the score reads the served index through the registry's
    normalization block, never this ceiling). Returns (display, capped);
    the compare table shows no difference against a capped figure."""
    le = build.legend["match_propensity"]
    strings = build.manifest["strings"]
    cap = float(strings["match_display_cap"])
    shown = format_value(value, le)
    if float(shown.replace(",", "")) > cap:
        return format_value(cap, le) + strings["match_display_cap_token"], True
    return shown, False


def same_sex_note(build: Build) -> str:
    """m3.2.0 (Phase 3b B3): the one registry sentence a same-sex search
    carries in its information box, saying whose pairing patterns the
    figure is built from — the components fitted on same-sex couples and
    the ones that fall back to opposite-sex couples. m4.0.0 (kernel_v3,
    ADR 0018): the age gaps and the education pairings come from same-sex
    couples and no racial pairing is used; the sentence says so."""
    strings = build.manifest["strings"]
    if build.kernel.same_sex_race_free is not None:
        return strings["match_same_sex_note"]
    ss = build.kernel.same_sex
    return strings["match_same_sex_note"] if ss is not None and ss.components \
        else strings["match_same_sex_note_all_fallback"]


def same_sex_components(build: Build) -> list[str]:
    """The kernel components a same-sex search reads from same-sex couples
    (technical record, match_inputs)."""
    k = build.kernel
    if k.same_sex_race_free is not None:
        return list((k.meta.get("same_sex") or {}).get("components_from_same_sex_couples", []))
    return list(k.same_sex.components) if k.same_sex is not None else []


def _match_block(mt: dict, i: int, build: Build, standing: float | None,
                 same_sex: bool = False) -> dict:
    """Chances of matching for one ranked metro: the index, its display
    string (capped by match_display), the (unrendered) margin, its
    within-query band and, for a same-sex search, the registry sentence
    naming whose patterns it is built from."""
    le = build.legend["match_propensity"]
    v = float(mt["index"][i])
    shown, capped = match_display(v, build) if np.isfinite(v) else (None, False)
    out = {"available": bool(np.isfinite(v)),
           "value": round(v, 2) if np.isfinite(v) else None,
           "display": shown,
           "capped": capped,
           "moe": round(float(mt["moe"][i]), 2) if np.isfinite(mt["moe"][i]) else None,
           "unit_line": le["unit"]}
    if same_sex:
        out["note"] = same_sex_note(build)
    band = _band_from_standing(build, "match_propensity", standing)
    if band:
        out["band"] = band
    return out


def search_frame(build: Build, req: Request) -> dict:
    """Everything about one search that no "about you" detail changes
    (m4.0.0: computed once per request and shared by every variant): the
    pool and its margin, the gate, the tiers, the weights, the sought side
    of the balance, and the words for both sexes."""
    mask_p = pool_mask(req.seeking)
    est = (build.pool_flat @ mask_p).astype(np.float64)
    n_alloc = (build.count_flat @ mask_p).astype(np.float64)
    sumw2 = (build.sumw2_flat @ mask_p).astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        kish = np.where(sumw2 > 0, est ** 2 / sumw2, 0.0)
    n_gate = np.minimum(n_alloc, kish)
    share = est / np.maximum(build.pool_pop, 1.0)

    # the served margin: computed, returned, never rendered (ADR 0004)
    im = build.intervals
    rse = im.served_rse(n_alloc, kish, share, req.seeking.marital_levels,
                        list(req.seeking.race_cube_levels)
                        if req.seeking.race_cube_levels else None)
    with np.errstate(invalid="ignore"):
        moe = np.where(est > 0, 1.645 * rse * est, 0.0)

    universe = build.ranked_set
    suppressed, ranked = tier_masks(universe, est, n_gate)
    weights = resolve_weights(req, build.manifest["model_defaults"])
    reasons: dict[str, int] = {}
    for i in np.where(suppressed)[0]:
        r = suppression_reason(float(est[i]), float(n_gate[i]))
        reasons[r] = reasons.get(r, 0) + 1
    return {"est": est, "n_gate": n_gate, "rse": rse, "moe": moe,
            "universe": universe, "suppressed": suppressed, "ranked": ranked,
            "ridx": np.where(ranked)[0], "weights": weights, "reasons": reasons}


def sex_word(sex: str) -> str:
    return "men" if sex == "male" else "women"


def _balance_sums(build: Build, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return ((build.pool_flat @ mask).astype(np.float64),
            (build.count_flat @ mask).astype(np.float64),
            (build.sumw2_flat @ mask).astype(np.float64))


def balance_parts(build: Build, req: Request, fr: dict) -> dict:
    """Dating pool balance for one search, gated separately per quantity
    (ADR 0004): the single people of the sought sex per 100 single people
    of the other sex, in the search's age range and marital selection.
    m4.1.0 (ADR 0004 amended, Nathan's decision): the other sex is the
    opposite of the sought sex, whoever is searching, so a search has one
    balance and a same-sex search shows it too. m4.0.0 took the second
    count from the seeker's own sex, which on a same-sex search counted
    the same people twice (a ratio of 1 by construction), and served it as
    not applicable — the rule ADR 0004 made when balance was a scored
    pillar (a constant pillar left the top-10 boundary to noise); balance
    has been out of the score since m3.0.0."""
    m_sought, m_other = balance_masks_for(req.seeking)
    b_sought, b_sought_n, b_sought_w2 = _balance_sums(build, m_sought)
    b_other, b_other_n, b_other_w2 = _balance_sums(build, m_other)
    with np.errstate(divide="ignore", invalid="ignore"):
        k_sought = np.where(b_sought_w2 > 0, b_sought ** 2 / b_sought_w2, 0.0)
        k_other = np.where(b_other_w2 > 0, b_other ** 2 / b_other_w2, 0.0)
    bal_ok = ((np.minimum(b_sought_n, k_sought) >= N_GATE_MIN)
              & (np.minimum(b_other_n, k_other) >= N_GATE_MIN)
              & (b_other > 0))
    with np.errstate(divide="ignore", invalid="ignore"):
        bal_ratio = np.where(bal_ok, b_sought / np.maximum(b_other, 1e-9),
                             np.nan)
    other = SEX_LEVELS[1 - SEX_LEVELS.index(req.seeking.sex)]
    # "seeker_word" keeps its served name (on an opposite-sex search the
    # other sex is the seeker's), so an opposite-sex block is unchanged
    bal = {"ratio": bal_ratio, "ok": bal_ok, "standing": None,
           "sought_word": sex_word(req.seeking.sex), "seeker_word": sex_word(other)}
    ridx, ranked = fr["ridx"], fr["ranked"]
    if len(ridx):
        # standing of a metro's balance among the query's ranked set
        ranked_bal = bal_ratio[ridx]
        st = np.full(len(bal_ratio), np.nan)
        st[ridx] = _pct_rank(ranked_bal)
        off = np.where(~ranked & bal_ok)[0]
        if len(off):
            st[off] = _pct_rank_interp(ranked_bal, bal_ratio[off])
        bal["standing"] = st
    return bal


def race_used(build: Build, same_sex: bool) -> bool:
    """Whether a seeker's own race can change the figure: under kernel_v3
    a same-sex search uses no race at all (ADR 0018 §3)."""
    return not (same_sex and build.kernel.same_sex_race_free is not None)


def match_inputs(build: Build, self_edu: str | None, self_race: str | None,
                 national_rate: float, same_sex: bool) -> dict:
    """m3.0.0: what the visitor disclosed and the national reference the
    index is measured against (technical record). m4.0.0: one per
    variant."""
    return {"education": self_edu, "race_ethnicity": self_race,
            "national_rate": (round(float(national_rate), 6)
                              if np.isfinite(national_rate) else None),
            # m3.2.0: a same-sex search says which components come from
            # same-sex couples (the row's note carries the sentence)
            "same_sex": same_sex,
            "same_sex_components": same_sex_components(build) if same_sex else []}


def _stat_entries(build: Build, i: int, k: int, feats: list[dict], z: np.ndarray,
                  raw: np.ndarray, w_eff: np.ndarray, contrib: np.ndarray,
                  standing: np.ndarray) -> list[dict]:
    stats = []
    for j, f in enumerate(feats):
        le = build.legend[f["id"]]
        if np.isnan(z[k, j]):
            stats.append({"id": f["id"], "pillar": f["pillar"],
                          "value": None, "missing": True,
                          "weight": 0.0, "contribution": None})
            continue
        is_match = f["id"] == "match_propensity"
        entry = {
            "id": f["id"], "pillar": f["pillar"],
            # m4.0.0: the compatibility figure's entry carries the figure
            # at its match block's precision — one figure, one value
            "value": round(float(raw[k, j]), 2 if is_match else 4),
            "display": (match_display(float(raw[k, j]), build)[0]
                        if is_match else format_value(float(raw[k, j]), le)),
            "standing": round(float(standing[k, j]), 1),
            "z": round(float(z[k, j]), 2),
            "weight": round(float(w_eff[k, j]), 4),
            "contribution": round(float(contrib[k, j]), 2),
        }
        band = (_band_from_standing(build, f["id"], float(standing[k, j]))
                if is_match else _band_of(build, f["id"], i))
        if band:
            entry["band"] = band
        stats.append(entry)
    return stats


def ranked_row(build: Build, fr: dict, bal: dict, mt: dict, sc: dict,
               standing: np.ndarray, i: int, k: int, pos: int,
               same_sex: bool) -> dict:
    """One ranked row for one variant: metro i, position k in the ranked
    set, rank pos + 1."""
    feats, z, raw, w_eff, score, contrib = (
        sc["feats"], sc["z"], sc["raw"], sc["w_eff"], sc["score"], sc["contrib"])
    jm = MATCH_COLUMN
    stats = _stat_entries(build, i, k, feats, z, raw, w_eff, contrib, standing)
    pillar_contrib: dict[str, float] = {}
    for j, f in enumerate(feats):
        if not np.isnan(z[k, j]):
            pillar_contrib[f["pillar"]] = (
                pillar_contrib.get(f["pillar"], 0.0)
                + float(contrib[k, j]))
    est, moe, rse, n_gate = fr["est"], fr["moe"], fr["rse"], fr["n_gate"]
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
        "balance": _balance_block(build, i, bal),
        "match": _match_block(mt, i, build, float(standing[k, jm]), same_sex),
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
    return row


def suppressed_row(build: Build, fr: dict, bal: dict, i: int) -> dict:
    est, n_gate = fr["est"], fr["n_gate"]
    return {
        "cbsa": build.metro_levels[i],
        "name": build.titles[build.metro_levels[i]],
        "display_name": build.display_names[i],
        "slug": build.slugs[i],
        "reason": suppression_reason(float(est[i]), float(n_gate[i])),
        "n_unweighted": round(float(n_gate[i])),
        "flags": _row_flags(build, i),
        # balance usually survives the pool's suppression — that is the
        # point of gating it separately (ADR 0004)
        "balance": _balance_block(build, i, bal),
        "cards": _card_stats(build, i),
        "crime": _crime_block(build, i),
    }


# the compatibility figure's column in the scored features (asserted by
# scored_features: pool_size first, match_propensity second)
MATCH_COLUMN = 1


def rank(build: Build, req: Request) -> dict:
    """One ranking for one fully specified seeker — the reference every
    "about you" variant of the m4.0.0 response is checked against
    (model.variants.rank_variants serves all of them at once)."""
    fr = search_frame(build, req)
    mt = match_index(build, req)
    same_sex = req.seeking.sex == req.self_sex
    bal = balance_parts(build, req, fr)
    universe, ranked, suppressed, ridx = fr["universe"], fr["ranked"], fr["suppressed"], fr["ridx"]
    out = {"counts": {"universe": int(universe.sum()),
                      "ranked": int(ranked.sum()),
                      "shown_unranked": 0,
                      "suppressed": int(suppressed.sum()),
                      "suppressed_by_reason": fr["reasons"]},
           "weights": fr["weights"],
           "few_metros_notice": bool(ranked.sum() < 40),
           # m4.1.0: balance applies to every search, so balance_applies is
           # gone; "seeker" names the other sex (the seeker's own on an
           # opposite-sex search)
           "balance_words": {"sought": bal["sought_word"], "seeker": bal["seeker_word"]},
           # the race the figure used: none on a kernel_v3 same-sex search
           "match_inputs": match_inputs(build, req.self_edu,
                                        req.self_race if race_used(build, same_sex) else None,
                                        mt["national_rate"], same_sex),
           "ranked": [], "shown_unranked": [], "suppressed": []}
    if len(ridx):
        match_scored = mt["index"][ridx]
        sc = score_components(build, ridx, fr["est"][ridx], match_scored, fr["weights"])
        raw = sc["raw"]
        standing = np.column_stack([_pct_rank(raw[:, j])
                                    for j in range(raw.shape[1])])
        order = np.argsort(-sc["score"], kind="stable")
        for pos, k in enumerate(order):
            out["ranked"].append(ranked_row(build, fr, bal, mt, sc, standing,
                                            int(ridx[k]), int(k), pos, same_sex))
    for i in np.where(suppressed)[0]:
        out["suppressed"].append(suppressed_row(build, fr, bal, int(i)))
    return out
