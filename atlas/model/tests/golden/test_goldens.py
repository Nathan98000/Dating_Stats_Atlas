"""Golden tests (m1.2.0): twelve pinned §8.2 request vectors against the
pinned 12-metro fixture. Exact rankings, scores, intervals, suppression and
— for race-filtered vectors — the §10.4 counterweight. A model change that
moves any of these fails until MODEL_VERSION is bumped and goldens are
regenerated (make_fixture.py) with a note in the commit.
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
        assert res["shown_unranked"] == [], (
            "the middle tier is removed (ADR 0002); shown_unranked must be "
            "a permanently empty array")
        assert {r["cbsa"]: r["reason"] for r in res["suppressed"]} == \
            exp["suppressed"], f"{v['name']}: suppression moved"
        assert res["counts"] == exp["counts"], f"{v['name']}: counts moved"
        for r in res["suppressed"]:
            assert r["reason"] in ("n_below_100", "empty_pool", "no_rivals"), (
                f"retired reason string produced: {r['reason']}")


def test_counterweight_pinned_for_race_vectors(build, goldens):
    for v in goldens["vectors"]:
        if "cross_group" not in v["expect"]:
            continue
        res = engine.rank(build, engine.parse_request(v["request"]))
        rows = {r["cbsa"]: r for r in res["ranked"]}
        for cbsa, exp in v["expect"]["cross_group"].items():
            r = rows[cbsa]
            if exp is None:
                assert r["cross_group_pairing_rate"] is None
                assert r.get("cross_group_pairing_suppressed") == "n_below_100"
            else:
                assert r["cross_group_pairing_rate"] == exp[0], (
                    f"{v['name']}: pairing rate moved for {cbsa}")
                assert r["cross_group_pairing_moe"] == exp[1]
                assert r["cross_group_pairing_moe"] > 0, (
                    "a pairing rate shipped without its margin")
                assert r["cross_group_pairing_n"] == exp[2]


def test_every_ranked_row_carries_the_contract(build, goldens):
    body = goldens["vectors"][0]["request"]
    res = engine.rank(build, engine.parse_request(body))
    for r in res["ranked"]:
        for key in ("cbsa", "name", "rank", "score", "score_moe", "pool",
                    "pool_moe", "cv", "n_unweighted", "tier", "ratio",
                    "allocation_purity", "contributions", "explanation",
                    "flags", "stats"):
            assert key in r, f"ranked row missing {key}"
        assert "comparator" not in r, "D10 is retired (ADR 0003)"
        assert r["tier"] == "measured"
        assert r["pool_moe"] > 0, "a population figure shipped without an interval"
        assert r["cross_group_pairing_rate"] is None  # no race filter here
        scored = [s for s in r["stats"] if s.get("contribution") is not None]
        assert len(scored) >= 2
        # feature-level attribution present and pillar sums exact (ADR 0003)
        by_pillar = {}
        for s in scored:
            by_pillar[s["pillar"]] = by_pillar.get(s["pillar"], 0.0) + s["contribution"]
        for c in r["contributions"]:
            assert abs(by_pillar[c["pillar"]] - c["value"]) < 0.05, (
                "pillar contribution is not the sum of its features'")


def test_suppressed_rows_carry_stats_for_compare(build, goldens):
    """A suppressed metro is comparable on its static stats (ADR 0003) —
    with its pool figure replaced by the suppression state, never shown."""
    below = next(v for v in goldens["vectors"]
                 if v["name"] == "below_bar_nhpi_250k")
    res = engine.rank(build, engine.parse_request(below["request"]))
    assert res["suppressed"], "stress vector no longer suppresses anything"
    for r in res["suppressed"]:
        assert "pool" not in r and "pool_moe" not in r
        assert r["reason"] in ("n_below_100", "empty_pool", "no_rivals")
        assert "stats" in r and "name" in r
        for s in r["stats"]:
            assert s["id"] != "pool_size", (
                "a suppressed metro's stats must not carry a pool figure")
