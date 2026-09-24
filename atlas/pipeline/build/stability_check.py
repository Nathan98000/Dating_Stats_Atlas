"""Phase 3b, Part B: the standing rank-stability gate on candidate kernel
artifacts (kernel_refine.py candidate/ship --out), loaded into a build in
memory in place of its shipped kernel — the same harness as the half-life
sweep. A refinement that fails the gate does not ship whatever its
held-out gain.

    python -m atlas.pipeline.build.stability_check <build_dir> <name>=<candidate_dir> [...]
        -> results/phase3b/stability_check.json (merged per name)
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from atlas import model as engine
from atlas.model.loader import _load_kernel
from atlas.model.tests.golden.make_fixture import GOLDEN_VECTORS
from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.build.validate import STABILITY_SHARE, rank_stability, run_personas
from atlas.pipeline.fetch import RESULTS

P3B = RESULTS / "phase3b"


def main(build_dir: str, specs: list[str]) -> None:
    build = engine.load_build(build_dir, allow_model_mismatch=True)
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    path = P3B / "stability_check.json"
    out = json.loads(path.read_text()) if path.exists() else {"build": build.manifest["data_version"],
                                                               "gate": f"every persona >= {STABILITY_SHARE}",
                                                               "candidates": {}}
    pool_reps: dict = {}
    for spec in specs:
        name, cdir = spec.split("=", 1)
        t0 = time.time()
        kern = _load_kernel(Path(cdir), build.metro_levels)
        b = replace(build, kernel=kern)
        personas = run_personas(b, GOLDEN_VECTORS)
        stab = rank_stability(b, con, GOLDEN_VECTORS, personas, pool_reps)
        shares = {n: s["share_replicates_with_>=8of10_overlap"] for n, s in stab.items() if "skipped" not in s}
        sd = [s["match_index_replicate_sd_median"] for s in stab.values() if "skipped" not in s]
        rec = {"artifact": cdir, "kernel_version": kern.meta.get("version"),
               "pass": bool(all(v >= STABILITY_SHARE for v in shares.values())),
               "min_share": min(shares.values()),
               "personas_below_bar": sorted(n for n, v in shares.items() if v < STABILITY_SHARE),
               "replicate_sd_median_across_personas": round(float(np.median(sd)), 2),
               "per_persona": stab, "seconds": round(time.time() - t0, 1)}
        out["candidates"][name] = rec
        print(f"[{name}] pass={rec['pass']} min share {rec['min_share']:.4f} below bar {rec['personas_below_bar']} "
              f"sd median {rec['replicate_sd_median_across_personas']} ({rec['seconds']}s)", flush=True)
        path.write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
