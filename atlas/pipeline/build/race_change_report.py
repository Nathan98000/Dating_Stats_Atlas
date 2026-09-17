"""The m2.2.0 race change's evidence (Phase 2e item 10): PROOF that
default-setting outputs reproduce m2.1.0 exactly, and the measured drop
for race-filtered searches now that nothing is added to a selection.

Two parts:
  1. Assert, against the pinned m2.1.0 snapshot, that every persona
     WITHOUT a race filter reproduces its unrounded scores exactly, and
     measure how the race-filtered personas move.
  2. Three worked searches (the brief's set): a single-group selection in
     a large metro, a two-group selection, and the same single group in
     Urban Honolulu, where the multiracial share is largest — pool under
     the old rule (ticked + the two always-counted groups) vs the new
     rule (ticked only), with the drop.

Usage: python -m atlas.pipeline.build.race_change_report <build_dir>
Writes results/phase2e/race_change_report.json.
"""
from __future__ import annotations

import json
import sys

import numpy as np

from atlas.model.loader import load_build
from atlas.model.preferences import SPEC_RACE, mask_vector, parse_request
from atlas.pipeline.build.score_snapshot import _exact_scores, personas
from atlas.pipeline.fetch import RESULTS

P2E = RESULTS / "phase2e"
TOL = 1e-9
OLD_EXTRA = ("nh_twoplus", "nh_other")   # what ADR 0004 always ORed in

WORKED = [
    {"name": "asian_nh in Los Angeles", "metro": "31080",
     "races": ["asian_nh"],
     "self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]}},
    {"name": "black_nh + hispanic in Chicago", "metro": "16980",
     "races": ["black_nh", "hispanic"],
     "self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]}},
    {"name": "asian_nh in Urban Honolulu", "metro": "46520",
     "races": ["asian_nh"],
     "self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]}},
]


def main(build_dir: str) -> None:
    P2E.mkdir(parents=True, exist_ok=True)
    build = load_build(build_dir)
    snap = json.loads(
        (RESULTS / "phase2d" / "m2_1_0_snapshot.json").read_text())
    assert snap["build"] == build.manifest["data_version"], (
        "the exactness claim needs the same data on both sides")

    out = {"build": build.manifest["data_version"],
           "default_exactness": {}, "race_filtered_moves": {},
           "worked_searches": []}
    worst_default = 0.0
    for name, p in snap["personas"].items():
        req = json.loads(json.dumps(p["request"]))
        if "size_vs_odds" in req:
            req["pool_vs_balance"] = req.pop("size_vs_odds")
        has_race = bool(req.get("seeking", {}).get("race_ethnicity"))
        new_scores = _exact_scores(build, parse_request(req))
        old_scores = p["exact_scores"]
        if not has_race:
            assert set(new_scores) == set(old_scores), (
                f"{name}: ranked set changed without a race filter")
            mx = max((abs(new_scores[c] - old_scores[c])
                      for c in old_scores), default=0.0)
            worst_default = max(worst_default, mx)
            out["default_exactness"][name] = {"max_abs_score_diff": mx}
            assert mx < TOL, (
                f"{name}: a race-free request moved by {mx} — the m2.2.0 "
                f"claim is that ONLY race-filtered outputs move")
        else:
            common = set(new_scores) & set(old_scores)
            moves = sorted((abs(new_scores[c] - old_scores[c])
                            for c in common), reverse=True)
            out["race_filtered_moves"][name] = {
                "ranked_before": len(old_scores),
                "ranked_after": len(new_scores),
                "max_abs_score_diff": moves[0] if moves else 0.0,
            }
    out["worst_default_abs_diff"] = worst_default

    for w in WORKED:
        i = build.metro_levels.index(w["metro"])
        spec = parse_request({"self": w["self"],
                              "seeking": {**w["seeking"],
                                          "race_ethnicity": w["races"]}}
                             ).seeking
        new_levels = spec.race_cube_levels
        old_levels = tuple(dict.fromkeys(
            [SPEC_RACE[r] for r in w["races"]] + list(OLD_EXTRA)))
        args = (spec.sex, spec.age_min, spec.age_max, spec.marital_levels,
                spec.education_min, spec.income_min)
        pool_new = float(build.pool_flat[i] @ mask_vector(*args, new_levels))
        pool_old = float(build.pool_flat[i] @ mask_vector(*args, old_levels))
        out["worked_searches"].append({
            "search": w["name"],
            "metro": build.display_names[i],
            "pool_old_rule": round(pool_old),
            "pool_new_rule": round(pool_new),
            "drop": round(pool_old - pool_new),
            "drop_pct": round((pool_old - pool_new) / pool_old * 100, 1),
        })

    (P2E / "race_change_report.json").write_text(
        json.dumps(out, indent=1) + "\n")
    print(f"default exactness: worst |diff| {worst_default:.2e} over "
          f"{len(out['default_exactness'])} race-free personas")
    for w in out["worked_searches"]:
        print(f"  {w['search']:34s} {w['pool_old_rule']:>9,} -> "
              f"{w['pool_new_rule']:>9,}  (-{w['drop_pct']}%)")


if __name__ == "__main__":
    main(sys.argv[1])
