"""Phase 3d A2 ship: the built m3.4.0 must serve what was measured in
memory. Reads the ship chain's records only:

- the same ranks as the in-memory C1 candidate on the default search and
  on the same-sex reference search (snapshot_m3_4_0.json against
  snapshot_m3_4_0_candidate_C1.json, row by row), the same top ten;
- the same ADR 0011 gate ratio as speedup/a2/gate_C1_cohorts_plus_shipped.json
  (validation_report_m3_4_0.json's rank_stability);
- every test search whose wobble rose more than 25% from m3.3.0
  (validation_report_m3_3_0.json against validation_report_m3_4_0.json,
  per search; findings, not gates), steadier / shakier / unchanged counts,
  the match-end searches;
- the hard gates, the latency reading and the load average, for the report.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/a2_ship_check.py
        -> results/phase3d/a2_ship_check.json  (exit 1 if a rank or the gate ratio differs)
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from atlas.pipeline.fetch import RESULTS

P3C, P3D = RESULTS / "phase3c", RESULTS / "phase3d"
A2 = P3D / "speedup" / "a2"


def load(p):
    return json.loads(p.read_text())


def ranks(snap: dict, key: str) -> dict:
    block = snap["default"] if key == "default" else snap["reference"][key]
    return {r["cbsa"]: (r["rank"], r["metro"]) for r in block["rows"]}


def main() -> int:
    built = load(P3D / "snapshot_m3_4_0.json")
    cand = load(P3D / "snapshot_m3_4_0_candidate_C1.json")
    out = {"built": built["build"], "model_version": built["model_version"], "candidate": cand["build"], "searches": {}}
    ok = True
    for key in ("default", "same_sex_man_31"):
        rb, rc = ranks(built, key), ranks(cand, key)
        same_set = set(rb) == set(rc)
        differing = [{"cbsa": c, "metro": rb[c][1], "built": rb[c][0], "candidate": rc[c][0]}
                     for c in rb if c in rc and rb[c][0] != rc[c][0]]
        top_b = [rb[c][1] for c in sorted(rb, key=lambda c: rb[c][0])[:10]]
        top_c = [rc[c][1] for c in sorted(rc, key=lambda c: rc[c][0])[:10]]
        out["searches"][key] = {"metros": len(rb), "same_metro_set": same_set, "ranks_differing": differing,
                               "top10_built": top_b, "top10_candidate": top_c, "top10_same": top_b == top_c,
                               "index_max_abs_diff": max(abs(a["index"] - b["index"]) for a, b in zip(
                                   sorted((built["default"] if key == "default" else built["reference"][key])["rows"], key=lambda r: r["cbsa"]),
                                   sorted((cand["default"] if key == "default" else cand["reference"][key])["rows"], key=lambda r: r["cbsa"])))}
        ok = ok and same_set and not differing and top_b == top_c
    # the gate ratio
    v4 = load(P3D / "validation_report_m3_4_0.json")
    g_mem = load(A2 / "gate_C1_cohorts_plus_shipped.json")["verdict"]
    rs = v4["hard"]["rank_stability"]
    out["gate"] = {"built_ratio": rs["ratio"], "in_memory_ratio": g_mem["ratio"], "same_ratio": abs(rs["ratio"] - g_mem["ratio"]) < 1e-6,
                   "built_pass": rs["pass"], "wobble_candidate": rs["wobble_candidate"], "wobble_reference": rs["wobble_reference"],
                   "searches_touched": rs["searches_touched"], "basis": rs["basis"],
                   "rose_more_than_25pct_vs_reference": len(rs["searches_wobble_rose_more_than_25pct"]),
                   "old_rule_min_share_personas": v4["soft"]["rank_stability_overlap_old_rule"]["min_share_personas"],
                   "old_rule_would_pass_at_0_80": v4["soft"]["rank_stability_overlap_old_rule"]["would_pass_at_0_80"]}
    ok = ok and out["gate"]["same_ratio"] and rs["pass"]
    # hard gates
    out["hard_gates"] = {k: bool(v.get("pass")) for k, v in v4["hard"].items()}
    out["hard_failures"] = v4["hard_failures"]
    ok = ok and not v4["hard_failures"]
    # wobble against m3.3.0, per search (findings)
    v3 = load(P3C / "validation_report_m3_3_0.json")
    p3 = {n: r for n, r in v3["hard"]["rank_stability"]["per_search"].items() if "skipped" not in r}
    p4 = {n: r for n, r in rs["per_search"].items() if "skipped" not in r}
    common = [n for n in p4 if n in p3]
    rises = [{"search": n, "m3_3_0": p3[n]["wobble"], "m3_4_0": p4[n]["wobble"]}
             for n in common if p4[n]["wobble"] > 1.25 * p3[n]["wobble"] and p4[n]["wobble"] > p3[n]["wobble"]]
    rises.sort(key=lambda r: -(r["m3_4_0"] - r["m3_3_0"]))
    out["wobble_vs_m3_3_0"] = {
        "searches": len(common),
        "total_m3_3_0": round(sum(p3[n]["wobble"] for n in common), 3),
        "total_m3_4_0": round(sum(p4[n]["wobble"] for n in common), 3),
        "steadier": sum(1 for n in common if p4[n]["wobble"] < p3[n]["wobble"]),
        "shakier": sum(1 for n in common if p4[n]["wobble"] > p3[n]["wobble"]),
        "unchanged": sum(1 for n in common if p4[n]["wobble"] == p3[n]["wobble"]),
        "rose_more_than_25pct": rises,
        "match_end_searches": {n: [p3[n]["wobble"], p4[n]["wobble"]] for n in common if n.startswith("persona:slider")},
        "max_wobble_m3_4_0": max(p4[n]["wobble"] for n in common),
        "median_wobble_m3_3_0": v3["hard"]["rank_stability"]["totals"]["wobble_median"],
        "median_wobble_m3_4_0": rs["totals"]["wobble_median"]}
    # latency
    lat = load(P3D / "latency_m3_4_0.json")
    out["latency"] = lat
    # tests and the rest of the chain, from the log
    log = (P3D / "ship_m3_4_0_run.log").read_text()
    out["pytest_line"] = next((ln for ln in log.splitlines() if "passed" in ln), None)
    out["all_as_measured"] = bool(ok)
    (P3D / "a2_ship_check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("wobble_vs_m3_3_0", "latency")}, indent=1))
    print("wobble vs m3.3.0:", json.dumps({k: v for k, v in out["wobble_vs_m3_3_0"].items() if k != "rose_more_than_25pct"}))
    print("rose >25%:", json.dumps(out["wobble_vs_m3_3_0"]["rose_more_than_25pct"], indent=1))
    print("latency:", json.dumps({k: lat[k] for k in lat if k != "queries"} if isinstance(lat, dict) else lat)[:800])
    if not ok:
        print("STOP: the build does not serve what was measured", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
