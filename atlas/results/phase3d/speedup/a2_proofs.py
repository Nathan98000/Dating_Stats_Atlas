"""Phase 3d A2, proofs 1 and 2 on the shipped opposite-sex form: with the
projection switched OFF the code reproduces the A1 fit (the a1 store's
C1_cohorts_plus_shipped, fitted under the new stopping rule) to 1e-9; with
it ON the penalised objective is at least as high, and the record shows
how far each block moved — the largest change in any log multiplier
(smoothed and gauged) and in any dial against the A1 fit and against the
m3.3.0 store — with the timing profile of each. The same-sex block has no
interaction, so the projection cannot touch it; that is asserted too.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/speedup/a2_proofs.py
        -> results/phase3d/speedup/a2_proofs.json (+ a2_trajectories.json)
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
A1 = OUT / "a1"
P3C = RESULTS / "phase3c"
sample = "decay_h5"
EDGES = (20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 43, 46, 50, 55, 60)
NAME = "C1_cohorts_plus_shipped"


def main() -> None:
    assert KR.PROJECT_INTERACTION, "the projection must be on by default for this proof"
    common = KR.load_common(sample)
    A = common["A"]
    S = KR.load_sample(sample)
    S_ss = KR.load_sample(sample, same_sex=True)
    za = np.load(A1 / "_form_fits.npz")
    z3 = np.load(P3C / "_form_fits.npz")
    rep_a1 = json.loads((A1 / "refine_fits.json").read_text())
    form = KR.Form(age_edges=EDGES, interaction=True, name=NAME)
    d = KR.design2(form)
    full, halves = K.load_metro_tables(sample)
    dd_a1 = pd.read_csv(A1 / f"dials_{NAME}.csv", dtype={"cbsa": str}).set_index("cbsa").loc[common["metro_levels"]]
    dd_3c = pd.read_csv(P3C / f"dials_{NAME}.csv", dtype={"cbsa": str}).set_index("cbsa").loc[common["metro_levels"]]
    out = {"form": form.describe(), "fits": {}}
    traj = {}
    for label, project in (("projection_off", False), ("projection_on", True)):
        t0 = time.time()
        fit = KR.fit_form(S["C"], A, form, mean_weight=S["mean_weight"], project=project)
        t1 = time.time()
        fg = KR.gauge_form(fit["f"], A, fit["N_s"], form)
        th, se2, shr = KR.full_dials(fg, form, full, common["A_metro"], common["metro_levels"], common["n_eff"])
        t2 = time.time()
        rec = {"seconds_fit": round(t1 - t0, 1), "seconds_dials": round(t2 - t1, 1),
               "iterations": {"raw": fit["raw_iterations"], "smoothed": fit["smoothed_iterations"],
                              "interaction": fit["interaction_iterations"]},
               "stopped_on": {k: fit["history"][k]["stopped_on"] for k in ("raw", "smoothed", "interaction")},
               "bandwidth_equal_to_a1": fit["bandwidth"] == rep_a1["fits"][NAME]["bandwidth"],
               "tau2": fit["tau2"], "tau2_a1": rep_a1["fits"][NAME]["tau2"],
               "objective": fit["objective_from_scratch"], "objective_a1_record": rep_a1["forms"][NAME]["ipf"]["objective"],
               "projection": fit["projection"], "profile": fit["profile"], "final_move": fit["final_move"],
               "vs_a1": {"log_multipliers_smoothed": {k: float(np.abs(fit["f"][k] - za[f"{NAME}__f_{k}"]).max()) for k in fit["f"]},
                         "log_multipliers_gauged": {k: float(np.abs(fg[k] - za[f"{NAME}__fg_{k}"]).max()) for k in fg},
                         "dials_theta_hat": float(np.abs(th - za[f"{NAME}__theta_hat"]).max()),
                         "dials_theta_tilde": float(max(np.abs(shr[k]["theta_tilde"] - dd_a1[f"theta_tilde_{k}"].to_numpy(float)).max()
                                                        for k in K.COMPONENTS))},
               "vs_m3_3_0": {"log_multipliers_smoothed": {k: float(np.abs(fit["f"][k] - z3[f"{NAME}__f_{k}"]).max()) for k in fit["f"]},
                             "log_multipliers_gauged": {k: float(np.abs(fg[k] - z3[f"{NAME}__fg_{k}"]).max()) for k in fg},
                             "dials_theta_hat": float(np.abs(th - z3[f"{NAME}__theta_hat"]).max()),
                             "dials_theta_tilde": float(max(np.abs(shr[k]["theta_tilde"] - dd_3c[f"theta_tilde_{k}"].to_numpy(float)).max()
                                                            for k in K.COMPONENTS))}}
        vals = [v for grp in rec["vs_a1"].values() for v in (grp.values() if isinstance(grp, dict) else [grp])]
        rec["max_abs_diff_vs_a1"] = float(max(vals))
        out["fits"][label] = rec
        traj[label] = fit["history"]
        print(label, json.dumps({k: rec[k] for k in ("seconds_fit", "iterations", "stopped_on", "objective", "max_abs_diff_vs_a1")}),
              json.dumps(rec["projection"]), flush=True)
        if project:
            # the served-kernel view of the interaction: the residual's size
            # and the parts that went into the main effects
            g = fg["int"]
            out["interaction_after_projection"] = {
                "log_sd": float(g.std()), "cells_abs_log_above_0_1": int((np.abs(g) > 0.1).sum()),
                "max_abs_log": float(np.abs(g).max()),
                "m3_3_0_log_sd": float(z3[f"{NAME}__fg_int"].std()),
                "m3_3_0_cells_abs_log_above_0_1": int((np.abs(z3[f"{NAME}__fg_int"]) > 0.1).sum())}
    off, on = out["fits"]["projection_off"], out["fits"]["projection_on"]
    out["proof_1_off_reproduces_a1_to_1e-9"] = bool(off["max_abs_diff_vs_a1"] < 1e-9 and off["bandwidth_equal_to_a1"])
    out["proof_2_objective"] = {"on": on["objective"], "off": off["objective"],
                                "on_minus_off_units": on["objective"] - off["objective"],
                                "on_minus_off_per_1000_sides": (on["objective"] - off["objective"]) / S["C"].sum() * 1000,
                                "at_least_as_high": bool(on["objective"] >= off["objective"])}
    # the same-sex block cannot be touched by the projection (no interaction in its form)
    form_ss = KR.Form(name="samesex")
    f_off = KR.fit_form(S_ss["C"], A, form_ss, mean_weight=S_ss["mean_weight"], same_sex=True, project=False)
    f_on = KR.fit_form(S_ss["C"], A, form_ss, mean_weight=S_ss["mean_weight"], same_sex=True, project=True)
    out["same_sex_block_identical_on_off"] = {k: float(np.abs(f_on["f"][k] - f_off["f"][k]).max()) for k in f_on["f"]}
    (OUT / "a2_proofs.json").write_text(json.dumps(out, indent=1, default=KR._json) + "\n")
    (OUT / "a2_trajectories.json").write_text(json.dumps(traj, indent=0, default=KR._json) + "\n")
    print(json.dumps({k: out[k] for k in ("proof_1_off_reproduces_a1_to_1e-9", "proof_2_objective", "same_sex_block_identical_on_off")}))


if __name__ == "__main__":
    main()
