"""Phase 3d B3 ship: m3.5.0 (build 1ebeaa2dcad6, its manifest refreshed
with match_scoring V2) must serve what B2 measured. Reads the chain's
records only:

- the served index is unchanged from m3.4.0 on the default search and the
  same-sex reference search (a scoring-only change; snapshot_m3_4_0.json
  against snapshot_m3_5_0.json), and the manifest names V2;
- the ADR 0011 gate on the build reads the same ratio and total as the B2
  measurement of V2 (b2_gate_V2.json; validation_report_m3_5_0.json);
- every test search whose wobble rose more than 25% from m3.4.0
  (validation_report_m3_4_0.json against validation_report_m3_5_0.json;
  findings, not gates), steadier / shakier / unchanged, the match-end
  searches;
- the hard gates, the old overlap reading, the latency and the load.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/b3_ship_check.py
        -> results/phase3d/b3_ship_check.json  (exit 1 if the index moved or the gate differs)
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from atlas.pipeline.fetch import DATA, RESULTS

P3D = RESULTS / "phase3d"


def load(p):
    return json.loads(p.read_text())


def main() -> int:
    a, b = load(P3D / "snapshot_m3_4_0.json"), load(P3D / "snapshot_m3_5_0.json")
    out = {"build_m3_4_0": a["build"], "build_m3_5_0": b["build"], "model_version": b["model_version"], "searches": {}}
    ok = True
    for key in ("default", "same_sex_man_31"):
        ra = {r["cbsa"]: r for r in (a["default"] if key == "default" else a["reference"][key])["rows"]}
        rb = {r["cbsa"]: r for r in (b["default"] if key == "default" else b["reference"][key])["rows"]}
        same_set = set(ra) == set(rb)
        idx = max(abs(ra[c]["index"] - rb[c]["index"]) for c in ra if c in rb)
        moe = max(abs(ra[c]["moe"] - rb[c]["moe"]) for c in ra if c in rb)
        disp = sum(1 for c in ra if c in rb and ra[c]["display"] != rb[c]["display"])
        band = sum(1 for c in ra if c in rb and ra[c]["band"] != rb[c]["band"])
        out["searches"][key] = {"metros": len(rb), "same_metro_set": same_set, "index_max_abs_diff": idx,
                               "moe_max_abs_diff": moe, "displays_changed": disp, "bands_changed": band,
                               "ranks_changed": sum(1 for c in ra if c in rb and ra[c]["rank"] != rb[c]["rank"])}
        ok = ok and same_set and idx == 0 and moe == 0 and disp == 0 and band == 0
    manifest = load(DATA / "builds" / b["build"] / "manifest.json")
    out["manifest"] = {"model_version": manifest["model_version"], "normalization": manifest["normalization"]}
    ok = ok and manifest["normalization"]["match_scoring"] == "V2" and manifest["model_version"] == "m3.5.0"
    v5 = load(P3D / "validation_report_m3_5_0.json")
    rs = v5["hard"]["rank_stability"]
    g2 = load(P3D / "b2_gate_V2.json")
    out["gate"] = {"built_ratio": rs["ratio"], "b2_ratio": g2["verdict"]["ratio"], "same_ratio": abs(rs["ratio"] - g2["verdict"]["ratio"]) < 1e-6,
                   "built_total": rs["wobble_candidate"], "b2_total": g2["totals"]["wobble_sum"],
                   "same_total": abs(rs["wobble_candidate"] - g2["totals"]["wobble_sum"]) < 1e-6,
                   "built_pass": rs["pass"], "wobble_reference": rs["wobble_reference"], "searches_touched": rs["searches_touched"],
                   "basis": rs["basis"], "rose_more_than_25pct_vs_reference": len(rs["searches_wobble_rose_more_than_25pct"]),
                   "totals": rs["totals"],
                   "old_rule_min_share_personas": v5["soft"]["rank_stability_overlap_old_rule"]["min_share_personas"],
                   "old_rule_would_pass_at_0_80": v5["soft"]["rank_stability_overlap_old_rule"]["would_pass_at_0_80"],
                   "old_rule_personas_below_0_9": {k: x for k, x in v5["soft"]["rank_stability_overlap_old_rule"]["per_persona"].items() if x < 0.9}}
    ok = ok and out["gate"]["same_ratio"] and out["gate"]["same_total"] and rs["pass"]
    out["hard_gates"] = {k: bool(v.get("pass")) for k, v in v5["hard"].items()}
    out["hard_failures"] = v5["hard_failures"]
    ok = ok and not v5["hard_failures"]
    out["weight_sensitivity_tau"] = v5["soft"]["weight_sensitivity"]["kendall_tau"]
    v4 = load(P3D / "validation_report_m3_4_0.json")
    p4 = {n: r for n, r in v4["hard"]["rank_stability"]["per_search"].items() if "skipped" not in r}
    p5 = {n: r for n, r in rs["per_search"].items() if "skipped" not in r}
    common = [n for n in p5 if n in p4]
    rises = [{"search": n, "m3_4_0": p4[n]["wobble"], "m3_5_0": p5[n]["wobble"]}
             for n in common if p5[n]["wobble"] > 1.25 * p4[n]["wobble"] and p5[n]["wobble"] > p4[n]["wobble"]]
    rises.sort(key=lambda r: -(r["m3_5_0"] - r["m3_4_0"]))
    out["wobble_vs_m3_4_0"] = {
        "searches": len(common),
        "total_m3_4_0": round(sum(p4[n]["wobble"] for n in common), 3),
        "total_m3_5_0": round(sum(p5[n]["wobble"] for n in common), 3),
        "steadier": sum(1 for n in common if p5[n]["wobble"] < p4[n]["wobble"]),
        "shakier": sum(1 for n in common if p5[n]["wobble"] > p4[n]["wobble"]),
        "unchanged": sum(1 for n in common if p5[n]["wobble"] == p4[n]["wobble"]),
        "rose_more_than_25pct": rises,
        "rose_more_than_25pct_same_sex": sum(1 for r in rises if r["search"].startswith("samesex:")),
        "match_end_searches": {n: [p4[n]["wobble"], p5[n]["wobble"]] for n in common if n.startswith("persona:slider")},
        "max_wobble_m3_5_0": max(p5[n]["wobble"] for n in common),
        "max_wobble_search_m3_5_0": max(common, key=lambda n: p5[n]["wobble"]),
        "median_wobble_m3_4_0": v4["hard"]["rank_stability"]["totals"]["wobble_median"],
        "median_wobble_m3_5_0": rs["totals"]["wobble_median"],
        "index_hashes_unchanged": all(p4[n]["index_hash"] == p5[n]["index_hash"] and p4[n]["replicate_hash"] == p5[n]["replicate_hash"] for n in common)}
    lat_p = P3D / "latency_m3_5_0.json"
    out["latency"] = load(lat_p) if lat_p.exists() else None
    log_p = P3D / "ship_m3_5_0_run.log"
    if log_p.exists():
        log = log_p.read_text()
        out["pytest_line"] = next((ln for ln in log.splitlines() if "passed" in ln), None)
        out["load_at_latency"] = next((ln.split(":", 1)[1].strip() for ln in log.splitlines() if ln.startswith("load at measurement")), None)
    out["all_as_measured"] = bool(ok)
    (P3D / "b3_ship_check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("wobble_vs_m3_4_0",)}, indent=1))
    w = out["wobble_vs_m3_4_0"]
    print("wobble vs m3.4.0:", json.dumps({k: v for k, v in w.items() if k != "rose_more_than_25pct"}))
    print(f"rose >25% ({len(w['rose_more_than_25pct'])}):", json.dumps(w["rose_more_than_25pct"]))
    if not ok:
        print("STOP: the build does not serve what was measured", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
