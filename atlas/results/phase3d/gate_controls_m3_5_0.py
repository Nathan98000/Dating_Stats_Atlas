"""Nathan's call after Phase 3d (ADR 0015): the ADR 0011 reference moves to
m3.5.0 (build 1ebeaa2dcad6). Reads the new reference record
(stability_gate.REFERENCE, written by `stability_gate reference`) and, on
the reference's own build:

- the two controls, through stability_gate.controls (the code Phase 3c's
  controls ran): the reference read against itself must read exactly 1.0
  and pass; with every replicate's deviation from the published estimate
  scaled by 1.5 it must fail;
- that the new record is the m3.5.0 build's own reading: search for
  search the same wobble and the same index and replicate hashes as B2's
  measurement of V2 (b2_gate_V2.json) and the ship's validation record
  (validation_report_m3_5_0.json);
- for the record, not as a gate, the past builds read against the new
  reference from their stored records (m3.2.0's Phase 3c reference
  record, m3.3.0's and m3.4.0's validation reports): each ratio and
  whether it would pass. Nothing past is re-judged;
- the headroom: where the gate's 10% line sat against m3.2.0 and where it
  sits now, both against m3.5.0's total.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/gate_controls_m3_5_0.py atlas/data/builds/1ebeaa2dcad6
        -> results/phase3d/gate_controls_m3_5_0.json  (exit 1 if a control fails)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from atlas.pipeline.build import stability_gate as SG
from atlas.pipeline.fetch import RESULTS

P3C, P3D = RESULTS / "phase3c", RESULTS / "phase3d"
OUT = P3D / "gate_controls_m3_5_0.json"
PAST = (("m3.2.0", SG.REFERENCE_M3_2_0), ("m3.3.0", P3C / "validation_report_m3_3_0.json"),
        ("m3.4.0", P3D / "validation_report_m3_4_0.json"))
SAME = (("b2_gate_V2", P3D / "b2_gate_V2.json"), ("validation_report_m3_5_0", P3D / "validation_report_m3_5_0.json"))


def rel(p: Path) -> str:
    return str(p.relative_to(RESULTS.parent))


def record(name: str, p: Path) -> dict:
    """A stored gate record, or a validation report's rank-stability block,
    in the shape stability_gate.verdict reads."""
    d = json.loads(p.read_text())
    searches = d["hard"]["rank_stability"]["per_search"] if "hard" in d else d["searches"]
    return {"name": name, "build": d["build"], "model_version": d["model_version"], "searches": searches}


def same_searches(a: dict, b: dict) -> dict:
    names = sorted(set(a["searches"]) | set(b["searches"]))
    keys = ("wobble", "index_hash", "replicate_hash", "skipped")
    differ = [n for n in names if any(a["searches"].get(n, {}).get(k) != b["searches"].get(n, {}).get(k) for k in keys)]
    return {"searches": len(names), "compared": list(keys), "differing": len(differ), "first_differing": differ[:5],
            "identical": not differ}


def main(build_dir: str) -> int:
    from atlas.pipeline.build.pool import open_pool
    ref = SG.load_reference()
    old = SG.load_reference(SG.REFERENCE_M3_2_0)
    build = SG._load(build_dir, None)
    m = build.manifest
    assert ref["build"] == m["data_version"] == "1ebeaa2dcad6", (ref["build"], m["data_version"])
    assert (ref["model_version"], ref["match_scoring"]) == (m["model_version"], m["normalization"]["match_scoring"]) \
        == ("m3.5.0", "V2"), (ref["model_version"], ref["match_scoring"])
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    try:
        ctl = SG.controls(build, con, ref)
    finally:
        con.close()
    past = {}
    for label, p in PAST:
        v = SG.verdict(record(label, p), ref)
        past[label] = {"record": rel(p), "build": v["candidate_build"],
                       **{k: v[k] for k in ("ratio", "pass", "basis", "searches_compared", "searches_touched",
                                             "wobble_candidate", "wobble_reference", "ratio_over_all_searches")},
                       "searches_wobble_rose_more_than_25pct": len(v["searches_wobble_rose_more_than_25pct"])}
    now = SG.verdict({"name": "m3.5.0", "build": ref["build"], "searches": ref["searches"]}, old)
    t_old, t_new = old["totals"]["wobble_sum"], ref["totals"]["wobble_sum"]
    line_old, line_new = (1 + SG.TOLERANCE) * t_old, (1 + SG.TOLERANCE) * t_new
    out = {"adr": "0015",
           "reference": {"record": rel(SG.REFERENCE), "build": ref["build"], "model_version": ref["model_version"],
                         "match_scoring": ref["match_scoring"], "totals": ref["totals"]},
           "replaces": {"record": rel(SG.REFERENCE_M3_2_0), "build": old["build"], "model_version": old["model_version"],
                        "totals": old["totals"], "note": "kept byte-identical as history, with results/phase3c/gate_controls.json"},
           "reproduces": {label: same_searches(ref, record(label, p)) for label, p in SAME},
           "reference_build": ctl["reference_build"], "identity": ctl["identity"], "enlarged_noise": ctl["enlarged_noise"],
           "both_controls_pass": ctl["both_controls_pass"],
           "past_builds": {"note": "for the record, not a gate: the past builds' stored records read against the "
                                   "new reference; nothing past is re-judged", **past},
           "headroom": {"tolerance": SG.TOLERANCE,
                        "m3.5.0_against_m3.2.0": {k: now[k] for k in ("ratio", "pass", "basis", "searches_touched",
                                                                       "wobble_candidate", "wobble_reference")},
                        "line_against_m3.2.0": round(line_old, 6),
                        "line_against_m3.2.0_over_m3.5.0_total": round(line_old / t_new, 6),
                        "line_against_m3.5.0": round(line_new, 6),
                        "line_against_m3.5.0_over_m3.5.0_total": round(line_new / t_new, 6)},
           "records": ctl["records"]}
    SG._write(OUT, out)
    print(json.dumps({k: v for k, v in out.items() if k != "records"}, indent=1))
    return 0 if out["both_controls_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
