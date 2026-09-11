"""Correction 3: fit the serving-time variance model instead of assuming
RSE ~ n^-0.5.

Per metro:   log(RSE) = alpha + beta * log(n_alloc),  beta free,
fit by least squares over a seeded battery of realistic query shapes
(sex x age range x education floor x income floor x marital screen x race),
evaluated with the full 81-replicate machinery in one GROUP BY cbsa scan per
batch of shapes. Universe-scale points (pool >= 20% of the metro's 18-70
noninstitutional population) are excluded from the fit — calibrated weights
collapse variance near control totals and no product query asks for the
universe.

Validation: a held-out set of shapes, scored against true replicate MOEs;
the 90th-percentile relative error is the number that ships in the build
manifest. Above 15% the build stops.

The same battery points feed the suppression-tier study (work item E).
"""
from __future__ import annotations

import json
import random

import numpy as np
import pandas as pd

from fetch import DATA, RESULTS
from pool import open_pool

P1 = RESULTS / "phase1"
POINTS_PARQUET = DATA / "variance_points.parquet"
N_TRAIN_SHAPES = 120
N_VAL_SHAPES = 40
BATCH = 4
MIN_PTS_PER_METRO = 30
UNIVERSE_FRACTION = 0.20
SEED = 42

EDU_FLOORS = [("any", "TRUE", 0.35),
              ("some_college+", "edu4 IN ('some_college','bachelors','graduate')", 0.15),
              ("ba+", "edu4 IN ('bachelors','graduate')", 0.30),
              ("graduate", "edu4 = 'graduate'", 0.20)]
INC_FLOORS = [(None, 0.40), (25_000, 0.10), (50_000, 0.15), (75_000, 0.15),
              (100_000, 0.12), (150_000, 0.08)]
MARITALS = [("not_married", "msp IN (3,4,5,6)", 0.50),
            ("never", "msp = 6", 0.30), ("any", "TRUE", 0.20)]
RACES = [(None, 0.55), ("hispanic", 0.08), ("nh_white", 0.08), ("nh_black", 0.08),
         ("nh_asian", 0.08), ("nh_aian", 0.03), ("nh_nhpi", 0.02),
         ("nh_twoplus", 0.05), ("nh_other", 0.03)]


def _choice(rng: random.Random, options):
    r = rng.random()
    acc = 0.0
    for *vals, w in options:
        acc += w
        if r <= acc:
            return vals if len(vals) > 1 else vals[0]
    return options[-1][:-1] if len(options[-1]) > 2 else options[-1][0]


