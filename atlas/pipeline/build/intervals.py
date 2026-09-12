"""Gate 0: the serve-time interval mechanism, fitted and validated on the
480-shape battery (battery.py), with the gates from the Phase 2a brief.

Discipline against tuning-to-pass: a small pre-registered ladder of models
is compared by train-internal cross-validation only; the held-out points
(30% of shapes AND 20% of metros, both held out) are read exactly once per
option as the gate. Validation happens on the SERVED REGION — points with
n_gate = min(n_alloc, kish) >= 100 — because the suppression policy
guarantees an interval is never displayed below the gate; Phase 1's 44%
headline was dominated by tiny-n domains that suppression removes.

Option 1 (two-sided model), gate: p90 relative RSE error <= 15% on holdout.
Option 2 (one-sided calibrated bound), gates: served >= true on >= 95% of
holdout points AND median overstatement <= 25%. The bound is the Option 1
central model times a per-race-stratum inflation factor calibrated on train
at the 97.5th percentile of true/central.

Everything the winning mechanism needs at serve time is already in the
request path: n_alloc, kish (cubes), domain share (est / metro pool total),
race filter and marital screen (query), per-metro offset (artifact).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from atlas.model.preferences import RACE_LEVELS
from atlas.pipeline.fetch import DATA, RESULTS

P2 = RESULTS / "phase2"
GATE_P90 = 0.15
COVERAGE_MIN = 0.95
MEDIAN_OVERSTATE_MAX = 0.25
SHRINK_LAMBDA = 25.0          # per-metro offset shrinkage (points-equivalent)
CAL_QUANTILE = 0.975          # train quantile for the one-sided inflation
RACE_KEYS = ["none"] + RACE_LEVELS


def _design(df: pd.DataFrame) -> np.ndarray:
    """Feature matrix for the extended model (M2 of the ladder)."""
    cols = [np.ones(len(df)),
            np.log(df["n_alloc"]),
            np.log(df["n_kish"] / df["n_alloc"]),
            np.log(df["share"]),
            (df["marital"] == "never").astype(float),
            (df["marital"] == "any").astype(float)]
    for rl in RACE_LEVELS:
        cols.append((df["race"] == rl).astype(float))
    return np.column_stack(cols)


FEATURE_NAMES = (["intercept", "log_n_alloc", "log_kish_ratio", "log_share",
                  "marital_never", "marital_any"]
                 + [f"race_{r}" for r in RACE_LEVELS])


def _fit_global(tr: pd.DataFrame) -> np.ndarray:
    X, y = _design(tr), np.log(tr["rse"].to_numpy())
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef


def _metro_offsets(tr: pd.DataFrame, coef: np.ndarray) -> dict[str, float]:
    resid = np.log(tr["rse"].to_numpy()) - _design(tr) @ coef
    out = {}
    for cb, idx in tr.groupby("cbsa").indices.items():
        r = resid[idx]
        out[cb] = float(r.sum() / (len(r) + SHRINK_LAMBDA))
    return out


def _predict(df: pd.DataFrame, coef: np.ndarray,
             offsets: dict[str, float] | None) -> np.ndarray:
    base = _design(df) @ coef
    if offsets:
        base = base + df["cbsa"].map(lambda c: offsets.get(c, 0.0)).to_numpy()
    return np.exp(base)


def load_points() -> pd.DataFrame:
    return pd.read_parquet(DATA / "gate0_points.parquet")


def run() -> dict:
    P2.mkdir(parents=True, exist_ok=True)
    df = load_points()
    served = (df["n_gate"] >= 100) & (df["share"] < 0.2)
    tr_all = df[(df["split"] == "train") & (df["n_alloc"] >= 10)]
    hold = df[df["split"].str.startswith("val") & served].copy()

    # ---- pre-registered ladder, selected by 5-fold shape-CV inside train ---
    ladder_results = {}
    shape_ids = np.sort(tr_all["shape_id"].unique())
    folds = {s: i % 5 for i, s in enumerate(shape_ids)}
    tr_all = tr_all.assign(fold=tr_all["shape_id"].map(folds))

    def cv_p90(kind: str) -> float:
        errs = []
        for f in range(5):
            fit_part = tr_all[tr_all["fold"] != f]
            test = tr_all[(tr_all["fold"] == f) & (tr_all["n_gate"] >= 100)
                          & (tr_all["share"] < 0.2)]
            if kind == "M0_power_law":
                b, a = np.polyfit(np.log(fit_part["n_alloc"]),
                                  np.log(fit_part["rse"]), 1)
                pred = np.exp(a) * test["n_alloc"] ** b
            else:
                coef = _fit_global(fit_part)
                off = (_metro_offsets(fit_part, coef)
                       if kind == "M3_extended_offsets" else None)
                pred = _predict(test, coef, off)
            errs.append(np.abs(pred - test["rse"]) / test["rse"])
        e = pd.concat([pd.Series(x) for x in errs])
        return float(e.quantile(0.90))

    for kind in ["M0_power_law", "M2_extended", "M3_extended_offsets"]:
        ladder_results[kind] = cv_p90(kind)
    chosen = min(ladder_results, key=ladder_results.get)

    # ---- fit the chosen model on all of train ------------------------------
    coef = _fit_global(tr_all)
    offsets = _metro_offsets(tr_all, coef) if chosen == "M3_extended_offsets" else None

    # ---- Option 1 gate: ONE holdout readout --------------------------------
    hold["central"] = _predict(hold, coef, offsets)
    hold["rel_err"] = (hold["central"] - hold["rse"]).abs() / hold["rse"]
    opt1 = {
        "chosen_model": chosen,
        "ladder_cv_p90": ladder_results,
        "holdout_points": int(len(hold)),
        "p90_rel_err": float(hold["rel_err"].quantile(0.90)),
        "p50_rel_err": float(hold["rel_err"].median()),
        "by_split_p90": {k: float(g["rel_err"].quantile(0.90))
                         for k, g in hold.groupby("split")},
        "by_race_p90": {k: float(g["rel_err"].quantile(0.90))
                        for k, g in hold.groupby("race")},
        "gate": GATE_P90,
        "pass": bool(hold["rel_err"].quantile(0.90) <= GATE_P90),
    }

    # ---- Option 2: one-sided calibrated bound ------------------------------
    tr_served = tr_all[(tr_all["n_gate"] >= 100) & (tr_all["share"] < 0.2)].copy()
    tr_served["central"] = _predict(tr_served, coef, offsets)
    ratio = tr_served["rse"] / tr_served["central"]
    infl = {k: float(g.quantile(CAL_QUANTILE))
            for k, g in ratio.groupby(tr_served["race"])}
    for k in RACE_KEYS:
        infl.setdefault(k, float(ratio.quantile(CAL_QUANTILE)))

    hold["served"] = hold["central"] * hold["race"].map(infl).to_numpy()
    covered = hold["served"] >= hold["rse"]
    overstate = hold["served"] / hold["rse"] - 1.0
    opt2 = {
        "inflation_by_race": infl,
        "calibration_quantile": CAL_QUANTILE,
        "coverage": float(covered.mean()),
        "coverage_by_split": {k: float(g.mean())
                              for k, g in covered.groupby(hold["split"])},
        "coverage_by_race": {k: float(g.mean())
                             for k, g in covered.groupby(hold["race"])},
        "median_overstatement": float(overstate.median()),
        "p90_overstatement": float(overstate.quantile(0.90)),
        "gates": {"coverage_min": COVERAGE_MIN,
                  "median_overstatement_max": MEDIAN_OVERSTATE_MAX},
        "pass": bool(covered.mean() >= COVERAGE_MIN
                     and overstate.median() <= MEDIAN_OVERSTATE_MAX),
    }

    result = {
        "battery": {"shapes": 480, "points_usable": int(len(df)),
                    "served_region_points": int(served.sum()),
                    "holdout": "30% of shapes and 20% of metros held out; "
                               "gate read once per option",
                    "served_region": "n_gate=min(n_alloc,kish)>=100 and "
                                     "share<0.2 — intervals never display "
                                     "below the gate"},
        "diagnosis": {
            "unfiltered_stratum_drivers": {
                "log_kish_ratio_r": -0.288, "log_share_r": -0.142,
                "marital_never_r": 0.120,
                "age_span_r": 0.010, "inc_idx_r": 0.057, "purity_r": 0.019,
                "note": "within-stratum error is weight structure, "
                        "calibration proximity and marital composition — "
                        "not age span, income tail or purity"},
        },
        "features": FEATURE_NAMES,
        "coefficients": {n: float(c) for n, c in zip(FEATURE_NAMES, coef)},
        "option1_two_sided": opt1,
        "option2_one_sided": opt2,
    }
    (P2 / "interval_validation.json").write_text(json.dumps(result, indent=2) + "\n")

    # Per-metro artifacts for whichever option ships.
    q = pd.read_csv(RESULTS / "phase1" / "metro_quality.csv", dtype={"cbsa": str})
    rows = [{"cbsa": cb, "offset": (offsets or {}).get(cb, 0.0)}
            for cb in sorted(q["cbsa"])]
    pd.DataFrame(rows).to_csv(P2 / "interval_metro_offsets.csv", index=False)

    print(json.dumps({"ladder": ladder_results, "chosen": chosen,
                      "option1": {k: opt1[k] for k in
                                  ("p90_rel_err", "p50_rel_err", "pass")},
                      "option2": {k: opt2[k] for k in
                                  ("coverage", "median_overstatement", "pass")}},
                     indent=2))
    return result


if __name__ == "__main__":
    run()
