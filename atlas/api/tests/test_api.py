"""API tests against the pinned fixture build — §8.2 contract shape as
amended by ADRs 0002/0003."""
import json
import os
from pathlib import Path

import pytest

FIXTURE_DIR = (Path(__file__).resolve().parents[2] / "model" / "tests"
               / "golden" / "fixture_build")
GOLDENS = (Path(__file__).resolve().parents[2] / "model" / "tests"
           / "golden" / "goldens.json")

os.environ["BUILD_DIR"] = str(FIXTURE_DIR)

from fastapi.testclient import TestClient  # noqa: E402

from atlas.api import app as api  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(api.app)


def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["metros"] == 12
    assert body["model_version"] == json.loads(GOLDENS.read_text())["model_version"]
    assert body["interval"]["coverage"] >= 0.95


def test_meta_carries_legend_and_policy(client):
    r = client.get("/v1/meta")
    assert r.status_code == 200
    m = r.json()
    for fid in ("pool_size", "partners_per_rival", "median_gross_rent",
                "cross_group_pairing_rate", "crime_rate_context"):
        e = m["features"][fid]
        assert e["display_name"] and e["definition"], fid
        assert e["provenance"]["source"], fid
    assert m["pillars"]["balance"]["display_name"] == "Odds"
    assert "at least" in m["policy_strings"]["interval"]
    assert m["controls"]["income_band_edges"] == [25000, 50000, 75000,
                                                  100000, 150000, 250000]
    assert len(m["metros"]) == 12
    assert m["tier_policy"]["suppress"].startswith("min(n_alloc, kish) < 100")


def test_rank_matches_goldens_through_http(client):
    goldens = json.loads(GOLDENS.read_text())
    for v in goldens["vectors"][:5]:
        r = client.post("/v1/rank", json=v["request"])
        assert r.status_code == 200, r.text
        body = r.json()
        assert [x["cbsa"] for x in body["ranked"]] == v["expect"]["ranked_cbsas"]
        assert {x["cbsa"]: x["reason"] for x in body["suppressed"]} == \
            v["expect"]["suppressed"]
        assert body["permalink"].startswith(
            f"/r/{body['data_version']}/{body['model_version']}/")
        assert set(body) >= {"ranked", "shown_unranked", "suppressed", "counts",
                             "data_version", "model_version", "permalink"}
        assert body["shown_unranked"] == []
        assert sum(body["counts"]["suppressed_by_reason"].values()) == \
            body["counts"]["suppressed"]
        for row in body["ranked"]:
            assert row["pool_moe"] > 0
            assert {"name", "rank", "score", "score_moe", "cv", "n_unweighted",
                    "tier", "allocation_purity", "contributions",
                    "stats"} <= set(row)
            assert "comparator" not in row


def test_race_filter_serves_counterweight(client):
    goldens = json.loads(GOLDENS.read_text())
    v = next(x for x in goldens["vectors"] if "cross_group" in x["expect"])
    r = client.post("/v1/rank", json=v["request"])
    body = r.json()
    rows = {x["cbsa"]: x for x in body["ranked"]}
    for cbsa, exp in v["expect"]["cross_group"].items():
        got = rows[cbsa]
        if exp is None:
            assert got["cross_group_pairing_rate"] is None
        else:
            assert got["cross_group_pairing_rate"] == exp[0]
            assert got["cross_group_pairing_moe"] == exp[1]


def test_income_floor_validation(client):
    r = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 32},
        "seeking": {"age": [30, 40], "marital": ["never_married"],
                    "income_min": 60000}})
    assert r.status_code == 422


def test_religion_not_yet(client):
    r = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 32},
        "seeking": {"age": [30, 40], "marital": ["never_married"],
                    "religion": "any"}})
    assert r.status_code == 422


def test_weights_and_slider_conflict(client):
    r = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 32},
        "seeking": {"age": [30, 40], "marital": ["never_married"]},
        "weights": {"pool": 1.0}, "size_vs_odds": 0.5})
    assert r.status_code == 422


def test_version_pin_mismatch_409(client):
    r = client.post("/v1/rank", json={
        "data_version": "not-a-build",
        "self": {"sex": "female", "age": 32},
        "seeking": {"age": [30, 40], "marital": ["never_married"]}})
    assert r.status_code == 409


def test_age_bounds_validation(client):
    r = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 17},
        "seeking": {"age": [30, 40], "marital": ["never_married"]}})
    assert r.status_code == 422
    r = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 30},
        "seeking": {"age": [40, 30], "marital": ["never_married"]}})
    assert r.status_code == 422


def test_build_fallback_refuses_to_guess(tmp_path, monkeypatch):
    """BUILD_DIR unset + more than one complete build = a refusal, never a
    silent mtime race (Phase 2b item 10)."""
    for name in ("aaa111", "bbb222"):
        d = tmp_path / name
        d.mkdir()
        (d / "manifest.json").write_text("{}")
        (d / "pool_cube.npy").write_bytes(b"x")
    # a retired build (manifest kept, cubes removed) is not a candidate
    retired = tmp_path / "retired0"
    retired.mkdir()
    (retired / "manifest.json").write_text("{}")
    monkeypatch.delenv("BUILD_DIR", raising=False)
    monkeypatch.setattr(api, "BUILDS_DEFAULT", tmp_path)
    with pytest.raises(RuntimeError, match="refusing to guess"):
        api._resolve_build_dir()
    (tmp_path / "bbb222" / "pool_cube.npy").unlink()
    (tmp_path / "bbb222" / "manifest.json").unlink()
    (tmp_path / "bbb222").rmdir()
    assert api._resolve_build_dir().name == "aaa111"
