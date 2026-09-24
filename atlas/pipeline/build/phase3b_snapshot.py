"""Snapshot what a build serves for the visitor-facing comparisons in
PHASE3B.md: the default search's ranking and index distribution, and a
handful of reference searches whose index runs into the hundreds (the
display-cap before/after). Taken on the m3.0.0 build before any change and
again on each build that ships, so the report compares files rather than
recomputing anything.

    python -m atlas.pipeline.build.phase3b_snapshot <build_dir> <tag>
        -> results/phase3b/snapshot_<tag>.json
"""
from __future__ import annotations

import json
import sys

import numpy as np

from atlas import model as engine
from atlas.pipeline.fetch import RESULTS

P3B = RESULTS / "phase3b"
DEFAULT = {"self": {"sex": "female", "age": 30},
           "seeking": {"age": [28, 40],
                       "marital": ["never_married", "previously_married"]}}
# the searches PHASE3.md named as running into the hundreds, plus the
# disclosed graduate seeker
REFERENCE = {
    "grad_asian_woman_30": {"self": {"sex": "female", "age": 30, "education": "graduate",
                                     "race_ethnicity": "asian_nh"},
                            "seeking": DEFAULT["seeking"]},
    "black_woman_30": {"self": {"sex": "female", "age": 30, "race_ethnicity": "black_nh"},
                       "seeking": DEFAULT["seeking"]},
    "grad_woman_30": {"self": {"sex": "female", "age": 30, "education": "graduate"},
                      "seeking": DEFAULT["seeking"]},
    "nhpi_man_35": {"self": {"sex": "male", "age": 35, "race_ethnicity": "nhpi_nh"},
                    "seeking": {"age": [33, 45],
                                "marital": ["never_married", "previously_married"]}},
    "nhpi_woman_35": {"self": {"sex": "female", "age": 35, "race_ethnicity": "nhpi_nh"},
                      "seeking": {"age": [33, 45],
                                  "marital": ["never_married", "previously_married"]}},
    "grad_asian_man_34": {"self": {"sex": "male", "age": 34, "education": "graduate",
                                   "race_ethnicity": "asian_nh"},
                          "seeking": DEFAULT["seeking"]},
    "same_sex_man_31": {"self": {"sex": "male", "age": 31},
                        "seeking": {"sex": "male", "age": [27, 38],
                                    "marital": ["never_married"],
                                    "education_min": "bachelors"}},
}


def summarise(res: dict) -> dict:
    rows = res["ranked"]
    idx = np.array([r["match"]["value"] for r in rows], float)
    moe = np.array([r["match"]["moe"] for r in rows], float)
    by_index = sorted(rows, key=lambda r: -r["match"]["value"])
    return {
        "ranked": len(rows),
        "index_p10_p50_p90": [round(float(v), 1) for v in np.percentile(idx, [10, 50, 90])],
        "index_min_max": [round(float(idx.min()), 1), round(float(idx.max()), 1)],
        "moe_median": round(float(np.median(moe)), 2),
        "metros_index_above_250": int((idx > 250).sum()),
        "metros_index_above_200": int((idx > 200).sum()),
        "top5_by_index": [{"metro": r["display_name"], "cbsa": r["cbsa"],
                           "index": r["match"]["value"], "display": r["match"]["display"],
                           "band": r["match"].get("band", {}).get("label"),
                           "rank": r["rank"], "score": r["score"]} for r in by_index[:5]],
        "bottom3_by_index": [{"metro": r["display_name"], "cbsa": r["cbsa"],
                              "index": r["match"]["value"], "display": r["match"]["display"]}
                             for r in by_index[-3:]],
        "rows": [{"cbsa": r["cbsa"], "metro": r["display_name"], "rank": r["rank"],
                  "score": r["score"], "index": r["match"]["value"],
                  "display": r["match"]["display"], "moe": r["match"]["moe"],
                  "band": r["match"].get("band", {}).get("label")} for r in rows],
    }


def main(build_dir: str, tag: str) -> None:
    build = engine.load_build(build_dir)
    out = {"build": build.manifest["data_version"], "model_version": engine.MODEL_VERSION,
           "kernel_sample": build.kernel.meta.get("fitting_sample"),
           "default_search": DEFAULT, "default": summarise(engine.rank(build, engine.parse_request(DEFAULT))),
           "reference": {}}
    for name, body in REFERENCE.items():
        out["reference"][name] = {"body": body,
                                  **summarise(engine.rank(build, engine.parse_request(body)))}
    P3B.mkdir(parents=True, exist_ok=True)
    (P3B / f"snapshot_{tag}.json").write_text(json.dumps(out, indent=1) + "\n")
    brief = {"build": out["build"], "default": {k: v for k, v in out["default"].items() if k != "rows"},
             "reference": {n: {k: v for k, v in r.items() if k not in ("rows", "body", "bottom3_by_index")}
                           for n, r in out["reference"].items()}}
    print(json.dumps(brief, indent=1))


