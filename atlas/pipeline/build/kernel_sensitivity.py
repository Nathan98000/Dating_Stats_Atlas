"""Per-level sensitivity of chances of matching (Phase 3 item 10), and
the disclosure gap.

The three inputs are modelled on the same footing; this script gives
each the same measured report, in one format, written to
results/phase3/sensitivity.csv (+ .json):

  for every level of every component — five seeker age bands, four
  education levels, eight race groups — the median absolute change in
  match_propensity across the ranked set for a seeker at that level when
  the kernel is REFITTED WITHOUT that component (IPF with the term held
  at zero, the other two absorbing what they can), and the change in
  which cities come out highest (top-5 by the index before/after, top-10
  overlap of the full score under default weights, Kendall tau of the
  index across the ranked set).

Reference search per seeker: the site's default window relative to the
seeker's age (a woman of 30 seeking 28-40 is the stated default, so
[age-2, age+10] clipped to 18-70), opposite sex, never or previously
married, no other filter — the UNFILTERED view, where each component
does most of its work (a filter to a single level of an attribute makes
that component nearly a constant multiplier). Both sexes are run and
reported; the age bands average over every seeker age in the band.

Disclosure gap: for a grid of seekers, the same city's index with each
education level / race group disclosed against the undisclosed figure —
how far two visitors differing only in what they disclosed can land apart.

    python -m atlas.pipeline.build.kernel_sensitivity <build_dir>
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from atlas import model as engine
from atlas.model.preferences import EDU_LEVELS, RACE_LEVELS, SEX_LEVELS, SPEC_RACE, Kernel
from atlas.model.scoring import match_index
from atlas.pipeline.build import kernel as K
from atlas.pipeline.fetch import DATA, RESULTS

P3 = RESULTS / "phase3"
AGE_BANDS = {"18-24": range(18, 25), "25-34": range(25, 35), "35-44": range(35, 45),
             "45-54": range(45, 55), "55-70": range(55, 71)}
CUBE_TO_SPEC = {v: k for k, v in SPEC_RACE.items()}


def default_window(age: int) -> list[int]:
    return [max(18, age - 2), min(70, age + 10)]


def body_for(sex: str, age: int, edu: str | None = None, race: str | None = None) -> dict:
    self_ = {"sex": sex, "age": age}
    if edu:
        self_["education"] = edu
    if race:
        self_["race_ethnicity"] = CUBE_TO_SPEC[race]
    return {"self": self_,
            "seeking": {"age": default_window(age),
                        "marital": ["never_married", "previously_married"]}}


def kernel_without(build, comp: str, C: np.ndarray, A: np.ndarray, meta: dict) -> Kernel:
    """Refit the national kernel without `comp`, gauge it, and keep the
    shipped dials for the other components (the dial of the dropped
    component is moot: its term is zero)."""
    fit = K.fit_national(C, A, skip=(comp,), bandwidth=tuple(meta["bandwidth_years"])
                         if comp != "age" else None)
    fg = K.gauge(fit["f"], A, fit["N_s"])
    fg[comp] = np.zeros(K.f_shape(comp))
    k = build.kernel
    dials = k.dials.copy()
    dials[:, K.COMPONENTS.index(comp)] = 1.0
    n = len(build.metro_levels)
    log_norm = np.stack([K.log_norm_for(fg, A, dials[i]) for i in range(n)])
    log_norm = log_norm.reshape(n, K.N_SEX, K.N_AGE, K.N_EDU, K.N_RACE)
    return replace(k, f_age=fg["age"], f_edu=fg["edu"], f_race=fg["race"], dials=dials,
                   log_norm=log_norm.astype(np.float32))


def index_for(build, body: dict) -> np.ndarray:
    return match_index(build, engine.parse_request(body))["index"]


def score_order(build, body: dict) -> list[str]:
    res = engine.rank(build, engine.parse_request(body))
    return [r["cbsa"] for r in res["ranked"]]


def main(build_dir: str) -> None:
    t0 = time.time()
    build = engine.load_build(build_dir)
    ranked = build.ranked_set
    meta = json.loads((Path(build_dir) / "kernel.json").read_text())
    sample = meta["fitting_sample"]
    nat = pd.read_parquet(DATA / f"couple_table_national_{sample}.parquet")
    C = K.table_to_dense(nat)
    A = np.load(P3 / "_avail_national.npy")
    alt = {comp: replace(build, kernel=kernel_without(build, comp, C, A, meta))
           for comp in K.COMPONENTS}
    names = np.array(build.display_names)
    rows = []

    def record(comp, level, sex, bodies):
        full = np.array([index_for(build, b) for b in bodies])
        without = np.array([index_for(alt[comp], b) for b in bodies])
        d = (full - without)[:, ranked]
        f_mean, w_mean = full[:, ranked].mean(axis=0), without[:, ranked].mean(axis=0)
        ok = np.isfinite(f_mean) & np.isfinite(w_mean)
        tau = kendalltau(f_mean[ok], w_mean[ok]).statistic
        top_full = names[ranked][np.argsort(-np.where(ok, f_mean, -np.inf))[:5]].tolist()
        top_without = names[ranked][np.argsort(-np.where(ok, w_mean, -np.inf))[:5]].tolist()
        # full-score top-10 under default weights, for the band's middle seeker
        mid = bodies[len(bodies) // 2]
        top10_full = score_order(build, mid)[:10]
        top10_without = score_order(alt[comp], mid)[:10]
        rows.append({"component": comp, "level": level, "seeker_sex": sex,
                     "seekers": len(bodies),
                     "median_abs_change_index_pts": round(float(np.nanmedian(np.abs(d))), 2),
                     "p90_abs_change_index_pts": round(float(np.nanpercentile(np.abs(d), 90)), 2),
                     "max_abs_change_index_pts": round(float(np.nanmax(np.abs(d))), 2),
                     "index_spread_full_p10_p90": round(float(np.nanpercentile(f_mean, 90)
                                                              - np.nanpercentile(f_mean, 10)), 2),
                     "index_spread_without_p10_p90": round(float(np.nanpercentile(w_mean, 90)
                                                                 - np.nanpercentile(w_mean, 10)), 2),
                     "kendall_tau_index": round(float(tau), 3),
                     "top5_by_index_full": " | ".join(top_full),
                     "top5_by_index_without": " | ".join(top_without),
                     "top1_changes": top_full[0] != top_without[0],
                     "top10_score_overlap": len(set(top10_full) & set(top10_without))})

    for sex in SEX_LEVELS:
        for band, ages in AGE_BANDS.items():
            record("age", band, sex, [body_for(sex, a) for a in ages])
        for e in EDU_LEVELS:
            record("edu", e, sex, [body_for(sex, a, edu=e) for a in (25, 30, 35, 40, 50)])
        for r in RACE_LEVELS:
            record("race", r, sex, [body_for(sex, a, race=r) for a in (25, 30, 35, 40, 50)])
    df = pd.DataFrame(rows)
    df.to_csv(P3 / "sensitivity.csv", index=False)

    # disclosure gap: same city, same sex and age, different disclosure
    gaps = []
    for sex in SEX_LEVELS:
        for age in (25, 30, 35, 40, 50):
            base = index_for(build, body_for(sex, age))[ranked]
            for e in EDU_LEVELS:
                v = index_for(build, body_for(sex, age, edu=e))[ranked]
                gaps.append({"sex": sex, "age": age, "disclosed": "edu", "level": e,
                             "median_abs_gap": float(np.nanmedian(np.abs(v - base))),
                             "max_abs_gap": float(np.nanmax(np.abs(v - base)))})
            for r in RACE_LEVELS:
                v = index_for(build, body_for(sex, age, race=r))[ranked]
                gaps.append({"sex": sex, "age": age, "disclosed": "race", "level": r,
                             "median_abs_gap": float(np.nanmedian(np.abs(v - base))),
                             "max_abs_gap": float(np.nanmax(np.abs(v - base)))})
            for e in EDU_LEVELS:
                for r in RACE_LEVELS:
                    v = index_for(build, body_for(sex, age, edu=e, race=r))[ranked]
                    gaps.append({"sex": sex, "age": age, "disclosed": "both",
                                 "level": f"{e}+{r}",
                                 "median_abs_gap": float(np.nanmedian(np.abs(v - base))),
                                 "max_abs_gap": float(np.nanmax(np.abs(v - base)))})
    gdf = pd.DataFrame(gaps)
    gdf.to_csv(P3 / "disclosure_gap.csv", index=False)
    summary = {
        "reference_search": "opposite sex, ages [age-2, age+10] clipped to 18-70, never or "
                            "previously married, no other filter (the site's default window)",
        "kernel_without": "the national kernel refitted by IPF with that component held at "
                          "zero (the other two absorb what they can), the shipped dials kept "
                          "for the remaining components",
        "by_component": {comp: {
            "median_of_level_medians_pts": round(float(df[df.component == comp]
                                                       ["median_abs_change_index_pts"].median()), 2),
            "largest_level_median_pts": round(float(df[df.component == comp]
                                                    ["median_abs_change_index_pts"].max()), 2),
            "largest_level": df[df.component == comp].sort_values(
                "median_abs_change_index_pts").iloc[-1][["level", "seeker_sex"]].tolist(),
            "levels_where_top1_changes": int(df[df.component == comp]["top1_changes"].sum()),
            "levels": int((df.component == comp).sum()),
            "min_kendall_tau": round(float(df[df.component == comp]["kendall_tau_index"].min()), 3)}
            for comp in K.COMPONENTS},
        "disclosure_gap": {
            d: {"median_of_median_gaps_pts": round(float(gdf[gdf.disclosed == d]["median_abs_gap"].median()), 2),
                "largest_median_gap_pts": round(float(gdf[gdf.disclosed == d]["median_abs_gap"].max()), 2),
                "largest_max_gap_pts": round(float(gdf[gdf.disclosed == d]["max_abs_gap"].max()), 2),
                "largest_median_gap_level": gdf[gdf.disclosed == d].sort_values("median_abs_gap")
                .iloc[-1][["sex", "age", "level"]].tolist()}
            for d in ("edu", "race", "both")},
        "seconds": round(time.time() - t0, 1)}
    def _js(o):
        return o.item() if hasattr(o, "item") else str(o)
    (P3 / "sensitivity.json").write_text(json.dumps(summary, indent=1, default=_js) + "\n")
    print(json.dumps(summary, indent=1, default=_js))


if __name__ == "__main__":
    main(sys.argv[1])
