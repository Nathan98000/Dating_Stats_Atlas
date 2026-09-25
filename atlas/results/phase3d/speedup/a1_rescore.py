"""Phase 3d A1, proof 2 (items 2-3): the Phase 3c leave-one-metro-out
decisions re-scored from the a1 store's records — the forms refitted
under the couple-weighted rule, their LOMO refits warm-started from the
smoothed-stage terms and stopped on tolerance — next to Phase 3c's
figures. Reads results only.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/speedup/a1_rescore.py [a1|a2]
        -> results/phase3d/speedup/<store>_rescore.json
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from atlas.pipeline.fetch import RESULTS

OUT = RESULTS / "phase3d" / "speedup"
P3C = RESULTS / "phase3c"
CANDIDATES = ("C1_cohorts_plus_shipped", "C2_edu_by_sex_plus_shipped", "C3_both_plus_shipped")


def stage_stats(lomo: list[dict], form: str) -> dict:
    recs = [r["forms"][form] for r in lomo if form in r["forms"]]
    out = {"metros": len(recs), "iterations_median": float(np.median([r["iterations"] for r in recs]))}
    if recs and "stages" in recs[0]:
        for st in ("raw", "smoothed", "interaction"):
            passes = [r["stages"][st]["passes"] for r in recs]
            out[st] = {"passes_median": float(np.median(passes)), "passes_max": int(max(passes)),
                       "stopped_on_cap": int(sum(r["stages"][st]["stopped_on"] == "cap" for r in recs))}
        secs = [r["seconds_refit"] for r in recs if r.get("seconds_refit") is not None]
        if secs:
            out["seconds_refit_median"] = float(np.median(secs))
    return out


def main(store: str) -> None:
    D = OUT / store
    ho = json.loads((D / "refine_heldout.json").read_text())
    ho3 = json.loads((P3C / "refine_heldout.json").read_text())
    lomo = json.loads((D / "lomo_forms.json").read_text())
    rep = json.loads((D / "refine_fits.json").read_text())
    rep3 = json.loads((P3C / "refine_fits.json").read_text())
    out = {"store": store, "forms": {}, "decisions": {}}
    for name, r in ho["forms"].items():
        r3 = ho3["forms"].get(name, {})
        out["forms"][name] = {
            "heldout_gain_vs_shipped_per_1000": r.get("gain_vs_shipped_shrunk_per_1000_sides"),
            "phase3c_heldout_gain_vs_shipped_per_1000": r3.get("gain_vs_shipped_shrunk_per_1000_sides"),
            "heldout_gain_vs_baseline_per_1000": r["gain_vs_baseline_shrunk_per_1000_sides"],
            "phase3c_heldout_gain_vs_baseline_per_1000": r3.get("gain_vs_baseline_shrunk_per_1000_sides"),
            "heldout_loglik_shrunk": r["heldout_loglik_shrunk"],
            "phase3c_heldout_loglik_shrunk": r3.get("heldout_loglik_shrunk"),
            "metros_better_than_shipped": r.get("metros_where_better_than_shipped_shrunk"),
            "phase3c_metros_better_than_shipped": r3.get("metros_where_better_than_shipped_shrunk"),
            "improves_on_shipped": r.get("improves_on_shipped"),
            "phase3c_improves_on_shipped": r3.get("improves_on_shipped"),
            "dial_gain_per_1000": r["dial_gain_shrunk_minus_national_per_1000_sides"],
            "pew_corrected_median_abs_pts": r["pew"]["corrected_errors"]["shrunk_dial"]["median_abs_pts"],
            "phase3c_pew_corrected_median_abs_pts": (r3["pew"]["corrected_errors"]["shrunk_dial"]["median_abs_pts"]
                                                     if r3 else None),
            "full_fit": {k: rep["forms"][name]["ipf"].get(k) for k in
                         ("raw_iterations", "smoothed_iterations", "interaction_iterations", "stopped_on",
                          "objective", "final_move")} if name in rep["forms"] else None,
            "full_fit_seconds": rep["forms"][name].get("seconds") if name in rep["forms"] else None,
            "phase3c_full_fit_seconds": rep3["forms"][name].get("seconds") if name in rep3["forms"] else None,
            "lomo": stage_stats(lomo, name)}
    # the C1/C2/C3 rule as Phase 3c applied it (the gate verdicts are read separately)
    qual = {n: out["forms"][n] for n in CANDIDATES if n in out["forms"]}
    improving = [n for n, r in qual.items() if r["improves_on_shipped"]]
    out["decisions"]["heldout_improves_on_shipped"] = {n: bool(r["improves_on_shipped"]) for n, r in qual.items()}
    out["decisions"]["phase3c_heldout_improves_on_shipped"] = {n: bool(r["phase3c_improves_on_shipped"]) for n, r in qual.items()}
    out["decisions"]["largest_gain_among_improving"] = (max(improving, key=lambda n: qual[n]["heldout_gain_vs_shipped_per_1000"])
                                                       if improving else None)
    out["decisions"]["phase3c_largest_gain_among_improving"] = "C1_cohorts_plus_shipped"
    out["decisions"]["heldout_verdicts_match_phase3c"] = bool(
        out["decisions"]["heldout_improves_on_shipped"] == out["decisions"]["phase3c_heldout_improves_on_shipped"]
        and out["decisions"]["largest_gain_among_improving"] == "C1_cohorts_plus_shipped")
    ss_path = D / "samesex_fit.json"
    if ss_path.exists():
        ss = json.loads(ss_path.read_text())
        ss3 = json.loads((P3C / "samesex_fit.json").read_text())
        h, h3 = ss["heldout"], ss3["heldout"]
        lomo_ss = json.loads((D / "lomo_samesex.json").read_text())
        rec = {"vs_m3_2_0_served_gain_per_1000": h["vs_m3_2_0_served"]["gain_per_1000_sides"],
               "phase3c_vs_m3_2_0_served_gain_per_1000": h3["vs_m3_2_0_served"]["gain_per_1000_sides"],
               "metros_better_than_served": h["vs_m3_2_0_served"]["metros_better_than_served"],
               "education_term_improves_on_served": h["vs_m3_2_0_served"]["education_term_improves_on_served"],
               "interaction_applies": h["interaction_applies"],
               "interaction_margin_per_1000": h["interaction_decision"]["margin_per_1000_sides"],
               "phase3c_interaction_margin_per_1000": h3["interaction_decision"]["margin_per_1000_sides"],
               "served_from_same_sex_couples": h["served_from_same_sex_couples"],
               "phase3c_served_from_same_sex_couples": h3["served_from_same_sex_couples"],
               "face_validity_pass": ss["fit"]["face_validity"]["pass"],
               "seconds_total": ss.get("seconds"), "phase3c_seconds_total": ss3.get("seconds"),
               "fit": {k: ss["fit"]["ipf"].get(k) for k in ("raw_iterations", "smoothed_iterations", "stopped_on", "objective")}}
        recs = [x for x in lomo_ss if x.get("sides", 0) > 0 and "stages" in x]
        if recs:
            rec["lomo"] = {"metros": len(recs),
                           "os_interaction_passes_median": float(np.median([x["stages"]["os"]["interaction"]["passes"] for x in recs])),
                           "os_interaction_stopped_on_cap": int(sum(x["stages"]["os"]["interaction"]["stopped_on"] == "cap" for x in recs)),
                           "os_raw_passes_median": float(np.median([x["stages"]["os"]["raw"]["passes"] for x in recs])),
                           "ss_raw_passes_median": float(np.median([x["stages"]["ss"]["raw"]["passes"] for x in recs])),
                           "seconds_refit_median": [float(np.median([x["seconds_refit"][i] for x in recs])) for i in (0, 1)]}
        rec["verdicts_match_phase3c"] = bool(
            rec["education_term_improves_on_served"] == h3["vs_m3_2_0_served"]["education_term_improves_on_served"]
            and rec["interaction_applies"] == h3["interaction_applies"]
            and rec["served_from_same_sex_couples"] == h3["served_from_same_sex_couples"])
        out["same_sex"] = rec
    (OUT / f"{store}_rescore.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["decisions"], indent=1))
    if "same_sex" in out:
        print(json.dumps({k: out["same_sex"][k] for k in ("vs_m3_2_0_served_gain_per_1000", "interaction_applies",
                                                          "interaction_margin_per_1000", "verdicts_match_phase3c")}, indent=1))
    for n, r in out["forms"].items():
        print(f"  {n}: gain vs shipped {r['heldout_gain_vs_shipped_per_1000']} (3c {r['phase3c_heldout_gain_vs_shipped_per_1000']}); "
              f"lomo {json.dumps(r['lomo'])}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "a1")
