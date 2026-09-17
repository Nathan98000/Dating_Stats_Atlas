"""Gate 7's second clause, run as a one-off phase gate: the six-pillar
split (item 4) reproduces m2.0.0 scoring EXACTLY at default settings.

Method: load the m2.0.0 build (same pleasant-days data, same everything),
patch only the pillar bookkeeping in memory to the v4 registry — the
lifestyle features move to their own pillars with weight 1.0, and the
pillar weights become the six-way split — then score every snapshot
persona under the m2.1.0 engine and compare against the pinned m2.0.0
unrounded scores. The split divides lifestyle's 0.10 exactly in the
proportion its features carried (0.6/0.4), so the effective per-feature
weights are arithmetically identical and any difference is a bug.

Usage: python -m atlas.pipeline.build.split_equivalence <old_build_dir>
Writes results/phase2d/split_equivalence.json.
"""
from __future__ import annotations

import json
import sys

from atlas.model.loader import load_build
from atlas.pipeline.build.score_snapshot import _exact_scores, personas
from atlas.pipeline.fetch import RESULTS
from atlas.pipeline.registry.loader import load_registry
from atlas.model.preferences import parse_request

P2D = RESULTS / "phase2d"
TOL = 1e-9


def main(old_build_dir: str) -> None:
    reg = load_registry()
    build = load_build(old_build_dir, allow_model_mismatch=True)
    fb = build.manifest["features_block"]
    for fid in ("pleasant_days", "students_per_1k_adults"):
        fb[fid]["pillar"] = reg.features[fid].pillar
        fb[fid]["weight_in_pillar"] = reg.features[fid].weight_in_pillar
    build.manifest["model_defaults"]["pillar_weights"] = reg.pillar_weights

    snap = json.loads((P2D / "m2_0_0_snapshot.json").read_text())
    assert snap["build"] == build.manifest["data_version"], (
        "snapshot and build disagree — compare like with like")
    # The one principled exception, found by this gate's first run and
    # reported rather than absorbed: a metro missing ONE lifestyle feature
    # used to renormalize within the pillar (its sibling quietly carried
    # the whole 0.10); under the split that metro is missing a whole
    # pillar, and the registry's missing-pillar policy redistributes the
    # weight pro-rata across the rest. The split is asserted EXACT for
    # every metro carrying both features; the missing-feature metros are
    # listed with their movement.
    midx = {c: i for i, c in enumerate(build.metro_levels)}
    incomplete = {c for c in build.metro_levels
                  if any(f in (build.feature_flags[midx[c]] or "")
                         for f in ("pleasant_days", "students_per_1k_adults"))}
    out = {"old_build": snap["build"], "tolerance": TOL, "personas": {},
           "metros_with_missing_lifestyle_feature": sorted(incomplete)}
    worst = 0.0
    policy_moves: dict[str, float] = {}
    for name, p in snap["personas"].items():
        req = json.loads(json.dumps(p["request"]))
        if "size_vs_odds" in req:
            # the alias left the contract in m2.1.0; its documented
            # meaning was pool_vs_balance with the same value, so the
            # persona re-expresses rather than dropping out
            req["pool_vs_balance"] = req.pop("size_vs_odds")
        parsed = parse_request(req)
        new_scores = _exact_scores(build, parsed)
        old_scores = p["exact_scores"]
        assert set(new_scores) == set(old_scores), (
            f"{name}: ranked set changed under the split")
        diffs = {c: abs(new_scores[c] - old_scores[c]) for c in old_scores}
        complete_mx = max((d for c, d in diffs.items() if c not in incomplete),
                          default=0.0)
        worst = max(worst, complete_mx)
        for c in incomplete:
            if c in diffs:
                policy_moves[c] = max(policy_moves.get(c, 0.0), diffs[c])
        out["personas"][name] = {
            "metros": len(diffs),
            "max_abs_score_diff_complete_metros": complete_mx}
        assert complete_mx < TOL, (
            f"{name}: split changed a default-setting score by {complete_mx} "
            f"(> {TOL}) on a metro with complete lifestyle features — the "
            f"split must be pure re-bookkeeping there")
    out["worst_abs_score_diff_complete_metros"] = worst
    out["missing_pillar_policy_moves"] = {
        c: round(v, 3) for c, v in sorted(policy_moves.items())}
    (P2D / "split_equivalence.json").write_text(
        json.dumps(out, indent=1) + "\n")
    print(f"exact on complete metros: worst |diff| {worst:.2e} "
          f"(tolerance {TOL}) across {len(out['personas'])} personas")
    print(f"missing-pillar policy moves (reported, not absorbed): "
          f"{out['missing_pillar_policy_moves']}")


if __name__ == "__main__":
    main(sys.argv[1])
