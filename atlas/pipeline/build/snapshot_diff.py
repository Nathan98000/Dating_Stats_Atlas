"""Compare two score snapshots (Phase 2d): the report's before/after
instrument. Item 4's split is asserted exact separately
(split_equivalence); this measures what actually moves rankings — the
pleasant-days recomputation — so the two effects read apart.

Usage: python -m atlas.pipeline.build.snapshot_diff <before.json> <after.json> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from scipy.stats import kendalltau


def rank_map(p: dict) -> dict[str, int]:
    return {r["cbsa"]: r["rank"] for r in p["ranked"]}


def main(before_path: str, after_path: str, out_path: str) -> None:
    before = json.loads(Path(before_path).read_text())
    after = json.loads(Path(after_path).read_text())
    names = {}
    metros_file = Path("atlas/results/phase2c/city_meta.csv")
    if metros_file.exists():
        import pandas as pd
        cm = pd.read_csv(metros_file, dtype={"cbsa": str})
        names = dict(zip(cm["cbsa"], cm["display_name"]))
    out = {"before": {"build": before["build"],
                      "model": before["model_version"]},
           "after": {"build": after["build"], "model": after["model_version"]},
           "personas": {}}
    for name in before["personas"]:
        if name not in after["personas"]:
            continue
        rb = rank_map(before["personas"][name])
        ra = rank_map(after["personas"][name])
        common = sorted(set(rb) & set(ra))
        if len(common) < 10:
            out["personas"][name] = {"skipped": f"{len(common)} common"}
            continue
        tau = kendalltau([rb[c] for c in common],
                         [ra[c] for c in common]).statistic
        top_b = {c for c, r in rb.items() if r <= 10}
        top_a = {c for c, r in ra.items() if r <= 10}
        moves = sorted(((c, rb[c] - ra[c]) for c in common),
                       key=lambda kv: -abs(kv[1]))
        out["personas"][name] = {
            "kendall_tau": round(float(tau), 3),
            "common_metros": len(common),
            "top10_overlap": len(top_b & top_a),
            "median_abs_move": float(
                sorted(abs(m) for _, m in moves)[len(moves) // 2]),
            "biggest_moves": [
                {"cbsa": c, "name": names.get(c, c), "before": rb[c],
                 "after": ra[c], "move": m} for c, m in moves[:8]],
        }
    Path(out_path).write_text(json.dumps(out, indent=1) + "\n")
    for name, p in out["personas"].items():
        if "skipped" in p:
            continue
        print(f"{name:32s} tau {p['kendall_tau']:5.2f}  top10 "
              f"{p['top10_overlap']}/10  median move {p['median_abs_move']:.0f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
