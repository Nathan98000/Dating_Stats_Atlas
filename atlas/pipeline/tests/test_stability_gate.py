"""Phase 3c (B1, ADR 0011): the wobble gate's arithmetic and verdict, on
synthetic rankings and records (no build, no database)."""
import json

import numpy as np

from atlas.pipeline.build import stability_gate as SG


def test_wobble_counts_places_moved_over_both_top_tens():
    n = 40
    identity = np.arange(n)
    assert SG.wobble_of(identity) == (0.0, True)
    # 10th and 11th swap: two cities move one place each -> 2 / 11 cities
    swap = identity.copy()
    swap[9], swap[10] = 10, 9
    w, hit = SG.wobble_of(swap)
    assert abs(w - 2 / 11) < 1e-12 and hit
    # the 40th city jumps to 1st: it moves 39, the first ten each move one
    jump = np.concatenate([[39], np.arange(39)])
    w, hit = SG.wobble_of(jump)
    assert abs(w - (39 + 10) / 11) < 1e-12 and hit
    # three of the top ten fall out: the old rule fails
    out3 = np.concatenate([np.arange(7), [30, 31, 32], np.arange(7, 30), [33, 34, 35, 36, 37, 38, 39]])
    _, hit = SG.wobble_of(out3)
    assert not hit


def _rec(name, wobbles, hashes, personas=()):
    return {"name": name, "build": "b", "searches": {
        n: {"wobble": w, "index_hash": h, "replicate_hash": h + "r",
            "overlap_share_old_rule": 0.9 if n in personas else 1.0}
        for n, (w, h) in zip(["persona:a", "s1", "s2", "s3"], zip(wobbles, hashes))}}


def test_identity_reads_exactly_one_and_passes():
    ref = _rec("ref", [1.0, 2.0, 3.0, 4.0], list("abcd"), personas=["persona:a"])
    v = SG.verdict(_rec("same", [1.0, 2.0, 3.0, 4.0], list("abcd")), ref)
    assert v["ratio"] == 1.0 and v["pass"] and v["searches_touched"] == 0
    assert v["basis"].startswith("all searches")


def test_verdict_sums_over_touched_searches_only():
    ref = _rec("ref", [1.0, 2.0, 3.0, 4.0], list("abcd"))
    # s2 and s3 touched: 3 + 4 = 7 -> 3.3 + 4.3 = 7.6 (8.6% up) passes
    v = SG.verdict(_rec("c", [9.0, 9.0, 3.3, 4.3], list("abXY")), ref)
    assert v["searches_touched"] == 2 and abs(v["ratio"] - 7.6 / 7) < 1e-5 and v["pass"]
    # 3.5 + 4.5 = 8 (14% up) fails, and s3 (+12.5%) is not a 25% riser but s2 (+16.7%) is not either
    v = SG.verdict(_rec("c", [9.0, 9.0, 3.5, 4.5], list("abXY")), ref)
    assert not v["pass"]
    # a 25% riser is named even when the total passes
    v = SG.verdict(_rec("c", [1.0, 2.0, 3.0, 5.1], list("abcZ")), ref)
    assert [x["search"] for x in v["searches_wobble_rose_more_than_25pct"]] == ["s3"]


def test_enlarged_noise_fails_when_replicates_change():
    ref = _rec("ref", [1.0, 2.0, 3.0, 4.0], list("abcd"))
    cand = _rec("noise", [1.5, 3.0, 4.5, 6.0], list("abcd"))
    for r in cand["searches"].values():
        r["replicate_hash"] = "scaled"
    v = SG.verdict(cand, ref)
    assert v["searches_touched"] == 4 and abs(v["ratio"] - 1.5) < 1e-12 and not v["pass"]


def test_test_searches_are_unique_and_cover_the_three_sets():
    s = SG.test_searches()
    names = [n for n, _ in s]
    assert len(names) == len(set(names))
    bodies = {json.dumps(b, sort_keys=True) for _, b in s}
    assert len(bodies) == len(s)
    assert sum(n.startswith("persona:") for n in names) == 18
    assert sum(n.startswith("samesex:") for n in names) == 2 * 5 * 5
    grid = [n for n in names if not n.startswith(("persona:", "samesex:"))]
    assert len(grid) == 2 * 5 * (1 + 4 + 8 + 32)
    ss = dict(s)["samesex:female:30:edu=bachelors"]
    assert ss["seeking"]["sex"] == "female" and ss["seeking"]["age"] == [28, 40]
