"""Golden tests (m2.1.0): fourteen pinned request vectors against the
pinned 12-metro fixture. Exact rankings, scores, pools, balance figures,
summary lines and suppression. A model change that moves any of these
fails until MODEL_VERSION is bumped and goldens are regenerated
(make_fixture.py) with a note in the commit.
"""
import json
from pathlib import Path

import pytest

from atlas import model as engine

FIXTURE_DIR = Path(__file__).resolve().parent / "fixture_build"
GOLDENS = Path(__file__).resolve().parent / "goldens.json"


@pytest.fixture(scope="module")
def build():
    return engine.load_build(FIXTURE_DIR)


@pytest.fixture(scope="module")
def goldens():
    return json.loads(GOLDENS.read_text())


def test_model_version_pinned(goldens):
    assert goldens["model_version"] == engine.MODEL_VERSION, (
        "MODEL_VERSION changed without regenerating goldens "
        "(run make_fixture.py and note the bump in the commit)")


def test_goldens_cover_required_shapes(goldens):
    vecs = goldens["vectors"]
    assert len(vecs) == 14
    race_filtered = [v for v in vecs
                     if v["request"]["seeking"].get("race_ethnicity")]
    assert len(race_filtered) >= 3
    assert any(len(v["expect"]["suppressed"]) >= 6 for v in vecs)
    assert not any("size_vs_odds" in v["request"] for v in vecs), (
        "size_vs_odds left the contract in m2.1.0 — its one deprecation "
        "version was m2.0.0")
    assert any("pool_vs_balance" in v["request"] for v in vecs)
    # the four m2.1.0 controls and the one-version lifestyle alias both
    # need pinned coverage (ADR 0005)
    assert any({"students", "weather"} <= set(v["request"].get("importance")
                                              or {}) for v in vecs)
    assert any("lifestyle" in (v["request"].get("importance") or {})
               for v in vecs)


def test_exact_rankings_scores_and_suppression(build, goldens):
    for v in goldens["vectors"]:
        res = engine.rank(build, engine.parse_request(v["request"]))
        exp = v["expect"]
        got_ranked = [r["cbsa"] for r in res["ranked"]]
        assert got_ranked == exp["ranked_cbsas"], f"{v['name']}: ranking moved"
        for r in res["ranked"]:
            assert abs(r["score"] - exp["scores"][r["cbsa"]]) < 0.05, (
                f"{v['name']}: score moved for {r['cbsa']}")
            assert r["score_display"] == exp["score_displays"][r["cbsa"]]
            assert r["pool"] == exp["pools"][r["cbsa"]], (
                f"{v['name']}: pool moved for {r['cbsa']}")
            assert r["pool_moe"] == exp["pool_moes"][r["cbsa"]], (
                f"{v['name']}: served interval moved for {r['cbsa']}")
            want_bal = exp["balance_per_100"][r["cbsa"]]
            got_bal = (r["balance"]["per_100"]
                       if r["balance"]["available"] else None)
            assert got_bal == want_bal, (
                f"{v['name']}: balance moved for {r['cbsa']}")
        for cbsa, line in exp["summary_lines"].items():
            got = next(r for r in res["ranked"] if r["cbsa"] == cbsa)
            assert got["summary_line"] == line, f"{v['name']}: movers moved"
        assert res["shown_unranked"] == []
        assert {r["cbsa"]: r["reason"] for r in res["suppressed"]} == \
            exp["suppressed"], f"{v['name']}: suppression moved"
        assert res["counts"] == exp["counts"], f"{v['name']}: counts moved"
        for r in res["suppressed"]:
            assert r["reason"] in ("n_below_100", "empty_pool"), (
                f"retired reason string produced: {r['reason']}")
        for cbsa, avail in exp.get("suppressed_balance_available", {}).items():
            row = next(r for r in res["suppressed"] if r["cbsa"] == cbsa)
            assert row["balance"]["available"] == avail


def test_every_ranked_row_carries_the_contract(build, goldens):
    body = goldens["vectors"][0]["request"]
    res = engine.rank(build, engine.parse_request(body))
    for r in res["ranked"]:
        for key in ("cbsa", "name", "display_name", "slug", "rank", "score",
                    "score_display", "pool", "pool_moe", "cv", "n_unweighted",
                    "tier", "balance", "allocation_purity", "contributions",
                    "summary_line", "flags", "stats", "cards", "top_stats"):
            assert key in r, f"ranked row missing {key}"
        for gone in ("ratio", "ratio_moe", "rivals", "comparator",
                     "cross_group_pairing_rate", "explanation"):
            assert gone not in r, f"{gone} left the contract in m2.0.0"
        assert r["pool_moe"] > 0, (
            "the interval machinery must keep computing (ADR 0004 hides "
            "margins, it does not delete them)")


def test_suppressed_rows_carry_balance_and_cards(build, goldens):
    below = next(v for v in goldens["vectors"]
                 if v["name"] == "below_bar_nhpi_250k")
    res = engine.rank(build, engine.parse_request(below["request"]))
    assert res["suppressed"], "stress vector no longer suppresses anything"
    for r in res["suppressed"]:
        assert "pool" not in r and "pool_moe" not in r
        assert "balance" in r and "cards" in r and "slug" in r
        for c in r["cards"]:
            assert c["id"] != "pool_size"
