"""Phase 3b, A1: choose the kernel's fitting sample by the standing
rank-stability gate, shortest half-life first.

For each candidate sample (recent = the m3.0.0 baseline that failed; then
decay_h5, decay_h10, decay_h20 in that order) the national kernel is
refitted (kernel.candidate_artifact: the Phase 3 bandwidth, the Phase 3
shrunk dials), loaded into the CURRENT build in memory in place of the
shipped kernel — the cubes are what they are; only the kernel changes —
and the validation suite's own rank_stability() runs over all eighteen
personas. The first candidate on which every persona reaches 0.80 ships;
the sweep stops there (the stated rule) unless --all is given. Nothing
about the gate is touched.

Per candidate the record carries: the eighteen stability shares, the
index's replicate sd at the median and p90 (the root-cause metric), the
p10-p90 spread and the score bunching at the top-10 boundary; and from
the Phase 3 kernel report the sample's effective couple-sides (Kish and
allocated) and its race cells that are empty or under 30 effective
sides. The Pew number is NOT read here: it is not the selection
criterion (the sweep is confounded with Pew's period, PHASE3.md).

    python -m atlas.pipeline.build.stability_sweep <build_dir> [--all]
        -> results/phase3b/stability_sweep.json, stability_sweep.csv,
           candidates under results/phase3b/_candidates/<sample>/
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace

import numpy as np
import pandas as pd

from atlas import model as engine
from atlas.model.loader import _load_kernel
from atlas.model.tests.golden.make_fixture import GOLDEN_VECTORS
from atlas.pipeline.build import kernel as K
from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.build.validate import (STABILITY_SHARE, rank_stability,
                                           run_personas)
from atlas.pipeline.fetch import RESULTS

P3B = RESULTS / "phase3b"
CANDIDATES = ["recent", "decay_h5", "decay_h10", "decay_h20"]


def sample_facts(report: dict, sample: str) -> dict:
    s = report["samples"][sample]
    race = s["margins"]["race_8x8_by_sex"]
    return {"half_life_years": (None if sample == "recent"
                                else float(sample[len("decay_h"):])),
            "spec": s["spec"],
            "couple_sides_allocated": s["n_alloc"],
            "couple_sides_kish": s["n_kish"],
            "couple_sides_weighted": s["couple_sides_weighted"],
            "race_cells_empty": s["race_cells_empty"],
            "race_cells_below_30_effective": race["cells_below_30_effective"],
            "race_cells_floored": s["floored_cells"]["race"],
            "gap_cells_below_30_effective": s["margins"]["age_gap_by_sex"]["cells_below_30_effective"],
            "national_outgroup_share": s["national_outgroup_share"],
            "bandwidth_years": s["bandwidth"],
            "dial_components_earned": [k for k in K.COMPONENTS
                                       if s["split_half_dial_test"][k]["earns_dial"]],
            "pew_corrected_median_abs_pts_shrunk": s["pew"]["corrected_errors"]["shrunk_dial"]["median_abs_pts"]}


def main(argv: list[str]) -> None:
    build_dir = argv[0]
    stop_at_pass = "--all" not in argv
    P3B.mkdir(parents=True, exist_ok=True)
    report = json.loads((K.P3 / "kernel_report.json").read_text())
    build = engine.load_build(build_dir, allow_model_mismatch=True)
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    pool_reps: dict = {}
    out: dict = {"build": build.manifest["data_version"],
                 "shipped_kernel_sample": build.kernel.meta.get("fitting_sample"),
                 "gate": f"every persona >= {STABILITY_SHARE} share of replicates with "
                         f">= 8 of 10 top-10 overlap",
                 "order": CANDIDATES, "stop_at_first_pass": stop_at_pass,
                 "candidates": {}, "shipped": None}
    rows = []
    for sample in CANDIDATES:
        t0 = time.time()
        if sample == build.kernel.meta.get("fitting_sample"):
            kern = build.kernel      # the baseline: exactly the shipped artifact
            src = "build"
        else:
            cdir = P3B / "_candidates" / sample
            if not (cdir / "kernel.json").exists():
                K.candidate_artifact(sample, cdir, report=report)
            kern = _load_kernel(cdir, build.metro_levels)
            src = str(cdir.relative_to(RESULTS.parent))
        b = replace(build, kernel=kern)
        personas = run_personas(b, GOLDEN_VECTORS)
        stab = rank_stability(b, con, GOLDEN_VECTORS, personas, pool_reps)
        shares = {n: s["share_replicates_with_>=8of10_overlap"]
                  for n, s in stab.items() if "skipped" not in s}
        passed = all(v >= STABILITY_SHARE for v in shares.values())
        sd_med = [s["match_index_replicate_sd_median"] for s in stab.values() if "skipped" not in s]
        sd_p90 = [s["match_index_replicate_sd_p90"] for s in stab.values() if "skipped" not in s]
        rec = {"kernel_source": src, "pass": bool(passed),
               "personas_below_bar": sorted(n for n, v in shares.items() if v < STABILITY_SHARE),
               "min_share": min(shares.values()),
               "replicate_sd_median_across_personas": round(float(np.median(sd_med)), 2),
               "replicate_sd_p90_across_personas": round(float(np.median(sd_p90)), 2),
               "per_persona": stab, **sample_facts(report, sample),
               "seconds": round(time.time() - t0, 1)}
        out["candidates"][sample] = rec
        for n, s in stab.items():
            rows.append({"sample": sample, "persona": n,
                         **({"skipped": s["skipped"]} if "skipped" in s else s)})
        print(f"[{sample}] pass={passed} min share {rec['min_share']:.3f} "
              f"below bar: {rec['personas_below_bar']} sd med/p90 "
              f"{rec['replicate_sd_median_across_personas']}/{rec['replicate_sd_p90_across_personas']} "
              f"({rec['seconds']}s)", flush=True)
        (P3B / "stability_sweep.json").write_text(json.dumps(out, indent=1, default=K._json) + "\n")
        pd.DataFrame(rows).to_csv(P3B / "stability_sweep.csv", index=False)
        if passed and sample != "recent" and stop_at_pass:
            out["shipped"] = sample
            break
    if out["shipped"] is None:
        passing = [s for s in CANDIDATES if s != "recent" and s in out["candidates"]
                   and out["candidates"][s]["pass"]]
        out["shipped"] = passing[0] if passing else None
    out["rule"] = ("the shortest half-life on which every persona reaches the bar ships; "
                   "recent-only never ships (it failed in m3.0.0); the stock is never fitted "
                   "here; a failure at 20 years is a stop condition, not a reason to go further")
    (P3B / "stability_sweep.json").write_text(json.dumps(out, indent=1, default=K._json) + "\n")
    pd.DataFrame(rows).to_csv(P3B / "stability_sweep.csv", index=False)
    print(json.dumps({"shipped": out["shipped"],
                      "candidates": {s: {k: v for k, v in r.items() if k != "per_persona"}
                                     for s, r in out["candidates"].items()}}, indent=1, default=K._json))


if __name__ == "__main__":
    main(sys.argv[1:])
