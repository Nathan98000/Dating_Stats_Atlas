"""Phase 3d A1, proof 2 (items 2-3 on): the couple-weighted stopping rule
against the m3.3.0 fit. Fits the shipped opposite-sex form and the
same-sex block under the new rule and reports, next to the m3.3.0 store:
the penalised objective of each (new rule against the old rule's
200-pass fit, both from scratch), the largest change in any log
multiplier (raw, smoothed, gauged) and any dial (theta_hat, theta_tilde),
the timing profile, and whether the bandwidth choice depends on the raw
stage's tolerance (the CV re-run with the raw stage stopped at 1e-3 ...
1e-8 on the cohort form without the interaction, whose raw stage and CV
are the C1 form's, and on the same-sex form).

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/speedup/a1_new_rule.py
        -> results/phase3d/speedup/a1_new_rule.json (+ a1_new_rule_trajectories.json)
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
RAW_TOLS = (1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8)


def per_1000(x: float, sides: float) -> float:
    return x / sides * 1000.0


def main() -> None:
    common = KR.load_common(sample)
    A = common["A"]
    S = KR.load_sample(sample)
    S_ss = KR.load_sample(sample, same_sex=True)
    z = np.load(P3C / "_form_fits.npz")
    zs = np.load(P3C / "_samesex_fit.npz")
    rep = json.loads((P3C / "refine_fits.json").read_text())
    srep = json.loads((P3C / "samesex_fit.json").read_text())
    repro = json.loads((OUT / "a1_reproduction.json").read_text())
    out = {"rule": {"stop": KR.STOP_RULE, "ctol": KR.COUPLE_TOL, "raw_ctol": KR.RAW_COUPLE_TOL,
                    "otol_per_1000_sides_per_pass": KR.OBJECTIVE_TOL},
           "fits": {}, "bandwidth_choice_vs_raw_tolerance": {}}
    traj = {}
    # ---- C1 under the new rule
    name = "C1_cohorts_plus_shipped"
    form = KR.Form(age_edges=EDGES, interaction=True, name=name)
    t0 = time.time()
    fit = KR.fit_form(S["C"], A, form, mean_weight=S["mean_weight"])
    t1 = time.time()
    fg = KR.gauge_form(fit["f"], A, fit["N_s"], form)
    sides = fit["couple_sides"]
    d = KR.design2(form)
    T = fit["T"]
    logA = KR.log_avail(A, False)
    lam = S["mean_weight"] / rep["fits"][name]["tau2"]
    # the m3.3.0 fit's objective from scratch, with ITS tau^2 and with the new fit's
    f_old = {k: z[f"{name}__f_{k}"] for k in ("age", "edu", "race", "int")}
    obj_old_own = KR._objective_of(f_old, T, logA, fit["N_s"], lam, d)
    lam_new = S["mean_weight"] / fit["tau2"]
    obj_old_newlam = KR._objective_of(f_old, T, logA, fit["N_s"], lam_new, d)
    obj_new = fit["objective_from_scratch"]
    full, halves = K.load_metro_tables(sample)
    th, se2, shr = KR.full_dials(fg, form, full, common["A_metro"], common["metro_levels"], common["n_eff"])
    dd = pd.read_csv(P3C / f"dials_{name}.csv", dtype={"cbsa": str}).set_index("cbsa").loc[common["metro_levels"]]
    rec = {"seconds_fit": round(t1 - t0, 1),
           "seconds_fit_old_code_this_machine": json.loads((OUT / "timing_old_code.json").read_text())["fits"][name]["seconds"]
           if (OUT / "timing_old_code.json").exists() else None,
           "seconds_fit_old_rule_new_engine": repro["fits"][name]["seconds_fit"],
           "iterations": {"raw": fit["raw_iterations"], "smoothed": fit["smoothed_iterations"],
                          "interaction": fit["interaction_iterations"]},
           "stopped_on": {k: fit["history"][k]["stopped_on"] for k in ("raw", "smoothed", "interaction")},
           "iterations_m3_3_0": rep["forms"][name]["ipf"],
           "bandwidth_equal_to_m3_3_0": fit["bandwidth"] == rep["fits"][name]["bandwidth"],
           "tau2": fit["tau2"], "tau2_m3_3_0": rep["fits"][name]["tau2"],
           "objective": {"new_rule": obj_new, "m3_3_0_fit_its_tau2": obj_old_own,
                         "m3_3_0_fit_new_tau2": obj_old_newlam,
                         "new_minus_m3_3_0_per_1000_sides": per_1000(obj_new - obj_old_newlam, sides),
                         "new_minus_m3_3_0_units": obj_new - obj_old_newlam,
                         "no_worse": bool(obj_new >= obj_old_newlam),
                         "note": "penalised conditional log-likelihood in weight units up to the constant "
                                 "sum C log A; the ridge term uses the new fit's tau^2 for both (the two "
                                 "tau^2 differ only through the raw stage's stopping point)"},
           "largest_change_vs_m3_3_0": {
               "log_multipliers_smoothed": {k: float(np.abs(fit["f"][k] - z[f"{name}__f_{k}"]).max()) for k in fit["f"]},
               "log_multipliers_raw": {k: float(np.abs(fit["raw_f"][k] - z[f"{name}__raw_{k}"]).max()) for k in fit["raw_f"]},
               "log_multipliers_gauged": {k: float(np.abs(fg[k] - z[f"{name}__fg_{k}"]).max()) for k in fg},
               "dials_theta_hat": float(np.abs(th - z[f"{name}__theta_hat"]).max()),
               "dials_theta_tilde": float(max(np.abs(shr[k]["theta_tilde"] - dd[f"theta_tilde_{k}"].to_numpy(float)).max()
                                              for k in K.COMPONENTS))},
           "couple_sides": sides, "profile": fit["profile"], "final_move": fit["final_move"]}
    out["fits"][name] = rec
    traj[name] = fit["history"]
    print(json.dumps({k: rec[k] for k in ("seconds_fit", "iterations", "stopped_on", "bandwidth_equal_to_m3_3_0")}),
          json.dumps(rec["objective"]), json.dumps(rec["largest_change_vs_m3_3_0"]), flush=True)
    # ---- the same-sex block under the new rule
    form_ss = KR.Form(name="samesex")
    t0 = time.time()
    fit_ss = KR.fit_form(S_ss["C"], A, form_ss, mean_weight=S_ss["mean_weight"], same_sex=True)
    t1 = time.time()
    fg_ss = KR.gauge_form(fit_ss["f"], A, fit_ss["N_s"], form_ss, same_sex=True)
    f_old = {k: zs[f"f_{k}"] for k in ("age", "edu", "race")}
    obj_old = KR._objective_of(f_old, fit_ss["T"], KR.log_avail(A, True), fit_ss["N_s"], np.inf, KR.design2(form_ss))
    rec = {"seconds_fit": round(t1 - t0, 1),
           "seconds_fit_old_code_this_machine": json.loads((OUT / "timing_old_code.json").read_text())["fits"]["samesex"]["seconds"]
           if (OUT / "timing_old_code.json").exists() else None,
           "seconds_fit_old_rule_new_engine": repro["fits"]["samesex"]["seconds_fit"],
           "iterations": {"raw": fit_ss["raw_iterations"], "smoothed": fit_ss["smoothed_iterations"]},
           "stopped_on": {k: fit_ss["history"][k]["stopped_on"] for k in ("raw", "smoothed")},
           "iterations_m3_3_0": srep["fit"]["ipf"],
           "bandwidth_equal_to_m3_3_0": fit_ss["bandwidth"] == list(srep["fit"]["bandwidth_by_sex_cohort"].values()),
           "objective": {"new_rule": fit_ss["objective_from_scratch"], "m3_3_0_fit": obj_old,
                         "new_minus_m3_3_0_per_1000_sides": per_1000(fit_ss["objective_from_scratch"] - obj_old, fit_ss["couple_sides"]),
                         "new_minus_m3_3_0_units": fit_ss["objective_from_scratch"] - obj_old,
                         "no_worse": bool(fit_ss["objective_from_scratch"] >= obj_old)},
           "largest_change_vs_m3_3_0": {
               "log_multipliers_smoothed": {k: float(np.abs(fit_ss["f"][k] - zs[f"f_{k}"]).max()) for k in fit_ss["f"]},
               "log_multipliers_gauged": {k: float(np.abs(fg_ss[k] - zs[f"fg_{k}"]).max()) for k in fg_ss}},
           "couple_sides": fit_ss["couple_sides"], "profile": fit_ss["profile"], "final_move": fit_ss["final_move"]}
    out["fits"]["samesex"] = rec
    traj["samesex"] = fit_ss["history"]
    print(json.dumps({k: rec[k] for k in ("seconds_fit", "iterations", "stopped_on", "bandwidth_equal_to_m3_3_0")}),
          json.dumps(rec["objective"]), flush=True)
    # ---- the bandwidth choice against the raw stage's tolerance
    for label, C_, mw, ss, form_, ref_bw in (
            ("cohorts_17_no_interaction", S["C"], S["mean_weight"], False, KR.Form(age_edges=EDGES, name="B1"),
             rep["fits"][name]["bandwidth"]),
            ("samesex", S_ss["C"], S_ss["mean_weight"], True, form_ss, list(srep["fit"]["bandwidth_by_sex_cohort"].values()))):
        rows = {}
        for rt in RAW_TOLS:
            t0 = time.time()
            ft = KR.fit_form(C_, A, form_, mean_weight=mw, same_sex=ss, raw_ctol=rt, max_iter=K.IPF_MAX_ITER)
            rows[f"{rt:.0e}"] = {"raw_passes": ft["raw_iterations"], "raw_stopped_on": ft["history"]["raw"]["stopped_on"],
                                 "chosen": ft["bandwidth"], "equal_to_m3_3_0": ft["bandwidth"] == ref_bw,
                                 "rows_differing": int(sum(a != b for a, b in zip(ft["bandwidth"], ref_bw))),
                                 "seconds": round(time.time() - t0, 1)}
            print(label, rt, rows[f"{rt:.0e}"]["raw_passes"], rows[f"{rt:.0e}"]["equal_to_m3_3_0"], flush=True)
        out["bandwidth_choice_vs_raw_tolerance"][label] = {
            "m3_3_0_bandwidths": ref_bw, "by_raw_tolerance": rows,
            "independent_of_raw_tolerance": all(r["equal_to_m3_3_0"] for r in rows.values())}
    (OUT / "a1_new_rule.json").write_text(json.dumps(out, indent=1, default=KR._json) + "\n")
    (OUT / "a1_new_rule_trajectories.json").write_text(json.dumps(traj, indent=0, default=KR._json) + "\n")
    print("done")


if __name__ == "__main__":
    main()
