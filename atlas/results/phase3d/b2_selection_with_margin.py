"""Nathan's call after Phase 3d (ADR 0013, amended): the match-end margin,
applied to the stored B2 records — no candidate is re-measured.

Reads results/phase3d/b2_candidates.json (match_scoring_candidates on
m3.4.0, run after 4bab576 under the rule as drafted) and passes its
per-candidate records through match_scoring_candidates.select, the
function main calls, with MATCH_END_MARGIN. Writes the margin as a
fraction and in places of N0's match-end total, each candidate's
match-end reduction against N0, the qualifying set, the tie band and what
ships, and beside it the drafted rule's reading as B2 stored it. Also the
anchors the amendment gives for 5%, read from the stored gate records:
what changes that leave the scoring alone moved (finishing the fit,
m3.3.0 -> m3.4.0, on the gate-set total and on the two match-end
searches; the C1 and C3 candidates' gate-set totals), the gate's own
line, and the match-end rise Part B was meant to undo (m3.2.0 -> m3.3.0).

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/b2_selection_with_margin.py
        -> results/phase3d/b2_selection_with_margin.json  (exit 1 unless qualifying [V2], ships V2)
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from atlas.pipeline.build import match_scoring_candidates as MSC
from atlas.pipeline.build import stability_gate as SG
from atlas.pipeline.fetch import RESULTS

P3C, P3D = RESULTS / "phase3c", RESULTS / "phase3d"
A2 = P3D / "speedup" / "a2"
SRC = P3D / "b2_candidates.json"
OUT = P3D / "b2_selection_with_margin.json"
MATCH_END_SEARCHES = ("persona:slider_all_match", "persona:slider_alias_pool_vs_balance")
EXPECTED = {"qualifying": ["V2"], "ships": "V2"}


def rel(p: Path) -> str:
    return str(p.relative_to(RESULTS.parent))


def searches(p: Path) -> dict:
    """A gate record's per-search readings: a gate record's own, or a
    validation report's rank-stability block."""
    d = json.loads(p.read_text())
    return d["hard"]["rank_stability"]["per_search"] if "hard" in d else d["searches"]


def total(p: Path) -> float:
    return sum(r["wobble"] for r in searches(p).values() if "skipped" not in r)


def match_end(p: Path) -> float:
    s = searches(p)
    w = {s[n]["wobble"] for n in MATCH_END_SEARCHES}
    assert len(w) == 1, f"the two match-end searches read differently in {p}"
    return w.pop()


def anchors(margin: float) -> dict:
    m320, m330 = P3C / "stability_reference.json", P3C / "validation_report_m3_3_0.json"
    m340 = P3D / "validation_report_m3_4_0.json"
    c1, c3 = A2 / "gate_C1_cohorts_plus_shipped.json", A2 / "gate_C3_both_plus_shipped.json"
    g330, g340, e320, e330, e340 = total(m330), total(m340), match_end(m320), match_end(m330), match_end(m340)
    gc1, gc3 = total(c1), total(c3)
    rise = e330 / e320 - 1
    return {
        "ordinary_movement": {
            "finishing_the_fit_gate_set_total": {"m3.3.0": round(g330, 6), "m3.4.0": round(g340, 6),
                                                 "change_fraction": round(g340 / g330 - 1, 6),
                                                 "records": [rel(m330), rel(m340)]},
            "finishing_the_fit_match_end_searches": {"searches": list(MATCH_END_SEARCHES), "m3.3.0": e330, "m3.4.0": e340,
                                                     "change_fraction": round(e340 / e330 - 1, 6),
                                                     "records": [rel(m330), rel(m340)]},
            "C1_against_C3_gate_set_total": {"C1": round(gc1, 6), "C3": round(gc3, 6),
                                             "difference_fraction_of_C1": round(gc3 / gc1 - 1, 6),
                                             "records": [rel(c1), rel(c3)]},
            "margin_over_largest": round(margin / max(abs(g340 / g330 - 1), abs(e340 / e330 - 1), abs(gc3 / gc1 - 1)), 2)},
        "gate_line": {"tolerance": SG.TOLERANCE, "margin_over_line": round(margin / SG.TOLERANCE, 6)},
        "match_end_rise_part_b_answers": {"searches": list(MATCH_END_SEARCHES), "m3.2.0": e320, "m3.3.0": e330,
                                          "rise_fraction": round(rise, 6), "margin_over_rise": round(margin / rise, 4),
                                          "records": [rel(m320), rel(m330)]}}


def main() -> int:
    raw = SRC.read_bytes()
    b2 = json.loads(raw)
    sel = MSC.select(b2["rules"])
    drafted = {"commit": "4bab576", "rule": b2["selection_rule"], "qualifying": b2["qualifying"], "ships": b2["ships"],
               "candidates": {rule: {"lower_match_end_wobble_than_N0": r["lower_match_end_wobble_than_N0"],
                                     "qualifies": r["qualifies"]} for rule, r in b2["rules"].items()}}
    out = {"source": {"file": rel(SRC), "sha256": hashlib.sha256(raw).hexdigest(), "build": b2["build"],
                      "model_version": b2["model_version"], "reference_build": b2["reference_build"],
                      "note": "the stored B2 records, read; no candidate re-measured"},
           "adr": "0013, amended after Phase 3d: the match-end margin",
           "margin": {"fraction": sel["margin_fraction"], "places": round(sel["margin_places"], 6),
                      "of": "N0's total wobble over the match-end set", "N0_match_end_total": sel["N0_match_end_total"]},
           "candidates": {rule: {**c, "match_end_reduction_vs_N0_places": round(c["match_end_reduction_vs_N0_places"], 6),
                                 "match_end_reduction_vs_N0_fraction": round(c["match_end_reduction_vs_N0_fraction"], 6),
                                 "outlier_condition_worst_spread": min(
                                     b2["rules"][rule]["outlier_condition"][s]["min_spread"] for s in ("own_slider", "match_end")),
                                 "drafted_rule": drafted["candidates"][rule]}
                          for rule, c in sel["candidates"].items()},
           "amended_rule": {"qualifying": sel["qualifying"], "lowest_match_end": sel["lowest_match_end"],
                            "tie_band": sel["tie_band"], "tied_for_first": sel["tied_for_first"],
                            "ships": sel["ships"], "settled_by": sel["settled_by"]},
           "drafted_rule": drafted,
           "same_outcome_as_drafted": bool(sel["qualifying"] == b2["qualifying"] and sel["ships"] == b2["ships"]),
           "anchors": anchors(sel["margin_fraction"]),
           "expected": EXPECTED}
    out["matches_expected"] = bool(sel["qualifying"] == EXPECTED["qualifying"] and sel["ships"] == EXPECTED["ships"])
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"margin": out["margin"], "amended_rule": out["amended_rule"],
                      "reductions": {r: c["match_end_reduction_vs_N0_fraction"] for r, c in out["candidates"].items()},
                      "drafted": {"qualifying": drafted["qualifying"], "ships": drafted["ships"]},
                      "matches_expected": out["matches_expected"]}, indent=1))
    return 0 if out["matches_expected"] else 1


if __name__ == "__main__":
    sys.exit(main())
