"""Golden tests (m1.1.0): twelve pinned §8.2 request vectors against the
pinned 12-metro fixture. Exact rankings, scores, intervals and suppression.
A model change that moves any of these fails until MODEL_VERSION is bumped
and goldens are regenerated (make_fixture.py) with a note in the commit.
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


def test_fixture_has_twelve_metros(build):
    assert len(build.metro_levels) == 12


def test_goldens_cover_required_shapes(goldens):
    vecs = goldens["vectors"]
    assert len(vecs) == 12
    race_filtered = [v for v in vecs
                     if v["request"]["seeking"].get("race_ethnicity")]
    assert len(race_filtered) >= 3
    assert any(len(v["expect"]["suppressed"]) >= 6 for v in vecs)
    assert any("size_vs_odds" in v["request"] for v in vecs)


def test_exact_rankings_scores_and_suppression(build, goldens):
    for v in goldens["vectors"]:
        res = engine.rank(build, engine.parse_request(v["request"]))
        exp = v["expect"]
        got_ranked = [r["cbsa"] for r in res["ranked"]]
        assert got_ranked == exp["ranked_cbsas"], f"{v['name']}: ranking moved"
        for r in res["ranked"]:
            assert abs(r["score"] - exp["scores"][r["cbsa"]]) < 0.05, (
                f"{v['name']}: score moved for {r['cbsa']}")
            assert r["pool"] == exp["pools"][r["cbsa"]], (
                f"{v['name']}: pool moved for {r['cbsa']}")
            assert r["pool_moe"] == exp["pool_moes"][r["cbsa"]], (
                f"{v['name']}: served interval moved for {r['cbsa']}")
        assert sorted(r["cbsa"] for r in res["shown_unranked"]) == \
            exp["shown_unranked_cbsas"], f"{v['name']}: middle tier moved"
        assert {r["cbsa"]: r["reason"] for r in res["suppressed"]} == \
            exp["suppressed"], f"{v['name']}: suppression moved"
        assert res["counts"] == exp["counts"], f"{v['name']}: counts moved"


def test_every_ranked_row_carries_the_contract(build, goldens):
    body = goldens["vectors"][0]["request"]
    res = engine.rank(build, engine.parse_request(body))
    for r in res["ranked"]:
        for key in ("cbsa", "name", "rank", "score", "score_moe", "pool",
                    "pool_moe", "cv", "n_unweighted", "tier", "ratio",
                    "allocation_purity", "comparator", "contributions",
                    "explanation", "flags"):
            assert key in r, f"ranked row missing {key}"
        assert r["tier"] == "measured"
        assert r["pool_moe"] > 0, "a population figure shipped without an interval"
        assert r["cross_group_pairing_rate"] is None  # Phase 3
