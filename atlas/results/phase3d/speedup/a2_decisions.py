"""Phase 3d A2: the decisions that shaped m3.3.0, re-run on the finished
(projected) fit, read from the a2 store — held-out gains from the LOMO
summary, the ADR 0011 gate verdicts from the candidate checks, the
same-sex decision from samesex_fit.json — and compared verdict by verdict
with Phase 3b/3c's. Any flip is a stop condition. Reads results only.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/speedup/a2_decisions.py
        -> results/phase3d/speedup/a2_decisions.json
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from atlas.pipeline.fetch import RESULTS

OUT = RESULTS / "phase3d" / "speedup"
A2 = OUT / "a2"
P3C = RESULTS / "phase3c"
CANDIDATES = ("C1_cohorts_plus_shipped", "C2_edu_by_sex_plus_shipped", "C3_both_plus_shipped")


def gate(path: Path) -> dict | None:
    if not path.exists():
        return None
    v = json.loads(path.read_text())["verdict"]
    return {k: v[k] for k in ("pass", "ratio", "searches_touched", "wobble_candidate", "wobble_reference",
                              "ratio_over_all_searches")} | {
        "old_rule_min_share_personas": v["old_rule"]["min_share_personas"],
        "searches_wobble_rose_more_than_25pct": len(v["searches_wobble_rose_more_than_25pct"])}


def main() -> None:
    ho = json.loads((A2 / "refine_heldout.json").read_text())
    ho3 = json.loads((P3C / "refine_heldout.json").read_text())
    ss = json.loads((A2 / "samesex_fit.json").read_text())["heldout"]
    ss3 = json.loads((P3C / "samesex_fit.json").read_text())["heldout"]
    out = {"decisions": {}, "all_verdicts_match": True}
    # 1. Phase 3b: race x education ships (improves held-out over the baseline; passes the gate)
    b2a = ho["forms"]["B2a_race_x_edu"]
    g = gate(A2 / "gate_B2a_race_x_edu.json")
    d = {"rule": "ships if it improves total held-out likelihood over the baseline form and passes the "
                 "rank-stability gate (Phase 3b; the gate read today is ADR 0011's against the m3.2.0 reference "
                 "on the candidate as Phase 3b wrote it, baseline + interaction, no same-sex terms)",
         "heldout_gain_vs_baseline_per_1000": b2a["gain_vs_baseline_shrunk_per_1000_sides"],
         "phase3b_heldout_gain_vs_baseline_per_1000": ho3["forms"]["B2a_race_x_edu"]["gain_vs_baseline_shrunk_per_1000_sides"],
         "metros_better_than_baseline": b2a["metros_where_better_than_baseline_shrunk"],
         "improves_heldout": bool(b2a["ships"]), "gate": g,
         "verdict_ships": bool(b2a["ships"] and (g is None or g["pass"])),
         "phase3b_verdict_ships": True}
    d["matches"] = d["verdict_ships"] == d["phase3b_verdict_ships"]
    out["decisions"]["race_x_education_phase3b"] = d
    # 2. Phase 3c B3: C1/C2/C3 — of those improving on the shipped form and passing the gate, the largest gain
    cands = {}
    for n in CANDIDATES:
        r = ho["forms"][n]
        g = gate(A2 / f"gate_{n}.json")
        cands[n] = {"heldout_gain_vs_shipped_per_1000": r["gain_vs_shipped_shrunk_per_1000_sides"],
                    "phase3c_heldout_gain_vs_shipped_per_1000": ho3["forms"][n]["gain_vs_shipped_shrunk_per_1000_sides"],
                    "metros_better_than_shipped": r["metros_where_better_than_shipped_shrunk"],
                    "improves_on_shipped": bool(r["improves_on_shipped"]),
                    "phase3c_improves_on_shipped": bool(ho3["forms"][n]["improves_on_shipped"]),
                    "gate": g, "qualifies": bool(r["improves_on_shipped"] and g is not None and g["pass"])}
    qual = [n for n, c in cands.items() if c["qualifies"]]
    winner = max(qual, key=lambda n: cands[n]["heldout_gain_vs_shipped_per_1000"]) if qual else None
    d = {"rule": "of the candidates that improve held-out fit over the shipped form and pass the gate, the largest gain ships",
         "candidates": cands, "qualifying": qual, "ships": winner, "phase3c_ships": "C1_cohorts_plus_shipped",
         "phase3c_qualifying": ["C1_cohorts_plus_shipped", "C3_both_plus_shipped"]}
    d["matches"] = bool(winner == d["phase3c_ships"] and sorted(qual) == sorted(d["phase3c_qualifying"]))
    out["decisions"]["cohorts_edu_by_sex_both_phase3c_B3"] = d
    # 3. Phase 3c B2: the same-sex education term and whether the interaction rides
    d = {"rule": "the education term ships if it improves held-out same-sex fit on what m3.2.0 serves (either "
                 "interaction setting); the interaction rides if the composition with it predicts better",
         "gain_per_1000_vs_served": ss["vs_m3_2_0_served"]["gain_per_1000_sides"],
         "phase3c_gain_per_1000_vs_served": ss3["vs_m3_2_0_served"]["gain_per_1000_sides"],
         "metros_better_than_served": ss["vs_m3_2_0_served"]["metros_better_than_served"],
         "education_term_improves_on_served": bool(ss["vs_m3_2_0_served"]["education_term_improves_on_served"]),
         "interaction_applies": bool(ss["interaction_applies"]),
         "interaction_margin_per_1000": ss["interaction_decision"]["margin_per_1000_sides"],
         "phase3c_interaction_margin_per_1000": ss3["interaction_decision"]["margin_per_1000_sides"],
         "served_from_same_sex_couples": ss["served_from_same_sex_couples"],
         "phase3c_served_from_same_sex_couples": ss3["served_from_same_sex_couples"],
         "gate_shipped_form_with_same_sex_decision": gate(A2 / "gate_shipped.json")}
    d["matches"] = bool(d["education_term_improves_on_served"] == ss3["vs_m3_2_0_served"]["education_term_improves_on_served"]
                        and d["interaction_applies"] == ss3["interaction_applies"]
                        and d["served_from_same_sex_couples"] == ss3["served_from_same_sex_couples"])
    out["decisions"]["same_sex_education_and_interaction_phase3c_B2"] = d
    out["all_verdicts_match"] = all(v["matches"] for v in out["decisions"].values())
    out["stop_condition_verdict_flipped"] = not out["all_verdicts_match"]
    (OUT / "a2_decisions.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v["matches"] for k, v in out["decisions"].items()}), "all match:", out["all_verdicts_match"])
    print(json.dumps(out["decisions"]["cohorts_edu_by_sex_both_phase3c_B3"]["candidates"], indent=1))


if __name__ == "__main__":
    main()
