"""Snapshot ranked scores for the persona set against a build — the
before/after instrument for Phase 2d's two model changes, so the pillar
split's effect (item 4: none at defaults, asserted) and the nice-days
recomputation's effect (item 11: real, measured) can be read apart.

Usage: python -m atlas.pipeline.build.score_snapshot <build_dir> <out.json>
Scores are stored UNROUNDED so exact-reproduction assertions bite.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from atlas.model import versions
from atlas.model.loader import load_build
from atlas.model.preferences import parse_request
from atlas.model import scoring
from atlas.pipeline.fetch import RESULTS


def personas() -> dict[str, dict]:
    """The m1.2.0 persona requests (kept verbatim as the common yardstick),
    those still expressible under the current contract."""
    src = json.loads(
        (RESULTS / "phase2c" / "m1_2_0_rankings.json").read_text())
    out = {}
    for name, p in src["personas"].items():
        req = json.loads(json.dumps(p["request"]))
        seeking = req.get("seeking", {})
        marital = seeking.get("marital") or []
        if any(m == "currently_married" for m in marital):
            continue
        races = seeking.get("race_ethnicity") or []
        if any(r in ("two_or_more_nh", "other_nh") for r in races):
            continue
        if "size_vs_odds" in req:
            # the alias left the contract in m2.1.0; its documented
            # meaning was pool_vs_balance with the same value
            req["pool_vs_balance"] = req.pop("size_vs_odds")
        out[name] = req
    return out


def snapshot(build_dir: str | Path) -> dict:
    build = load_build(build_dir, allow_model_mismatch=True)
    entry = {"model_version": build.manifest["model_version"],
             "build": build.manifest["data_version"], "personas": {}}
    for name, req in personas().items():
        parsed = parse_request(json.loads(json.dumps(req)))
        result = scoring.rank(build, parsed)
        # unrounded scores: recompute the score vector over the same ranked
        # rows through the same entry the validation suite uses
        rows = [{"cbsa": r["cbsa"], "rank": r["rank"], "score": r["score"],
                 "pool": r["pool"]} for r in result["ranked"]]
        entry["personas"][name] = {
            "request": req,
            "weights": result["weights"],
            "ranked": rows,
            "exact_scores": _exact_scores(build, parsed),
        }
    return entry


def _exact_scores(build, parsed) -> dict[str, float]:
    """cbsa -> unrounded score for the ranked set, bypassing display
    rounding (the item-4 assertion compares these at 1e-9)."""
    from atlas.model.preferences import balance_masks, pool_mask, resolve_weights
    from atlas.model.suppression import N_GATE_MIN, tier_masks
    mask_p = pool_mask(parsed.seeking)
    m_sought, m_seeker = balance_masks(parsed)
    est = (build.pool_flat @ mask_p).astype(np.float64)
    n_alloc = (build.count_flat @ mask_p).astype(np.float64)
    sumw2 = (build.sumw2_flat @ mask_p).astype(np.float64)
    b_sought = (build.pool_flat @ m_sought).astype(np.float64)
    b_sought_n = (build.count_flat @ m_sought).astype(np.float64)
    b_sought_w2 = (build.sumw2_flat @ m_sought).astype(np.float64)
    b_seeker = (build.pool_flat @ m_seeker).astype(np.float64)
    b_seeker_n = (build.count_flat @ m_seeker).astype(np.float64)
    b_seeker_w2 = (build.sumw2_flat @ m_seeker).astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        kish = np.where(sumw2 > 0, est ** 2 / sumw2, 0.0)
        k_sought = np.where(b_sought_w2 > 0, b_sought ** 2 / b_sought_w2, 0.0)
        k_seeker = np.where(b_seeker_w2 > 0, b_seeker ** 2 / b_seeker_w2, 0.0)
    n_gate = np.minimum(n_alloc, kish)
    same_sex = parsed.seeking.sex == parsed.self_sex
    bal_ok = ((np.minimum(b_sought_n, k_sought) >= N_GATE_MIN)
              & (np.minimum(b_seeker_n, k_seeker) >= N_GATE_MIN)
              & (b_seeker > 0) & (not same_sex))
    with np.errstate(divide="ignore", invalid="ignore"):
        bal_ratio = np.where(bal_ok, b_sought / np.maximum(b_seeker, 1e-9),
                             np.nan)
    _, ranked = tier_masks(build.ranked_set, est, n_gate)
    ridx = np.where(ranked)[0]
    if not len(ridx):
        return {}
    weights = resolve_weights(parsed, build.manifest["model_defaults"])
    balance_scored = np.where(bal_ok[ridx], bal_ratio[ridx], np.nan)
    scores = scoring.score_vector(build, ridx, est[ridx], balance_scored,
                                  weights)
    return {build.metro_levels[int(i)]: float(s)
            for i, s in zip(ridx, scores)}


if __name__ == "__main__":
    build_dir, out = sys.argv[1], Path(sys.argv[2])
    data = snapshot(build_dir)
    data["engine_model_version"] = versions.MODEL_VERSION
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1) + "\n")
    n = len(data["personas"])
    print(f"{n} personas -> {out}")
