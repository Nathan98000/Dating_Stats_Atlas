"""Phase 2g item 1: what the ACS→HUD rent swap did, measured (gates 2–4).

Reads the OLD build (m2.3.1, ACS B25031 one-bedroom) and the NEW build
(m2.4.0, HUD FY2027 50th-percentile one-bedroom) and reports:

  - the level shift: HUD/ACS ratio across the 193 ranked metros
    (median, p10, p90), Austin named;
  - the rent stat page's reordering: positions in registry-direction
    order (cheapest first) before and after, the ten largest moves;
  - the overall-ranking effect: engine.rank on both builds under the
    stated default search — how many of the 193 change rank, Kendall
    tau, the biggest moves, Austin named;
  - gate 4's byte-identity: the three cubes' SHA-256s equal between
    builds, and every features.parquet column identical except the rent
    column and its standing.

Usage:
    python -m atlas.pipeline.build.rent_swap_report <old_build> <new_build> <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from atlas import model as engine

DEFAULT_REQ = {"self": {"sex": "female", "age": 30},
               "seeking": {"age": [28, 40],
                           "marital": ["never_married", "previously_married"]}}
AUSTIN = "12420"


def _positions(vals: pd.Series) -> dict[str, int]:
    """Stat-page positions: ascending (cheapest first — the registry's
    good_low direction), numbered once, ties broken stably by cbsa."""
    order = sorted(vals.index, key=lambda c: (vals[c], c))
    return {c: i + 1 for i, c in enumerate(order)}


def main(old_dir: str, new_dir: str, out_path: str) -> None:
    old = engine.load_build(old_dir, allow_model_mismatch=True)
    new = engine.load_build(new_dir)
    assert old.manifest["model_version"] == "m2.3.1"
    assert new.manifest["model_version"] == engine.MODEL_VERSION

    # ---- gate 4: nothing but rent moved in the artifact's inputs -----------
    cubes_identical = {}
    for f in ("pool_cube.npy", "count_cube.npy", "sumw2_cube.npy",
              "pairing_cells.parquet", "metros.json"):
        ha = hashlib.sha256((Path(old_dir) / f).read_bytes()).hexdigest()
        hb = hashlib.sha256((Path(new_dir) / f).read_bytes()).hexdigest()
        cubes_identical[f] = ha == hb
        assert ha == hb, f"{f} differs between builds — only rent may move"
    fa = pd.read_parquet(Path(old_dir) / "features.parquet")
    fb = pd.read_parquet(Path(new_dir) / "features.parquet")
    rent_cols = {"median_gross_rent", "rent_1br",
                 "standing_all_median_gross_rent", "standing_all_rent_1br"}
    shared = [c for c in fa.columns if c in fb.columns and c not in rent_cols]
    changed = [c for c in shared
               if not fa[c].equals(fb[c])]
    assert not changed, f"non-rent feature columns moved: {changed}"

    ranked = new.ranked_set
    cbsas = [c for i, c in enumerate(new.metro_levels) if ranked[i]]
    titles = {c: new.display_names[i]
              for i, c in enumerate(new.metro_levels)}
    # the loader maps the old artifact's median_gross_rent column onto
    # the new name under allow_model_mismatch; its VALUES are the ACS ones
    acs = pd.Series({c: float(old.static["rent_1br"][
        old.metro_levels.index(c)]) for c in cbsas})
    hud = pd.Series({c: float(new.static["rent_1br"][
        new.metro_levels.index(c)]) for c in cbsas})
    ratio = hud / acs

    # ---- the stat page's reordering ----------------------------------------
    pos_a, pos_b = _positions(acs), _positions(hud)
    moves = sorted(((c, pos_a[c] - pos_b[c]) for c in cbsas),
                   key=lambda kv: -abs(kv[1]))
    stat_moves = [{"cbsa": c, "name": titles[c],
                   "acs": round(acs[c]), "hud": round(hud[c]),
                   "old_pos": pos_a[c], "new_pos": pos_b[c],
                   "move": m} for c, m in moves[:10]]

    # ---- the overall ranking under the stated default search ---------------
    req = engine.parse_request(json.loads(json.dumps(DEFAULT_REQ)))
    ra = engine.rank(old, req)
    rb = engine.rank(new, engine.parse_request(json.loads(json.dumps(DEFAULT_REQ))))
    rank_a = {r["cbsa"]: r["rank"] for r in ra["ranked"]}
    rank_b = {r["cbsa"]: r["rank"] for r in rb["ranked"]}
    assert set(rank_a) == set(rank_b) == set(cbsas), (
        "the ranked set itself must not move with a rent swap")
    overall_moves = sorted(((c, rank_a[c] - rank_b[c]) for c in cbsas),
                           key=lambda kv: -abs(kv[1]))
    from scipy.stats import kendalltau
    tau = kendalltau([rank_a[c] for c in cbsas],
                     [rank_b[c] for c in cbsas]).statistic
    # gate 4's response-level check: pools and balance identical rows
    pools_a = {r["cbsa"]: r["pool"] for r in ra["ranked"]}
    pools_b = {r["cbsa"]: r["pool"] for r in rb["ranked"]}
    assert pools_a == pools_b, "pool counts moved — only cost may move"
    bal_a = {r["cbsa"]: r["balance"].get("per_100") for r in ra["ranked"]}
    bal_b = {r["cbsa"]: r["balance"].get("per_100") for r in rb["ranked"]}
    assert bal_a == bal_b, "balance figures moved — only cost may move"

    out = {
        "old": {"build": old.manifest["data_version"], "model": "m2.3.1",
                "rent": "ACS B25031 one-bedroom median, 2020-2024"},
        "new": {"build": new.manifest["data_version"],
                "model": engine.MODEL_VERSION,
                "rent": "HUD FY2027 50th-percentile one-bedroom"},
        "level_shift_hud_over_acs": {
            "median": round(float(ratio.median()), 3),
            "p10": round(float(ratio.quantile(0.10)), 3),
            "p90": round(float(ratio.quantile(0.90)), 3),
            "min": {"cbsa": ratio.idxmin(), "name": titles[ratio.idxmin()],
                    "ratio": round(float(ratio.min()), 3)},
            "max": {"cbsa": ratio.idxmax(), "name": titles[ratio.idxmax()],
                    "ratio": round(float(ratio.max()), 3)},
        },
        "austin": {
            "acs": round(acs[AUSTIN]), "hud": round(hud[AUSTIN]),
            "ratio": round(float(ratio[AUSTIN]), 3),
            "stat_page_pos_old": pos_a[AUSTIN],
            "stat_page_pos_new": pos_b[AUSTIN],
            "overall_rank_old": rank_a[AUSTIN],
            "overall_rank_new": rank_b[AUSTIN],
        },
        "stat_page_biggest_moves": stat_moves,
        "overall_rank": {
            "changed": sum(1 for c in cbsas if rank_a[c] != rank_b[c]),
            "of": len(cbsas),
            "kendall_tau": round(float(tau), 3),
            "biggest_moves": [
                {"cbsa": c, "name": titles[c], "old": rank_a[c],
                 "new": rank_b[c], "move": m}
                for c, m in overall_moves[:10]],
        },
        "gate4_byte_identity": {
            "cubes_and_metros_identical": cubes_identical,
            "non_rent_feature_columns_identical": True,
            "pool_counts_identical": True,
            "balance_figures_identical": True,
        },
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, indent=1) + "\n")
    ls = out["level_shift_hud_over_acs"]
    print(f"level shift HUD/ACS: median {ls['median']}, "
          f"p10 {ls['p10']}, p90 {ls['p90']}")
    print(f"austin: {out['austin']}")
    print(f"overall: {out['overall_rank']['changed']}/{len(cbsas)} ranks "
          f"change, tau {out['overall_rank']['kendall_tau']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