def compare(tag_a: str, tag_b: str) -> None:
    """The rank shift and the index's range/margin between two snapshots,
    default search, plus the before/after of every reference search's
    top city — written, never recomputed in the report."""
    from scipy.stats import kendalltau
    import pandas as pd
    a = json.loads((P3B / f"snapshot_{tag_a}.json").read_text())
    b = json.loads((P3B / f"snapshot_{tag_b}.json").read_text())
    ra = {r["cbsa"]: r for r in a["default"]["rows"]}
    rb = {r["cbsa"]: r for r in b["default"]["rows"]}
    common = [c for c in rb if c in ra]
    moves = {c: ra[c]["rank"] - rb[c]["rank"] for c in common}
    tau = kendalltau([ra[c]["rank"] for c in common], [rb[c]["rank"] for c in common]).statistic
    big = sorted(common, key=lambda c: -abs(moves[c]))[:10]
    idx_move = {c: rb[c]["index"] - ra[c]["index"] for c in common}
    out = {"from": {"tag": tag_a, "build": a["build"], "model_version": a["model_version"], "kernel_sample": a["kernel_sample"]},
           "to": {"tag": tag_b, "build": b["build"], "model_version": b["model_version"], "kernel_sample": b["kernel_sample"]},
           "default_search": a["default_search"],
           "rank_shift": {"metros_compared": len(common),
                          "ranks_changed": int(sum(1 for c in common if moves[c] != 0)),
                          "kendall_tau": round(float(tau), 3),
                          "median_abs_move": float(np.median([abs(moves[c]) for c in common])),
                          "p90_abs_move": float(np.percentile([abs(moves[c]) for c in common], 90)),
                          "max_abs_move": int(max(abs(moves[c]) for c in common)),
                          "biggest_moves": [{"metro": rb[c]["metro"], "cbsa": c, "rank_before": ra[c]["rank"],
                                             "rank_after": rb[c]["rank"], "move": moves[c]} for c in big],
                          "top10_before": [ra[c]["metro"] for c in sorted(common, key=lambda c: ra[c]["rank"])[:10]],
                          "top10_after": [rb[c]["metro"] for c in sorted(common, key=lambda c: rb[c]["rank"])[:10]]},
           "index_shift": {"median_abs_change_pts": round(float(np.median([abs(v) for v in idx_move.values()])), 2),
                           "p90_abs_change_pts": round(float(np.percentile([abs(v) for v in idx_move.values()], 90)), 2),
                           "max_abs_change_pts": round(float(max(abs(v) for v in idx_move.values())), 2),
                           "range_before": a["default"]["index_min_max"], "range_after": b["default"]["index_min_max"],
                           "p10_p50_p90_before": a["default"]["index_p10_p50_p90"],
                           "p10_p50_p90_after": b["default"]["index_p10_p50_p90"],
                           "moe_median_before": a["default"]["moe_median"], "moe_median_after": b["default"]["moe_median"],
                           "kendall_tau_index": round(float(kendalltau([ra[c]["index"] for c in common],
                                                                       [rb[c]["index"] for c in common]).statistic), 3)},
           "reference": {}}
    for name in a["reference"]:
        xa, xb = a["reference"][name], b["reference"][name]
        out["reference"][name] = {
            "top_before": xa["top5_by_index"][0], "top_after": xb["top5_by_index"][0],
            "range_before": xa["index_min_max"], "range_after": xb["index_min_max"],
            "metros_above_250_before": xa["metros_index_above_250"], "metros_above_250_after": xb["metros_index_above_250"],
            "moe_median_before": xa["moe_median"], "moe_median_after": xb["moe_median"]}
    (P3B / f"rank_shift_{tag_a}_to_{tag_b}.json").write_text(json.dumps(out, indent=1) + "\n")
    pd.DataFrame([{"cbsa": c, "metro": rb[c]["metro"], f"rank_{tag_a}": ra[c]["rank"], f"rank_{tag_b}": rb[c]["rank"],
                   "move": moves[c], f"index_{tag_a}": ra[c]["index"], f"index_{tag_b}": rb[c]["index"]}
                  for c in common]).sort_values(f"rank_{tag_b}").to_csv(
        P3B / f"rank_shift_{tag_a}_to_{tag_b}.csv", index=False)
    print(json.dumps({k: v for k, v in out.items() if k in ("rank_shift", "index_shift")}, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        main(sys.argv[1], sys.argv[2])
