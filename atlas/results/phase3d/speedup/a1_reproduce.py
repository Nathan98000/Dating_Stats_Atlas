"""Phase 3d A1, proof 1: with m3.3.0's stopping rule (stop="cell"), the
in-place table engine reproduces the m3.3.0 artifact's fit — the
C1_cohorts_plus_shipped form's log multipliers (raw, smoothed, gauged),
its 387 x 3 dials, and the same-sex block — to 1e-9, from the stored
Phase 3c fit store. Also records every pass's largest cell change,
couple-weighted move and objective (the trajectories the new stopping
rule is chosen from) and the timing profile.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/speedup/a1_reproduce.py
        -> results/phase3d/speedup/a1_reproduction.json, a1_trajectories.json
"""
import json, time, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from atlas.pipeline.build import kernel as K
from atlas.pipeline.build import kernel_refine as KR
from atlas.pipeline.fetch import RESULTS

OUT = RESULTS / "phase3d" / "speedup"
P3C = RESULTS / "phase3c"
sample = "decay_h5"
EDGES = (20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 43, 46, 50, 55, 60)


def _overall(d: dict) -> float:
    vals = []
    for v in d.values():
        vals.extend(v.values() if isinstance(v, dict) else [v])
    return float(max(vals))


def main() -> None:
    common = KR.load_common(sample)
    A = common["A"]
    S = KR.load_sample(sample)
    S_ss = KR.load_sample(sample, same_sex=True)
    z = np.load(P3C / "_form_fits.npz")
    zs = np.load(P3C / "_samesex_fit.npz")
    rep = json.loads((P3C / "refine_fits.json").read_text())
    assert rep["forms"]["C1_cohorts_plus_shipped"]["form"]["age_edges"] == list(EDGES)
    out = {"rule": "stop='cell' (m3.3.0's: largest single-cell change below 1e-6, 200-pass caps)",
           "reference": "results/phase3c/_form_fits.npz, dials_C1_cohorts_plus_shipped.csv, _samesex_fit.npz (m3.3.0)",
           "fits": {}}
    traj = {}
    # --- the shipped opposite-sex form
    form = KR.Form(age_edges=EDGES, interaction=True, name="C1_cohorts_plus_shipped")
    t0 = time.time()
    fit = KR.fit_form(S["C"], A, form, mean_weight=S["mean_weight"], stop="cell")
    t1 = time.time()
    fg = KR.gauge_form(fit["f"], A, fit["N_s"], form)
    name = "C1_cohorts_plus_shipped"
    d = {"log_multipliers_smoothed": {k: float(np.abs(fit["f"][k] - z[f"{name}__f_{k}"]).max()) for k in fit["f"]},
         "log_multipliers_raw": {k: float(np.abs(fit["raw_f"][k] - z[f"{name}__raw_{k}"]).max()) for k in fit["raw_f"]},
         "log_multipliers_gauged": {k: float(np.abs(fg[k] - z[f"{name}__fg_{k}"]).max()) for k in fg}}
    rec = {"seconds_fit": round(t1 - t0, 1), "iterations": {"raw": fit["raw_iterations"], "smoothed": fit["smoothed_iterations"],
                                                             "interaction": fit["interaction_iterations"]},
           "phase3c_record": rep["forms"][name]["ipf"], "phase3c_seconds_fit_and_report": rep["forms"][name]["seconds"],
           "bandwidth_equal": fit["bandwidth"] == rep["fits"][name]["bandwidth"],
           "tau2": fit["tau2"], "tau2_phase3c": rep["fits"][name]["tau2"],
           "tau2_abs_diff": abs(fit["tau2"] - rep["fits"][name]["tau2"]),
           "final_change": fit["final_change"], "final_change_phase3c": rep["forms"][name]["ipf"]["final_change"],
           "objective": fit["objective"], "objective_from_scratch": fit["objective_from_scratch"],
           "couple_sides": fit["couple_sides"], "max_abs_diff": d, "profile": fit["profile"]}
    # dials: every metro's three unshrunk dials and their variances
    full, halves = K.load_metro_tables(sample)
    t2 = time.time()
    th, se2, shr = KR.full_dials(fg, form, full, common["A_metro"], common["metro_levels"], common["n_eff"])
    rec["seconds_dials"] = round(time.time() - t2, 1)
    dd = pd.read_csv(P3C / f"dials_{name}.csv", dtype={"cbsa": str}).set_index("cbsa").loc[common["metro_levels"]]
    rec["max_abs_diff"]["dials_theta_hat_vs_store_npz"] = float(np.abs(th - z[f"{name}__theta_hat"]).max())
    rec["max_abs_diff"]["dials_se2_vs_store_npz"] = float(np.abs(se2 - z[f"{name}__se2"]).max())
    rec["max_abs_diff"]["dials_theta_tilde_vs_csv"] = float(max(
        np.abs(shr[k]["theta_tilde"] - dd[f"theta_tilde_{k}"].to_numpy(float)).max() for k in K.COMPONENTS))
    rec["max_abs_diff"]["dials_theta_hat_vs_csv"] = float(max(
        np.abs(th[:, j] - dd[f"theta_hat_{k}"].to_numpy(float)).max() for j, k in enumerate(K.COMPONENTS)))
    rec["max_abs_diff_overall"] = _overall(rec["max_abs_diff"])
    rec["reproduces_to_1e-9"] = bool(rec["max_abs_diff_overall"] < 1e-9 and rec["bandwidth_equal"])
    out["fits"][name] = rec
    traj[name] = fit["history"]
    print(json.dumps({k: rec[k] for k in ("seconds_fit", "iterations", "bandwidth_equal", "max_abs_diff_overall",
                                          "reproduces_to_1e-9")}), flush=True)
    # --- the same-sex block
    form_ss = KR.Form(name="samesex")
    srep = json.loads((P3C / "samesex_fit.json").read_text())
    t0 = time.time()
    fit_ss = KR.fit_form(S_ss["C"], A, form_ss, mean_weight=S_ss["mean_weight"], same_sex=True, stop="cell")
    t1 = time.time()
    fg_ss = KR.gauge_form(fit_ss["f"], A, fit_ss["N_s"], form_ss, same_sex=True)
    d = {"log_multipliers_smoothed": {k: float(np.abs(fit_ss["f"][k] - zs[f"f_{k}"]).max()) for k in fit_ss["f"]},
         "log_multipliers_gauged": {k: float(np.abs(fg_ss[k] - zs[f"fg_{k}"]).max()) for k in fg_ss}}
    bw_rec = list(srep["fit"]["bandwidth_by_sex_cohort"].values())
    rec = {"seconds_fit": round(t1 - t0, 1), "iterations": {"raw": fit_ss["raw_iterations"], "smoothed": fit_ss["smoothed_iterations"]},
           "phase3c_record": srep["fit"]["ipf"], "phase3c_seconds_fit_and_report": srep["fit"]["seconds"],
           "bandwidth_equal": fit_ss["bandwidth"] == bw_rec, "bandwidth": fit_ss["bandwidth"],
           "final_change": fit_ss["final_change"], "final_change_phase3c": srep["fit"]["ipf"]["final_change"],
           "objective": fit_ss["objective"], "couple_sides": fit_ss["couple_sides"],
           "max_abs_diff": d, "profile": fit_ss["profile"]}
    rec["max_abs_diff_overall"] = _overall(rec["max_abs_diff"])
    rec["reproduces_to_1e-9"] = bool(rec["max_abs_diff_overall"] < 1e-9 and rec["bandwidth_equal"])
    out["fits"]["samesex"] = rec
    traj["samesex"] = fit_ss["history"]
    print(json.dumps({k: rec[k] for k in ("seconds_fit", "iterations", "bandwidth_equal", "max_abs_diff_overall",
                                          "reproduces_to_1e-9")}), flush=True)
    out["reproduces_to_1e-9"] = all(r["reproduces_to_1e-9"] for r in out["fits"].values())
    (OUT / "a1_reproduction.json").write_text(json.dumps(out, indent=1, default=KR._json) + "\n")
    (OUT / "a1_trajectories.json").write_text(json.dumps(traj, indent=0, default=KR._json) + "\n")
    print("reproduces_to_1e-9:", out["reproduces_to_1e-9"])


if __name__ == "__main__":
    main()
