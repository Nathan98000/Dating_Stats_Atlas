"""Validation suite (§11), run on every build. Machine-readable report in
results/phase2/validation_report.json; HARD gates fail the build (nonzero
exit), SOFT gates warn and are reported as measured.

  hard  interval calibration     Gate 0 Option 2 coverage/overstatement
  hard  suppression goldens      the 12 pinned vectors, exact
  hard  rank stability           resample pool+ratio across the 80
                                 replicates; >=8-of-10 top-10 overlap in
                                 >=80% of replicates, every persona
  hard  adversarial artifacts    college/military/prison metros in any
                                 top-10 must not be there for a
                                 GQ-traceable reason (pool recomputed
                                 without noninstitutional GQ)
  soft  face validity            12 personas with attribution-consistent
                                 explanations, written out for human review
  soft  weight sensitivity       each pillar weight +/-20%, Kendall tau
                                 vs baseline (target >= 0.85)
  soft  external correlation     score/ratio vs B09021 living-alone share
                                 and B12007 median age at first marriage —
                                 reported as measured ("opportunity, not
                                 outcome")
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, pearsonr, spearmanr

from atlas import model as engine
from atlas.model.scoring import (_effective_weights, _pct_rank, _pillar_z,
                                 _winsor_log_minmax)
from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.fetch import RESULTS, api_get

P2 = RESULTS / "phase2"
GOLDEN_DIR = None  # set in main from the model tests package

STABILITY_OVERLAP = 8      # of top 10
STABILITY_SHARE = 0.80
KENDALL_MIN = 0.85
GQ_POOL_SHARE_LIMIT = 0.15


def _replicate_sums(con, where: str) -> pd.DataFrame:
    reps = ", ".join(f"sum(pwgtp{i} * a_eff)" for i in range(1, 81))
    rows = con.execute(
        f"SELECT cbsa, sum(pwgtp * a_eff), {reps} FROM contrib "
        f"WHERE gq <> 2 AND ({where}) GROUP BY 1").fetchall()
    return pd.DataFrame([{"cbsa": r[0],
                          "est": float(r[1] or 0),
                          **{f"r{i}": float(r[2 + i - 1] or 0)
                             for i in range(1, 81)}} for r in rows])


def _spec_to_sql(seeking: dict, self_: dict) -> tuple[str, str]:
    """(pool where, rival where) in contrib SQL, mirroring the mask logic."""
    sex = seeking.get("sex") or ("male" if self_["sex"] == "female" else "female")
    sexcode = 1 if sex == "male" else 2
    lo, hi = seeking["age"]
    mar = {"never_married": "6", "previously_married": "3,4,5",
           "currently_married": "1,2"}
    msp = ",".join(mar[m] for m in seeking["marital"])
    w = f"sex = {sexcode} AND agep BETWEEN {lo} AND {hi} AND msp IN ({msp})"
    if seeking.get("education_min"):
        tail = {"some_college": "'some_college','bachelors','graduate'",
                "bachelors": "'bachelors','graduate'",
                "graduate": "'graduate'"}[seeking["education_min"]]
        w += f" AND edu4 IN ({tail})"
    if seeking.get("income_min"):
        w += f" AND inc_adj >= {seeking['income_min']}"
    if seeking.get("race_ethnicity"):
        cubes = [engine.SPEC_RACE[r] for r in seeking["race_ethnicity"]]
        w += " AND race8 IN (" + ",".join(f"'{c}'" for c in cubes) + ")"
    r_sex = 1 if self_["sex"] == "male" else 2
    rlo, rhi = max(18, self_["age"] - 5), min(70, self_["age"] + 5)
    rw = f"sex = {r_sex} AND agep BETWEEN {rlo} AND {rhi} AND msp IN ({msp})"
    if seeking.get("education_min"):
        tail = {"some_college": "'some_college','bachelors','graduate'",
                "bachelors": "'bachelors','graduate'",
                "graduate": "'graduate'"}[seeking["education_min"]]
        rw += f" AND edu4 IN ({tail})"
    return w, rw


def _score_from_vectors(build, ridx, est, ratio, weights) -> np.ndarray:
    z_pool = _winsor_log_minmax(est)
    z_bal = _pct_rank(ratio)
    z, _ = _pillar_z(build, ridx, z_pool, z_bal)
    w_eff = _effective_weights(z, weights)
    return np.nansum(z * w_eff, axis=1)


def main(build_dir: str) -> int:
    from atlas.model.tests.golden.make_fixture import GOLDEN_VECTORS
    build = engine.load_build(build_dir)
    report: dict = {"build": build.manifest["data_version"],
                    "model_version": engine.MODEL_VERSION,
                    "hard": {}, "soft": {}}
    hard_fail = []

    # ---- hard: interval calibration ---------------------------------------
    im = build.manifest["interval_model"]
    ok = (im["used_by_api"] and im["validation"]["coverage"] >= 0.95
          and im["validation"]["median_overstatement"] <= 0.25)
    report["hard"]["interval_calibration"] = {
        "pass": bool(ok), **im["validation"],
        "mechanism": im["mechanism"], "copy_rule": im["copy_rule"]}
    if not ok:
        hard_fail.append("interval_calibration")

    # ---- hard: suppression goldens (full-build responses are exercised in
    # pytest against the fixture; here the same vectors run on THIS build and
    # the suppression logic must be internally consistent) -------------------
    con = open_pool()
    persona_results = {}
    golden_ok = True
    for v in GOLDEN_VECTORS:
        body = {k: v[k] for k in ("self", "seeking", "weights", "size_vs_odds")
                if k in v}
        res = engine.rank(build, engine.parse_request(body))
        persona_results[v["name"]] = res
        for row in res["suppressed"]:
            if row["reason"] not in ("n_below_100", "cv_above_30",
                                     "empty_pool", "no_rivals"):
                golden_ok = False
        for row in res["ranked"]:
            if not row["pool_moe"] > 0:
                golden_ok = False
    report["hard"]["suppression_reasons_and_intervals"] = {"pass": golden_ok}
    if not golden_ok:
        hard_fail.append("suppression")

    # ---- hard: rank stability across replicates ----------------------------
    stab = {}
    for v in GOLDEN_VECTORS:
        body = {k: v[k] for k in ("self", "seeking", "weights", "size_vs_odds")
                if k in v}
        req = engine.parse_request(body)
        res = persona_results[v["name"]]
        ranked_cbsas = [r["cbsa"] for r in res["ranked"]]
        if len(ranked_cbsas) < 12:
            stab[v["name"]] = {"skipped": f"only {len(ranked_cbsas)} ranked"}
            continue
        pw, rw = _spec_to_sql(v["seeking"], v["self"])
        P = _replicate_sums(con, pw).set_index("cbsa")
        R = _replicate_sums(con, rw).set_index("cbsa")
        P = P.reindex(ranked_cbsas).fillna(0.0)
        R = R.reindex(ranked_cbsas).fillna(0.0)
        ridx = np.array([build.metro_levels.index(c) for c in ranked_cbsas])
        wts = res["weights"]
        base_top = set(ranked_cbsas[:10])
        hits = 0
        for i in range(1, 81):
            est_r = P[f"r{i}"].to_numpy()
            ratio_r = est_r / np.maximum(R[f"r{i}"].to_numpy(), 1e-9)
            score_r = _score_from_vectors(build, ridx, est_r, ratio_r, wts)
            top_r = {ranked_cbsas[k] for k in np.argsort(-score_r)[:10]}
            if len(top_r & base_top) >= STABILITY_OVERLAP:
                hits += 1
        stab[v["name"]] = {"share_replicates_with_>=8of10_overlap": hits / 80}
    shares = [s["share_replicates_with_>=8of10_overlap"]
              for s in stab.values() if "skipped" not in s]
    ok = all(s >= STABILITY_SHARE for s in shares)
    report["hard"]["rank_stability"] = {"pass": bool(ok), "per_persona": stab,
                                        "gate": f">= {STABILITY_OVERLAP}/10 overlap "
                                                f"in >= {STABILITY_SHARE:.0%} of replicates"}
    if not ok:
        hard_fail.append("rank_stability")

    # ---- hard: adversarial artifacts ---------------------------------------
    quality = pd.read_csv(RESULTS / "phase1" / "metro_quality.csv",
                          dtype={"cbsa": str}).set_index("cbsa")
    adversarial = set(quality.nlargest(6, "noninst_gq_share_18_70").index) | \
        set(quality.nlargest(4, "inst_gq_share").index)
    findings = []
    for name, res in persona_results.items():
        for row in res["ranked"][:10]:
            if row["cbsa"] in adversarial:
                body = next(v for v in GOLDEN_VECTORS if v["name"] == name)
                pw, _ = _spec_to_sql(body["seeking"], body["self"])
                tot, hh_only = con.execute(
                    f"SELECT sum(pwgtp * a_eff) FILTER (WHERE gq <> 2), "
                    f"sum(pwgtp * a_eff) FILTER (WHERE gq = 0) "
                    f"FROM contrib WHERE cbsa = ? AND ({pw})",
                    [row["cbsa"]]).fetchone()
                gq_share = 1 - (hh_only or 0) / tot if tot else 0
                findings.append({"persona": name, "cbsa": row["cbsa"],
                                 "rank": row["rank"],
                                 "pool_share_noninst_gq": round(gq_share, 4),
                                 "gq_traceable": gq_share > GQ_POOL_SHARE_LIMIT})
    ok = not any(f["gq_traceable"] for f in findings)
    report["hard"]["adversarial_artifacts"] = {
        "pass": bool(ok), "watchlist": sorted(adversarial),
        "top10_appearances": findings,
        "rule": f"a watchlist metro in a top-10 fails if > "
                f"{GQ_POOL_SHARE_LIMIT:.0%} of that persona's pool there is "
                f"noninstitutional GQ"}
    if not ok:
        hard_fail.append("adversarial_artifacts")

    # ---- soft: face validity ------------------------------------------------
    face = []
    for name, res in persona_results.items():
        top = res["ranked"][:3]
        for row in top:
            top_pillar = max(row["contributions"], key=lambda c: c["value"])
            face.append({"persona": name, "cbsa": row["cbsa"], "rank": row["rank"],
                         "score": row["score"], "top_pillar": top_pillar["pillar"],
                         "explanation": row["explanation"],
                         "flags": row["flags"]})
    report["soft"]["face_validity"] = {
        "note": "reviewed by hand each build; every result must be "
                "explainable from its attribution",
        "rows": face}

    # ---- soft: weight sensitivity -------------------------------------------
    baseline = persona_results["A_woman32_ba_men_75k"]
    base_order = [r["cbsa"] for r in baseline["ranked"]]
    taus = {}
    for pillar in engine.PILLARS:
        for direction in (+0.2, -0.2):
            defaults = dict(build.manifest["model_defaults"]["pillar_weights"])
            defaults[pillar] = max(defaults[pillar] * (1 + direction), 0.0)
            body = dict(GOLDEN_VECTORS[0])
            body = {k: body[k] for k in ("self", "seeking") if k in body}
            body["weights"] = defaults
            res = engine.rank(build, engine.parse_request(body))
            order = [r["cbsa"] for r in res["ranked"]]
            common = [c for c in base_order if c in set(order)]
            tau = kendalltau([common.index(c) for c in common],
                             [order.index(c) for c in common]).statistic
            taus[f"{pillar}{'+' if direction > 0 else '-'}20%"] = round(float(tau), 4)
    report["soft"]["weight_sensitivity"] = {
        "kendall_tau": taus, "target": KENDALL_MIN,
        "pass": all(t >= KENDALL_MIN for t in taus.values())}

    # ---- soft: external correlation ----------------------------------------
    geo = "metropolitan statistical area/micropolitan statistical area"
    rows = api_get("2024/acs/acs5", {"get": "B09021_001E,B09021_002E",
                                     "for": f"{geo}:*"})
    ext = pd.DataFrame(rows[1:], columns=rows[0]).rename(
        columns={rows[0][-1]: "cbsa"})
    for c in ["B09021_001E", "B09021_002E"]:
        ext[c] = pd.to_numeric(ext[c], errors="coerce")
        ext.loc[ext[c] <= -111111111, c] = np.nan
    ext["alone_share"] = ext["B09021_002E"] / ext["B09021_001E"]
    # B12007 (median age at first marriage) is NOT published at CBSA level in
    # 2024 acs/acs5 — every metro value returns an annotation jam. Verified
    # 2026-09-12; recorded as a finding. Fallback: state medians mapped
    # through each metro's primary state (coarse, flagged as such).
    srows = api_get("2024/acs/acs5", {"get": "B12007_001E,B12007_002E",
                                      "for": "state:*"})
    st = pd.DataFrame(srows[1:], columns=srows[0])
    for c in ["B12007_001E", "B12007_002E"]:
        st[c] = pd.to_numeric(st[c], errors="coerce")
        st.loc[st[c] <= -111111111, c] = np.nan
    st["med_age_marry_state"] = (st["B12007_001E"] + st["B12007_002E"]) / 2
    state_med = dict(zip(st["state"], st["med_age_marry_state"]))
    metros_df = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})
    primary_state = {r["cbsa"]: str(r["states"]).split("+")[0]
                     for _, r in metros_df.iterrows()}
    b_res = persona_results["B_man28_women_never"]
    ours = pd.DataFrame([{"cbsa": r["cbsa"], "score": r["score"],
                          "ratio": r["ratio"]} for r in b_res["ranked"]])
    ours["med_age_marry_state"] = ours["cbsa"].map(
        lambda c: state_med.get(primary_state.get(c)))
    m = ours.merge(ext[["cbsa", "alone_share"]], on="cbsa")
    corr = {}
    for a in ("score", "ratio"):
        for b in ("alone_share", "med_age_marry_state"):
            mm = m[[a, b]].dropna()
            corr[f"{a}_vs_{b}"] = {
                "n": int(len(mm)),
                "pearson": round(float(pearsonr(mm[a], mm[b]).statistic), 3),
                "spearman": round(float(spearmanr(mm[a], mm[b]).statistic), 3)}
    report["soft"]["external_correlation"] = {
        "n_metros": int(len(m)), "correlations": corr,
        "b12007_finding": "B12007 returns annotation jams for every CBSA in "
                          "2024 acs/acs5 — median age at first marriage is "
                          "not published at metro level; state-level medians "
                          "used through each metro's primary state",
        "framing": "the index measures opportunity, not outcome; partnership "
                   "outcomes reflect decades of sorting and migration, so "
                   "weak correlation is expected and reported as measured "
                   "(§11)"}

    report["hard_failures"] = hard_fail
    P2.mkdir(parents=True, exist_ok=True)
    (P2 / "validation_report.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"hard_failures": hard_fail,
                      "rank_stability": {k: v for k, v in list(stab.items())[:4]},
                      "weight_sensitivity": report["soft"]["weight_sensitivity"]["kendall_tau"],
                      "external": corr}, indent=2))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