def sample_shapes(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    shapes = []
    for i in range(n):
        sex = rng.choice([1, 2])
        lo = rng.randint(18, 55)
        hi = min(70, lo + rng.randint(4, 20))
        edu_name, edu_sql = _choice(rng, EDU_FLOORS)
        inc = _choice(rng, INC_FLOORS)
        mar_name, mar_sql = _choice(rng, MARITALS)
        race = _choice(rng, RACES)
        where = f"sex = {sex} AND agep BETWEEN {lo} AND {hi} AND {edu_sql} AND {mar_sql}"
        if inc:
            where += f" AND inc_adj >= {inc}"
        if race:
            where += f" AND race8 = '{race}'"
        shapes.append({"shape_id": i, "sex": sex, "age_lo": lo, "age_hi": hi,
                       "edu": edu_name, "inc": inc, "marital": mar_name,
                       "race": race, "where": where})
    return shapes


def eval_shapes(con, shapes: list[dict], split: str) -> pd.DataFrame:
    """Full 81-replicate evaluation of shapes across every metro, batched into
    one GROUP BY cbsa scan per BATCH shapes."""
    frames = []
    for i in range(0, len(shapes), BATCH):
        batch = shapes[i:i + BATCH]
        parts = []
        for s in batch:
            f = f"CASE WHEN ({s['where']}) THEN 1 ELSE 0 END"
            parts.append(f"sum(a_eff * {f})")
            parts.append(f"sum(pwgtp * pwgtp * a_eff * a_eff * {f})")
            parts.append(f"sum(pwgtp * a_eff * {f})")
            for r in range(1, 81):
                parts.append(f"sum(pwgtp{r} * a_eff * {f})")
        rows = con.execute(
            f"SELECT cbsa, {', '.join(parts)} FROM contrib WHERE gq <> 2 GROUP BY 1"
        ).fetchall()
        per = 83
        for row in rows:
            cbsa, vals = row[0], row[1:]
            for j, s in enumerate(batch):
                v = vals[j * per:(j + 1) * per]
                n_alloc, sw2, est = float(v[0] or 0), float(v[1] or 0), float(v[2] or 0)
                reps = [float(x or 0) for x in v[3:83]]
                var = 0.05 * sum((e - est) ** 2 for e in reps)
                se = var ** 0.5
                frames.append({"split": split, "shape_id": s["shape_id"], "cbsa": cbsa,
                               "n_alloc": n_alloc, "est": est, "se": se,
                               "rse": se / est if est > 0 else None,
                               "n_kish": est * est / sw2 if sw2 > 0 else 0.0})
        print(f"  battery {split}: {min(i + BATCH, len(shapes))}/{len(shapes)} shapes",
              flush=True)
    return pd.DataFrame(frames)


def fit_and_validate() -> None:
    P1.mkdir(parents=True, exist_ok=True)
    con = open_pool()
    quality = pd.read_csv(P1 / "metro_quality.csv", dtype={"cbsa": str})
    pool_pop = quality.set_index("cbsa")["pop_pool_18_70"]

    train = sample_shapes(N_TRAIN_SHAPES, SEED)
    val = sample_shapes(N_VAL_SHAPES, SEED + 1)
    pts = pd.concat([eval_shapes(con, train, "train"),
                     eval_shapes(con, val, "val")], ignore_index=True)
    pts.to_parquet(POINTS_PARQUET, index=False)

    usable = pts[(pts["est"] > 0) & (pts["n_alloc"] >= 10) & pts["rse"].notna()
                 & (pts["rse"] > 0)].copy()
    usable["universe_scale"] = usable.apply(
        lambda r: r["est"] >= UNIVERSE_FRACTION * pool_pop.get(r["cbsa"], np.inf), axis=1)
    fitpts = usable[(usable["split"] == "train") & ~usable["universe_scale"]]

    # global fallback fit
    gx, gy = np.log(fitpts["n_alloc"]), np.log(fitpts["rse"])
    g_beta, g_alpha = np.polyfit(gx, gy, 1)

    rows = []
    for cbsa, grp in fitpts.groupby("cbsa"):
        if len(grp) >= MIN_PTS_PER_METRO:
            beta, alpha = np.polyfit(np.log(grp["n_alloc"]), np.log(grp["rse"]), 1)
            fallback = False
        else:
            alpha, beta, fallback = g_alpha, g_beta, True
        rows.append({"cbsa": cbsa, "alpha": float(alpha), "beta": float(beta),
                     "n_fit_points": len(grp), "fallback": fallback})
    fit = pd.DataFrame(rows)
    # metros never seen in usable train points still need coefficients
    missing = set(quality["cbsa"]) - set(fit["cbsa"])
    for cb in sorted(missing):
        fit.loc[len(fit)] = {"cbsa": cb, "alpha": float(g_alpha), "beta": float(g_beta),
                             "n_fit_points": 0, "fallback": True}

    # validation on held-out shapes (same universe-scale exclusion)
    v = usable[(usable["split"] == "val") & ~usable["universe_scale"]].merge(
        fit, on="cbsa")
    v["rse_fit"] = np.exp(v["alpha"]) * v["n_alloc"] ** v["beta"]
    v["rel_err"] = (v["rse_fit"] - v["rse"]).abs() / v["rse"]
    p90 = float(v["rel_err"].quantile(0.90))
    per_metro_p90 = v.groupby("cbsa")["rel_err"].quantile(0.90)
    fit = fit.merge(per_metro_p90.rename("val_p90_rel_err"), on="cbsa", how="left")
    fit.to_csv(P1 / "variance_fit.csv", index=False)

    result = {
        "model": "log(RSE) = alpha + beta*log(n_alloc), per metro",
        "train_shapes": N_TRAIN_SHAPES, "val_shapes": N_VAL_SHAPES,
        "train_points_used": int(len(fitpts)), "val_points_used": int(len(v)),
        "universe_scale_excluded_train": int(usable[(usable['split'] == 'train')
                                                    & usable['universe_scale']].shape[0]),
        "global_alpha": float(g_alpha), "global_beta": float(g_beta),
        "beta_median": float(fit[~fit["fallback"]]["beta"].median()),
        "beta_p10_p90": [float(fit[~fit['fallback']]['beta'].quantile(q))
                         for q in (0.1, 0.9)],
        "fallback_metros": int(fit["fallback"].sum()),
        "validation_p90_rel_err": p90,
        "validation_p50_rel_err": float(v["rel_err"].median()),
        "pass_15pct": bool(p90 <= 0.15),
    }
    (P1 / "variance_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    assert result["pass_15pct"], (
        f"variance model p90 relative error {p90:.1%} exceeds 15% — stopping, not shipping")

    # ---- suppression tier study (work item E) ------------------------------
    ranked_set = set(quality[quality["ranked_set"]]["cbsa"])
    study = usable[usable["cbsa"].isin(ranked_set)].copy()
    study["n_gate"] = study[["n_alloc", "n_kish"]].min(axis=1)
    study["cv_pct"] = study["rse"] * 100
    conds = {
        "suppressed_by_n": (study["n_gate"] < 100),
        "suppressed_by_cv_only": (study["n_gate"] >= 100) & (study["cv_pct"] > 30),
        "middle_tier": (study["n_gate"] >= 100) & (study["cv_pct"] > 20)
                       & (study["cv_pct"] <= 30),
        "ranked": (study["n_gate"] >= 100) & (study["cv_pct"] <= 20),
    }
    tiers = {k: int(m.sum()) for k, m in conds.items()}
    # where does the middle tier live?
    mid = study[conds["middle_tier"]]
    tier_study = {
        "points": int(len(study)), "ranked_set_metros": len(ranked_set),
        "tiers": tiers,
        "middle_tier_share": tiers["middle_tier"] / len(study),
        "middle_tier_n_gate_range": [float(mid["n_gate"].min()),
                                     float(mid["n_gate"].max())] if len(mid) else None,
        "kish_binding_share": float((study["n_kish"] < study["n_alloc"]).mean()),
        "n_gate_100_cv_at_gate": float(
            study[(study["n_gate"] >= 90) & (study["n_gate"] <= 110)]["cv_pct"].median())
        if len(study[(study["n_gate"] >= 90) & (study["n_gate"] <= 110)]) else None,
    }
    (P1 / "tier_study.json").write_text(json.dumps(tier_study, indent=2) + "\n")
    print(json.dumps(tier_study, indent=2))


if __name__ == "__main__":
    fit_and_validate()
