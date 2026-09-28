"""Nathan's decision 5 (ADR 0018): at the m4.0.0 ship the ADR 0011 gate is
read against the m3.5.0 reference and recorded as a finding (it does not
block this phase's changes; gate_m4_0_0_vs_m3_5_0.json), and the reference
then moves to m4.0.0 (build 5b780e4f2444). Reads the new reference record
(stability_gate.REFERENCE, written by `stability_gate reference`) and, on
the reference's own build:

- the two controls, through stability_gate.controls (the code ADR 0011's
  and ADR 0015's controls ran): the reference read against itself must
  read exactly 1.0 and pass; with every replicate's deviation from the
  published estimate scaled by 1.5 it must fail;
- that the new record is the m4.0.0 build's own reading: search for search
  the same wobble and the same index and replicate hashes as the ship's
  reading against m3.5.0 (gate_m4_0_0_vs_m3_5_0.json) and its validation
  record (validation_report_m4_0_0.json, when present);
- for the record, not as a gate: m3.5.0's and m3.6.0's stored records read
  against the new reference. Nothing past is re-judged.

    PYTHONPATH=. .venv/bin/python atlas/results/phase4/gate_controls_m4_0_0.py atlas/data/builds/5b780e4f2444
        -> results/phase4/gate_controls_m4_0_0.json  (exit 1 if a control fails)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from atlas.pipeline.build import stability_gate as SG
from atlas.pipeline.fetch import RESULTS

P3D, P4 = RESULTS / "phase3d", RESULTS / "phase4"
OUT = P4 / "gate_controls_m4_0_0.json"
PAST = (("m3.5.0", SG.REFERENCE_M3_5_0), ("m3.6.0", P4 / "validation_report_m3_6_0.json"))
SAME = (("gate_m4_0_0_vs_m3_5_0", P4 / "gate_m4_0_0_vs_m3_5_0.json"),
        ("validation_report_m4_0_0", P4 / "validation_report_m4_0_0.json"))


def rel(p: Path) -> str:
    return str(p.relative_to(RESULTS.parent))


def record(name: str, p: Path) -> dict:
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
    old = SG.load_reference(SG.REFERENCE_M3_5_0)
    build = SG._load(build_dir, None)
    m = build.manifest
    assert ref["build"] == m["data_version"] == "5b780e4f2444", (ref["build"], m["data_version"])
    assert (ref["model_version"], ref["match_scoring"]) == (m["model_version"], m["normalization"]["match_scoring"]) \
        == ("m4.0.0", "V2"), (ref["model_version"], ref["match_scoring"])
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
    out = {"adr": "0018",
           "reference": {"record": rel(SG.REFERENCE), "build": ref["build"], "model_version": ref["model_version"],
                         "match_scoring": ref["match_scoring"], "totals": ref["totals"]},
           "replaces": {"record": rel(SG.REFERENCE_M3_5_0), "build": old["build"], "model_version": old["model_version"],
                        "totals": old["totals"],
                        "note": "kept byte-identical as history, with results/phase3d/gate_controls_m3_5_0.json"},
           "reproduces": {label: same_searches(ref, record(label, p)) for label, p in SAME if p.exists()},
           "reference_build": ctl["reference_build"], "identity": ctl["identity"], "enlarged_noise": ctl["enlarged_noise"],
           "both_controls_pass": ctl["both_controls_pass"],
           "past_builds": {"note": "for the record, not a gate: the past builds' stored records read against the "
                                   "new reference; nothing past is re-judged", **past},
           "records": ctl["records"]}
    SG._write(OUT, out)
    print(json.dumps({k: v for k, v in out.items() if k != "records"}, indent=1))
    return 0 if out["both_controls_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
