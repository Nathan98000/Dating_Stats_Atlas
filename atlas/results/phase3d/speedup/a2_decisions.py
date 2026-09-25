"""Phase 3d A2: the decisions that shaped m3.3.0, re-run on the finished
(projected) fit, read from the a2 store — held-out gains from the LOMO
records, the ADR 0011 gate verdicts from the candidate checks, the
same-sex decision from the same-sex LOMO record — and compared verdict by
verdict with Phase 3b/3c's. Reads results only; nothing is refitted.

Phase 3d R (ADR 0014): every held-out comparison goes through the shared
functions (`kernel_refine.beats`, `select_form`, `samesex_decision`): a
difference smaller than HELDOUT_TIE_MARGIN_PER_1000 per 1,000 weighted
couple-sides is a tie, and a tie goes to the simpler form. The reading
under the old rule (a strict > 0; the largest gain among the qualifying
candidates) is kept beside it as `old_rule`, so the record shows both.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/speedup/a2_decisions.py
        -> results/phase3d/speedup/a2_decisions.json
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from atlas.pipeline.build import kernel_refine as KR
from atlas.pipeline.fetch import RESULTS

OUT = RESULTS / "phase3d" / "speedup"
A2 = OUT / "a2"
P3C = RESULTS / "phase3c"
CANDIDATES = ("C1_cohorts_plus_shipped", "C2_edu_by_sex_plus_shipped", "C3_both_plus_shipped")
DELTA = KR.HELDOUT_TIE_MARGIN_PER_1000


def gate(path: Path) -> dict | None:
    if not path.exists():
        return None
    v = json.loads(path.read_text())["verdict"]
    return {k: v[k] for k in ("pass", "ratio", "searches_touched", "wobble_candidate", "wobble_reference",
                              "ratio_over_all_searches")} | {
        "old_rule_min_share_personas": v["old_rule"]["min_share_personas"],
        "searches_wobble_rose_more_than_25pct": len(v["searches_wobble_rose_more_than_25pct"])}


def main() -> None:
    rep = json.loads((A2 / "refine_fits.json").read_text())
    forms = KR.forms_for(rep["sample"], tuple(rep["partition"]["chosen_edges"]))
    ho = json.loads((A2 / "refine_heldout.json").read_text())
    ho3 = json.loads((P3C / "refine_heldout.json").read_text())
    ssr = json.loads((A2 / "samesex_fit.json").read_text())
    ss_stored = ssr["heldout"]
    ss3 = json.loads((P3C / "samesex_fit.json").read_text())["heldout"]
    out = {"rule": {"adr": KR.HELDOUT_TIE_ADR, "margin_per_1000_sides": DELTA,
                    "text": "a held-out difference smaller than the margin per 1,000 weighted couple-sides is a "
                            "tie, and a tie goes to the simpler form; wherever a rule requires a candidate to "
                            "improve on a reference it must beat it by the margin; among qualifying candidates "
                            "every one within the margin of the largest gain is tied for first and the simplest "
                            "of those ships (nesting first, then fewer free parameters, then the lower gate "
                            "ratio, the served form, the earlier form in the table)",
                    "old_rule": "improves = a strict > 0; the largest gain among the qualifying candidates ships"},
           "decisions": {}, "all_verdicts_match": True}
    # 1. Phase 3b: race x education ships (improves held-out over the baseline; passes the gate)
    b2a = ho["forms"]["B2a_race_x_edu"]
    g = gate(A2 / "gate_B2a_race_x_edu.json")
    gain = b2a["gain_vs_baseline_shrunk_per_1000_sides"]
    d = {"rule": "ships if it improves total held-out likelihood over the baseline form (ADR 0014: beats it by "
                 "the margin) and passes the rank-stability gate (Phase 3b; the gate read today is ADR 0011's "
                 "against the m3.2.0 reference on the candidate as Phase 3b wrote it, baseline + interaction, "
                 "no same-sex terms)",
         "heldout_gain_vs_baseline_per_1000": gain,
         "phase3b_heldout_gain_vs_baseline_per_1000": ho3["forms"]["B2a_race_x_edu"]["gain_vs_baseline_shrunk_per_1000_sides"],
         "metros_better_than_baseline": b2a["metros_where_better_than_baseline_shrunk"],
         "improves_heldout": KR.beats(gain), "gate": g,
         "verdict_ships": bool(KR.beats(gain) and (g is None or g["pass"])),
         "old_rule": {"improves_heldout": bool(gain > 0), "verdict_ships": bool(gain > 0 and (g is None or g["pass"]))},
         "phase3b_verdict_ships": True}
    d["matches"] = d["verdict_ships"] == d["phase3b_verdict_ships"]
    out["decisions"]["race_x_education_phase3b"] = d
    # 2. Phase 3c B3: C1/C2/C3 — of those beating the shipped form and passing the gate, the largest gain;
    #    every qualifying candidate within the margin of it is tied for first and the simplest ships
    cands, sel_in = {}, {}
    for n in CANDIDATES:
        r = ho["forms"][n]
        g = gate(A2 / f"gate_{n}.json")
        gain = r["gain_vs_shipped_shrunk_per_1000_sides"]
        cands[n] = {"heldout_gain_vs_shipped_per_1000": gain,
                    "phase3c_heldout_gain_vs_shipped_per_1000": ho3["forms"][n]["gain_vs_shipped_shrunk_per_1000_sides"],
                    "metros_better_than_shipped": r["metros_where_better_than_shipped_shrunk"],
                    "beats_shipped": KR.beats(gain),
                    "phase3c_improves_on_shipped": bool(ho3["forms"][n]["improves_on_shipped"]),
                    "gate": g, "form": forms[n].describe(), "free_parameters": KR.free_parameters(forms[n]),
                    "old_rule": {"improves_on_shipped": bool(gain > 0),
                                 "qualifies": bool(gain > 0 and g is not None and g["pass"])}}
        sel_in[n] = {"form": forms[n], "gain_per_1000": gain, "qualifies": bool(g is not None and g["pass"]),
                     "gate_ratio": g["ratio"] if g else None}
    sel = KR.select_form(sel_in)
    for n in CANDIDATES:
        cands[n]["qualifies"] = sel["candidates"][n]["qualifies"]
        cands[n]["tied_for_first"] = sel["candidates"][n]["tied_for_first"]
        cands[n]["tied_forms_nested_in_it"] = sel["candidates"][n]["tied_forms_nested_in_it"]
    old_qual = [n for n in CANDIDATES if cands[n]["old_rule"]["qualifies"]]
    old_winner = max(old_qual, key=lambda n: cands[n]["heldout_gain_vs_shipped_per_1000"]) if old_qual else None
    d = {"rule": "of the candidates that beat the shipped form by the margin and pass the gate, take the largest "
                 "gain; every qualifying candidate within the margin of it is tied for first; of those the "
                 "simplest ships (nesting first)",
         "candidates": cands, "qualifying": sel["qualifying"], "largest_gain": sel["largest_gain"],
         "tied_for_first": sel["tied_for_first"], "ships": sel["winner"], "settled_by": sel["settled_by"],
         "old_rule": {"rule": "of the candidates that improve held-out fit (> 0) over the shipped form and pass "
                              "the gate, the largest gain ships",
                      "qualifying": old_qual, "ships": old_winner},
         "phase3c_ships": "C1_cohorts_plus_shipped",
         "phase3c_qualifying": ["C1_cohorts_plus_shipped", "C3_both_plus_shipped"]}
    d["matches"] = bool(sel["winner"] == d["phase3c_ships"] and sorted(sel["qualifying"]) == sorted(d["phase3c_qualifying"]))
    d["old_rule"]["matches_phase3c"] = bool(old_winner == d["phase3c_ships"] and sorted(old_qual) == sorted(d["phase3c_qualifying"]))
    out["decisions"]["cohorts_edu_by_sex_both_phase3c_B3"] = d
    # 3. Phase 3c B2: the same-sex education term and whether the interaction rides — the decision
    #    recomputed from the stored LOMO record through samesex_decision (the stored heldout block
    #    was written under the old rule and is kept beside it)
    lomo = [x for x in json.loads((A2 / "lomo_samesex.json").read_text()) if x["sides"] > 0]
    fv = ssr["fit"]["face_validity"]
    face = {k: bool(fv[f"{k}_pass"]) for k in KR.COMPONENTS}
    ss = KR.samesex_decision(lomo, ssr["support"], face)
    d = {"rule": "the education term ships if a composition with it beats what m3.2.0 serves by the margin "
                 "(either interaction setting); the interaction rides only if the composition with it beats "
                 "the one without by the margin — a tie keeps the interaction off",
         "gain_per_1000_vs_served": ss["vs_m3_2_0_served"]["gain_per_1000_sides"],
         "phase3c_gain_per_1000_vs_served": ss3["vs_m3_2_0_served"]["gain_per_1000_sides"],
         "metros_better_than_served": ss["vs_m3_2_0_served"]["metros_better_than_served"],
         "education_term_improves_on_served": bool(ss["vs_m3_2_0_served"]["education_term_improves_on_served"]),
         "interaction_applies": bool(ss["interaction_applies"]),
         "interaction_margin_per_1000": ss["interaction_decision"]["margin_per_1000_sides"],
         "phase3c_interaction_margin_per_1000": ss3["interaction_decision"]["margin_per_1000_sides"],
         "components": ss["components"],
         "served_from_same_sex_couples": ss["served_from_same_sex_couples"],
         "phase3c_served_from_same_sex_couples": ss3["served_from_same_sex_couples"],
         "old_rule": {"education_term_improves_on_served": bool(ss_stored["vs_m3_2_0_served"]["education_term_improves_on_served"]),
                      "interaction_applies": bool(ss_stored["interaction_applies"]),
                      "served_from_same_sex_couples": ss_stored["served_from_same_sex_couples"],
                      "components": {k: v["ships"] for k, v in ss_stored["components"].items()}},
         "gate_shipped_form_with_same_sex_decision": gate(A2 / "gate_shipped.json")}
    d["matches"] = bool(d["education_term_improves_on_served"] == ss3["vs_m3_2_0_served"]["education_term_improves_on_served"]
                        and d["interaction_applies"] == ss3["interaction_applies"]
                        and d["served_from_same_sex_couples"] == ss3["served_from_same_sex_couples"])
    d["stored_old_rule_reading_agrees"] = bool(d["old_rule"]["interaction_applies"] == d["interaction_applies"]
                                               and d["old_rule"]["served_from_same_sex_couples"] == d["served_from_same_sex_couples"])
    out["decisions"]["same_sex_education_and_interaction_phase3c_B2"] = d
    out["all_verdicts_match"] = all(v["matches"] for v in out["decisions"].values())
    out["stop_condition_verdict_flipped"] = not out["all_verdicts_match"]
    out["old_rule_all_verdicts_match"] = bool(out["decisions"]["race_x_education_phase3b"]["old_rule"]["verdict_ships"]
                                              and out["decisions"]["cohorts_edu_by_sex_both_phase3c_B3"]["old_rule"]["matches_phase3c"]
                                              and out["decisions"]["same_sex_education_and_interaction_phase3c_B2"]["matches"])
    (OUT / "a2_decisions.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v["matches"] for k, v in out["decisions"].items()}), "all match:", out["all_verdicts_match"],
          "| old rule all match:", out["old_rule_all_verdicts_match"])
    b3 = out["decisions"]["cohorts_edu_by_sex_both_phase3c_B3"]
    print(json.dumps({n: {k: c[k] for k in ("heldout_gain_vs_shipped_per_1000", "beats_shipped", "qualifies", "tied_for_first")}
                      for n, c in b3["candidates"].items()}, indent=1))
    print("ships:", b3["ships"], "|", b3["settled_by"], "| old rule:", b3["old_rule"]["ships"])


if __name__ == "__main__":
    main()
