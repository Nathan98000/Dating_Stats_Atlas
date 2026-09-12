"""API tests against the pinned fixture build — §8.2 contract shape."""
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
        for row in body["ranked"]:
            assert row["pool_moe"] > 0
            assert {"name", "rank", "score", "score_moe", "cv", "n_unweighted",
                    "tier", "allocation_purity", "comparator",
                    "contributions"} <= set(row)


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
