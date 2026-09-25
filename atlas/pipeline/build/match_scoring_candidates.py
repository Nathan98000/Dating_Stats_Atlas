"""Phase 3d B2 (ADR 0013): measure the four match-scoring candidates on
one build — the rule is committed before this runs and nothing here is
tuned to its results.

For each of N0, V1, V2 and V3 (the build's manifest switched in memory,
nothing on disk changes):

- the ADR 0011 gate's verdict and ratio against the m3.2.0 reference (a
  scoring-only change touches no index, so the totals run over every
  search, as the rule says);
- total wobble over the gate's own set and over the MATCH-END set (every
  ADR 0011 test search without explicit weights, re-sent with
  pool_vs_match = 1.0);
- the outlier condition: on every search of both sets the middle 80% of
  ranked cities keep at least OUTLIER_MIN_SPREAD points of match-score
  spread (10th to 90th percentile of the feature's normalised value);
  the worst searches are named;
- how much matching still steers: Kendall's tau between each search's
  ranking and its match-index order, at the searches' own slider
  positions and at the match end (reported, not gated);
- the disclosed reference searches' top city and top five.

Then the selection rule: a candidate qualifies if it passes the gate,
meets the outlier condition and wobbles less than N0 over the match-end
set; of those, the lowest match-end total ships, ties to the earlier
candidate; none qualifying ships nothing.

    python -m atlas.pipeline.build.match_scoring_candidates <build_dir> [--rules N0,V1,V2,V3] [--out results/phase3d]
        -> <out>/b2_candidates.json, <out>/b2_gate_<rule>.json, <out>/b2_matchend_<rule>.json
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from atlas import model as engine
from atlas.pipeline.build import stability_gate as SG
from atlas.pipeline.build.phase3b_snapshot import DEFAULT, REFERENCE
from atlas.pipeline.fetch import RESULTS

RULES = ("N0", "V1", "V2", "V3")
OUTLIER_MIN_SPREAD = 40.0          # points of match-score spread, p10 to p90, half of what a percentile rank gives
WORST_N = 5
DISCLOSED = ("grad_asian_woman_30", "grad_asian_man_34", "black_woman_30", "nhpi_man_35", "nhpi_woman_35")


def with_rule(build, rule: str):
    m = json.loads(json.dumps(build.manifest))
    block = dict(m.get("normalization") or {})
    assert block, "the build must carry the registry's normalization block (ADR 0013)"
    block["match_scoring"] = rule
    m["normalization"] = block
    return replace(build, manifest=m)


def match_end_searches() -> list[tuple[str, dict]]:
    """Every ADR 0011 test search that does not send explicit weights,
    re-sent with pool_vs_match = 1.0 (the deprecated pool_vs_balance alias
    is replaced, since the two controls cannot both be sent)."""
    out = []
    for name, body in SG.test_searches():
        if "weights" in body:
            continue
        b = {k: v for k, v in body.items() if k != "pool_vs_balance"}
        b["pool_vs_match"] = 1.0
        out.append((name, b))
    return out


def outlier_reading(rec: dict) -> dict:
    live = {n: r for n, r in rec["searches"].items() if "skipped" not in r and r.get("match_score_spread_p10_p90") is not None}
    worst = sorted(live.items(), key=lambda kv: kv[1]["match_score_spread_p10_p90"])[:WORST_N]
    fails = [n for n, r in live.items() if r["match_score_spread_p10_p90"] < OUTLIER_MIN_SPREAD]
    return {"searches": len(live), "min_spread": min(r["match_score_spread_p10_p90"] for r in live.values()),
            "median_spread": float(np.median([r["match_score_spread_p10_p90"] for r in live.values()])),
            "searches_below_min": len(fails), "passes": len(fails) == 0,
            "worst": [{"search": n, "spread": r["match_score_spread_p10_p90"]} for n, r in worst]}


def steering(rec: dict) -> dict:
    taus = [r["steering_tau"] for r in rec["searches"].values() if "skipped" not in r and r.get("steering_tau") is not None]
    return {"searches": len(taus), "tau_median": float(np.median(taus)), "tau_p10": float(np.percentile(taus, 10)),
            "tau_p90": float(np.percentile(taus, 90)), "tau_min": float(min(taus))}


def tops(build, rule: str) -> dict:
    out = {}
    for name in DISCLOSED:
        body = REFERENCE[name]
        res = engine.rank(with_rule(build, rule), engine.parse_request(body))
        end = engine.rank(with_rule(build, rule), engine.parse_request({**body, "pool_vs_match": 1.0}))
        out[name] = {"top": res["ranked"][0]["display_name"],
                     "top5": [r["display_name"] for r in res["ranked"][:5]],
                     "top5_index": [r["match"]["display"] for r in res["ranked"][:5]],
                     "match_end_top": end["ranked"][0]["display_name"],
                     "match_end_top5": [r["display_name"] for r in end["ranked"][:5]]}
    return out


def main(argv: list[str]) -> int:
    from atlas.pipeline.build.pool import open_pool
    build_dir = argv[0]
    opt = {argv[i]: argv[i + 1] for i in range(1, len(argv) - 1, 2) if argv[i].startswith("--")}
    rules = tuple(opt.get("--rules", ",".join(RULES)).split(","))
    out_dir = Path(opt.get("--out", RESULTS / "phase3d"))
    out_dir.mkdir(parents=True, exist_ok=True)
    build = engine.load_build(build_dir, allow_model_mismatch=True)
    ref = SG.load_reference()
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    end_set = match_end_searches()
    t0 = time.time()
    out = {"build": build.manifest["data_version"], "model_version": engine.MODEL_VERSION,
           "kernel": (build.kernel.meta or {}).get("generated_at"),
           "reference_build": ref["build"], "rules": {}, "outlier_min_spread": OUTLIER_MIN_SPREAD,
           "match_end_set": {"searches": len(end_set),
                             "definition": "every ADR 0011 test search without explicit weights, pool_vs_match = 1.0"},
           "selection_rule": "qualifies if: gate pass; outlier condition on both sets; match-end total below N0's. "
                             "Lowest match-end total ships; ties to the earlier candidate; none -> nothing ships."}
    try:
        for rule in rules:
            b = with_rule(build, rule)
            gate = SG.gate_record(b, con, name=f"b2:{rule}", verbose=False)
            gate["verdict"] = SG.verdict(gate, ref)
            SG._write(out_dir / f"b2_gate_{rule}.json", gate)
            end = SG.gate_record(b, con, name=f"b2:{rule}:match_end", searches=end_set, verbose=False)
            SG._write(out_dir / f"b2_matchend_{rule}.json", end)
            v = gate["verdict"]
            out["rules"][rule] = {
                "gate": {k: v[k] for k in ("pass", "ratio", "basis", "searches_touched", "wobble_candidate",
                                           "wobble_reference", "ratio_over_all_searches")},
                "gate_old_rule_min_share_personas": v["old_rule"]["min_share_personas"],
                "gate_set_wobble_total": gate["totals"]["wobble_sum"],
                "gate_set_wobble_median": gate["totals"]["wobble_median"],
                "match_end_wobble_total": end["totals"]["wobble_sum"],
                "match_end_wobble_median": end["totals"]["wobble_median"],
                "match_end_wobble_max": end["totals"]["wobble_max"],
                "outlier_condition": {"own_slider": outlier_reading(gate), "match_end": outlier_reading(end)},
                "steering_tau": {"own_slider": steering(gate), "match_end": steering(end)},
                "disclosed_searches": tops(build, rule),
                "seconds": round(time.time() - t0, 1)}
            r = out["rules"][rule]
            r["outlier_condition"]["passes"] = bool(r["outlier_condition"]["own_slider"]["passes"]
                                                    and r["outlier_condition"]["match_end"]["passes"])
            print(json.dumps({"rule": rule, "gate": r["gate"]["pass"], "ratio": r["gate"]["ratio"],
                              "match_end": r["match_end_wobble_total"], "gate_set": r["gate_set_wobble_total"],
                              "outlier": r["outlier_condition"]["passes"],
                              "min_spread": [r["outlier_condition"]["own_slider"]["min_spread"],
                                             r["outlier_condition"]["match_end"]["min_spread"]],
                              "tau_median": [r["steering_tau"]["own_slider"]["tau_median"],
                                             r["steering_tau"]["match_end"]["tau_median"]]}), flush=True)
    finally:
        con.close()
    n0 = out["rules"].get("N0")
    for rule, r in out["rules"].items():
        r["lower_match_end_wobble_than_N0"] = (bool(r["match_end_wobble_total"] < n0["match_end_wobble_total"])
                                               if n0 and rule != "N0" else False)
        r["qualifies"] = bool(rule != "N0" and r["gate"]["pass"] and r["outlier_condition"]["passes"]
                              and r["lower_match_end_wobble_than_N0"])
    qual = [rule for rule in rules if out["rules"][rule]["qualifies"]]
    winner = None
    if qual:
        best = min(out["rules"][r]["match_end_wobble_total"] for r in qual)
        winner = next(r for r in rules if r in qual and out["rules"][r]["match_end_wobble_total"] == best)
    out["qualifying"] = qual
    out["ships"] = winner
    out["seconds"] = round(time.time() - t0, 1)
    (out_dir / "b2_candidates.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    print(json.dumps({"qualifying": qual, "ships": winner, "seconds": out["seconds"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
