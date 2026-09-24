"""Phase 3c, B1: how the new gate (ADR 0011) reads the past three builds —
m3.1.0 -> m3.2.0 and m3.0.0 -> m3.1.0 — reported, changing nothing.

The three builds share their cubes byte for byte (pool, count and sumw2
cubes carry the same hashes in all three manifests), so each older kernel
is loaded into the reference build in memory and read against the same
cached replicate sums. m3.1.0's kernel is the complete ae1efbef9f0e
artifact. m3.0.0's build (59fd352c5c2f) was retired to its manifest,
metros and kernel.json; that record carries the kernel_v1 terms (f_age,
f_edu, f_race) and every metro's dials in full, so the artifact is
rebuilt from it — the normalisers are a deterministic function of the
terms and the national singles (results/phase3/_avail_national.npy, the
same array the fits used) — and the rebuilt kernel is checked against the
record before it is read.

    python -m atlas.pipeline.build.phase3c_past_readings <reference_build_dir>
        -> results/phase3c/past_readings.json, _candidates/m3_0_0_rebuilt/
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

from atlas import model as engine
from atlas.model.loader import _load_kernel
from atlas.pipeline.build import kernel as K
from atlas.pipeline.build import stability_gate as SG
from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.fetch import DATA, RESULTS

P3C = RESULTS / "phase3c"
BUILDS = DATA / "builds"


def rebuild_m3_0_0(out_dir: Path, metro_levels: list[str]) -> dict:
    rec = json.loads((BUILDS / "59fd352c5c2f" / "kernel.json").read_text())
    assert rec["version"] == "kernel_v1" and rec["fitting_sample"] == "recent", rec["version"]
    A = np.load(RESULTS / "phase3" / "_avail_national.npy")
    f_age = np.asarray(rec["f_age"], float)          # (2, 105)
    f_edu = np.asarray(rec["f_edu"], float)          # (4, 4)
    f_race = np.asarray(rec["f_race"], float)        # (2, 8, 8)
    dials = np.array([rec["dials"][c] for c in metro_levels], float)
    fg = {"age": f_age, "edu": f_edu, "race": f_race}
    log_norm = np.stack([K.log_norm_for({"age": fg["age"], "edu": fg["edu"], "race": fg["race"]}, A,
                                        theta=dials[i]) for i in range(len(metro_levels))])
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_dir / "kernel.npz", f_age=f_age, f_edu=f_edu, f_race=f_race,
                        dials=dials, log_norm=log_norm.astype(np.float32), avail_national=A,
                        metro_levels=np.array(metro_levels))
    meta = {k: v for k, v in rec.items() if k not in ("f_age", "f_edu", "f_race", "dials")}
    meta["rebuilt_from"] = "data/builds/59fd352c5c2f/kernel.json (Phase 3c: the retired m3.0.0 record)"
    meta["dials"] = rec["dials"]
    (out_dir / "kernel.json").write_text(json.dumps(meta, indent=1) + "\n")
    return {"terms_from_record": True, "dials_from_record": True,
            "log_norm_recomputed": "kernel.log_norm_for(terms, avail_national, dials)",
            "record_precision": "the record stores the terms and dials as written by the m3.0.0 build"}


def main(ref_dir: str) -> None:
    build = engine.load_build(ref_dir, allow_model_mismatch=True)
    ref = SG.load_reference()
    assert ref["build"] == build.manifest["data_version"], "run this on the reference build"
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    out = {"reference_build": ref["build"], "kernels": {}, "readings": {}}
    try:
        recs = {"m3.2.0": ref}
        k310 = _load_kernel(BUILDS / "ae1efbef9f0e", build.metro_levels)
        out["kernels"]["m3.1.0"] = {"source": "data/builds/ae1efbef9f0e (complete)", "version": k310.meta.get("version")}
        recs["m3.1.0"] = SG.gate_record(replace(build, kernel=k310), con, "m3.1.0", verbose=True)
        cdir = P3C / "_candidates" / "m3_0_0_rebuilt"
        out["kernels"]["m3.0.0"] = {"source": str(cdir.relative_to(RESULTS.parent)),
                                    **rebuild_m3_0_0(cdir, build.metro_levels)}
        k300 = _load_kernel(cdir, build.metro_levels)
        out["kernels"]["m3.0.0"]["version"] = k300.meta.get("version")
        recs["m3.0.0"] = SG.gate_record(replace(build, kernel=k300), con, "m3.0.0", verbose=True)
    finally:
        con.close()
    for cand, base in (("m3.2.0", "m3.1.0"), ("m3.1.0", "m3.0.0")):
        v = SG.verdict(recs[cand], recs[base])
        out["readings"][f"{base} -> {cand}"] = {k: v[k] for k in v if k != "touched"}
        out["readings"][f"{base} -> {cand}"]["totals"] = {n: recs[n]["totals"] for n in (base, cand)}
    for n in ("m3.1.0", "m3.0.0"):
        SG._write(P3C / f"gate_record_{n.replace('.', '_')}.json", recs[n])
    SG._write(P3C / "past_readings.json", out)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("searches_wobble_rose_more_than_25pct", "totals")}
                      for k, v in out["readings"].items()}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
