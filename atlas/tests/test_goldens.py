"""Golden tests: twelve pinned request vectors against the pinned 12-metro
fixture. Exact rankings and exact suppression behaviour. A model change that
moves any of these fails until MODEL_VERSION is bumped and goldens are
regenerated (atlas/tests/make_fixture.py) with a note in the commit.
"""
import json

import pytest

import score as engine
from conftest import FIXTURE_DIR, GOLDENS


@pytest.fixture(scope="module")
def build():
    return engine.load_build(FIXTURE_DIR)


@pytest.fixture(scope="module")
def goldens():
    return json.loads(GOLDENS.read_text())


def test_model_version_pinned(goldens):
    assert goldens["model_version"] == engine.MODEL_VERSION, (
        "MODEL_VERSION changed without regenerating goldens "
        "(run atlas/tests/make_fixture.py and note the bump in the commit)")


def test_fixture_has_twelve_metros(build):
    assert len(build.metro_levels) == 12


def test_goldens_cover_required_shapes(goldens):
    vecs = goldens["vectors"]
    assert len(vecs) == 12
    race_filtered = [v for v in vecs if v["request"]["pool"].get("race")]
    assert len(race_filtered) >= 3
    assert any(len(v["expect"]["suppressed"]) >= 6 for v in vecs), (
        "at least one vector must sit below the suppression bar")


def test_exact_rankings_and_suppression(build, goldens):
    for v in goldens["vectors"]:
        req = v["request"]
        res = engine.rank(build, req["seeker"]["sex"], req["seeker"]["age"],
                          req["pool"], req.get("weights"))
        exp = v["expect"]
        got_ranked = [r["cbsa"] for r in res["ranked"]]
        assert got_ranked == exp["ranked_cbsas"], f"{v['name']}: ranking moved"
        got_scores = {r["cbsa"]: r["score"] for r in res["ranked"]}
        for cb, s in exp["scores"].items():
            assert abs(got_scores[cb] - s) < 5e-5, f"{v['name']}: score moved for {cb}"
        assert sorted(r["cbsa"] for r in res["shown_unranked"]) == \
            exp["shown_unranked_cbsas"], f"{v['name']}: middle tier moved"
        got_sup = {r["cbsa"]: r["reason"] for r in res["suppressed"]}
        assert got_sup == exp["suppressed"], f"{v['name']}: suppression moved"
        assert res["counts"] == exp["counts"], f"{v['name']}: counts moved"
