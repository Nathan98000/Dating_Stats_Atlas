"""What changed for the visitor (Phase 3 exit item 4): rank before and
after across the 193 under the stated default search (the m2.4.0 build
scored by the m2.4.0 engine's outputs, which are pinned in that build's
goldens? — no: recomputed here from the OLD build loaded cross-version,
scoring the old pillar set through the old mechanics is not possible in
the new engine, so the old ranking comes from the old build's default
response snapshot written by score_snapshot.py in Phase 2g), the
correlation between the slider's two poles across the ranked set, and
the index distribution the bands cut.

Concretely this script writes results/phase3/visitor_change.json with:
  - default-search ranks under m3.0.0 vs the m2.4.0 snapshot
    (results/phase2g/rent_swap_report.json carries the m2.4.0 default
    ranking), moves, Kendall tau, the ten biggest moves
  - pool_size vs match_propensity across the ranked set: Pearson on
    log pool, Spearman, for the default search and a 64-seeker battery
    (both sexes, ages 25-50, every disclosure combination sampled) —
    the item 4 stop condition is |r| > 0.7
  - the default-search index distribution across the 193

    python -m atlas.pipeline.build.phase3_report_data <build_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, pearsonr, spearmanr

from atlas import model as engine
from atlas.model.preferences import EDU_LEVELS, RACE_LEVELS, SPEC_RACE
from atlas.pipeline.fetch import RESULTS

P3 = RESULTS / "phase3"
CUBE_TO_SPEC = {v: k for k, v in SPEC_RACE.items()}
DEFAULT = {"self": {"sex": "female", "age": 30},
           "seeking": {"age": [28, 40],
                       "marital": ["never_married", "previously_married"]}}


def old_default_ranking() -> dict[str, int] | None:
    """The m2.4.0 default-search ranking on build 5d0e3ca2f708, produced by
    the committed m2.4.0 engine (results/phase3/default_ranking_m2_4_0.json,
    written from a git worktree at the m2.4.0 commit)."""
    p = P3 / "default_ranking_m2_4_0.json"
    if not p.exists():
        return None
    rep = json.loads(p.read_text())
    return {r["cbsa"]: int(r["rank"]) for r in rep["ranked"]}


def correlation(build, body: dict) -> dict:
    res = engine.rank(build, engine.parse_request(body))
    rows = res["ranked"]
    pool = np.array([r["pool"] for r in rows], float)
    mt = np.array([r["match"]["value"] for r in rows], float)
    ok = np.isfinite(mt) & (pool > 0)
    if ok.sum() < 10:
        return {"n": int(ok.sum())}
    return {"n": int(ok.sum()),
            "pearson_log_pool": round(float(pearsonr(np.log(pool[ok]), mt[ok]).statistic), 3),
            "spearman": round(float(spearmanr(pool[ok], mt[ok]).statistic), 3)}


def main(build_dir: str) -> None:
    build = engine.load_build(build_dir)
    res = engine.rank(build, engine.parse_request(DEFAULT))
    new_rank = {r["cbsa"]: r["rank"] for r in res["ranked"]}
    names = {r["cbsa"]: r["display_name"] for r in res["ranked"]}
    out: dict = {"default_search": DEFAULT, "ranked": len(new_rank)}
    old = old_default_ranking()
    if old:
        common = [c for c in new_rank if c in old]
        moves = {c: old[c] - new_rank[c] for c in common}
        tau = kendalltau([old[c] for c in common], [new_rank[c] for c in common]).statistic
        big = sorted(common, key=lambda c: -abs(moves[c]))[:10]
        out["rank_shift_vs_m2_4_0"] = {
            "metros_compared": len(common),
            "ranks_changed": int(sum(1 for c in common if moves[c] != 0)),
            "kendall_tau": round(float(tau), 3),
            "median_abs_move": float(np.median([abs(moves[c]) for c in common])),
            "max_abs_move": int(max(abs(moves[c]) for c in common)),
            "biggest_moves": [{"metro": names[c], "cbsa": c, "old_rank": old[c],
                               "new_rank": new_rank[c], "move": moves[c]} for c in big],
            "top10_old": [names.get(c, c) for c in sorted(common, key=lambda c: old[c])[:10]],
            "top10_new": [names[c] for c in sorted(common, key=lambda c: new_rank[c])[:10]]}
        pd.DataFrame([{"cbsa": c, "metro": names[c], "rank_m2_4_0": old[c],
                       "rank_m3_0_0": new_rank[c], "move": moves[c]} for c in common]
                     ).sort_values("rank_m3_0_0").to_csv(P3 / "rank_shift_default.csv", index=False)
    else:
        out["rank_shift_vs_m2_4_0"] = {"skipped": "no m2.4.0 default ranking snapshot found"}

    # the two poles
    out["pole_correlation_default"] = correlation(build, DEFAULT)
    battery = []
    rng = np.random.default_rng(3)
    for sex in ("female", "male"):
        for age in (25, 30, 35, 42, 50):
            for edu in [None] + EDU_LEVELS:
                for race in [None] + RACE_LEVELS:
                    if rng.random() > 0.35:
                        continue
                    self_ = {"sex": sex, "age": age}
                    if edu:
                        self_["education"] = edu
                    if race:
                        self_["race_ethnicity"] = CUBE_TO_SPEC[race]
                    body = {"self": self_,
                            "seeking": {"age": [max(18, age - 2), min(70, age + 10)],
                                        "marital": ["never_married", "previously_married"]}}
                    c = correlation(build, body)
                    if "pearson_log_pool" in c:
                        battery.append({"sex": sex, "age": age, "edu": edu, "race": race, **c})
    bdf = pd.DataFrame(battery)
    bdf.to_csv(P3 / "pole_correlation_battery.csv", index=False)
    out["pole_correlation_battery"] = {
        "seekers": int(len(bdf)),
        "pearson_log_pool_median": round(float(bdf["pearson_log_pool"].median()), 3),
        "pearson_log_pool_min": round(float(bdf["pearson_log_pool"].min()), 3),
        "pearson_log_pool_max": round(float(bdf["pearson_log_pool"].max()), 3),
        "abs_pearson_p90": round(float(bdf["pearson_log_pool"].abs().quantile(0.9)), 3),
        "seekers_abs_above_0_7": int((bdf["pearson_log_pool"].abs() > 0.7).sum()),
        "spearman_median": round(float(bdf["spearman"].median()), 3),
        "stop_condition_abs_above_0_7": bool(abs(out["pole_correlation_default"]["pearson_log_pool"]) > 0.7)}
    # the index distribution under the default search
    idx = np.array([r["match"]["value"] for r in res["ranked"]], float)
    out["default_index_distribution"] = {
        "p10_p50_p90": [round(float(v), 1) for v in np.percentile(idx, [10, 50, 90])],
        "min_max": [round(float(idx.min()), 1), round(float(idx.max()), 1)],
        "top5": [(r["display_name"], r["match"]["value"]) for r in
                 sorted(res["ranked"], key=lambda r: -r["match"]["value"])[:5]],
        "bottom5": [(r["display_name"], r["match"]["value"]) for r in
                    sorted(res["ranked"], key=lambda r: r["match"]["value"])[:5]],
        "moe_index_median": round(float(np.median([r["match"]["moe"] for r in res["ranked"]])), 2)}
    (P3 / "visitor_change.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "default_search"}, indent=1)[:3000])


if __name__ == "__main__":
    main(sys.argv[1])
