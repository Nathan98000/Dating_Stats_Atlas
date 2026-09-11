"""API tests against the pinned fixture build."""
import json
import os

import pytest

from conftest import FIXTURE_DIR, GOLDENS

os.environ["BUILD_DIR"] = str(FIXTURE_DIR)

from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(api.app)


def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["metros"] == 12
    assert body["model_version"] == json.loads(GOLDENS.read_text())["model_version"]


def test_rank_matches_goldens_through_http(client):
    goldens = json.loads(GOLDENS.read_text())
    for v in goldens["vectors"][:4]:
        req = v["request"]
        payload = {"seeker": req["seeker"], "pool": req["pool"]}
        if req.get("weights"):
            payload["weights"] = req["weights"]
        r = client.post("/v1/rank", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert [x["cbsa"] for x in body["ranked"]] == v["expect"]["ranked_cbsas"]
        assert {x["cbsa"]: x["reason"] for x in body["suppressed"]} == \
            v["expect"]["suppressed"]
        assert set(body) >= {"ranked", "shown_unranked", "suppressed", "counts",
                             "data_version", "model_version"}


def test_income_floor_validation(client):
    r = client.post("/v1/rank", json={
        "seeker": {"sex": "female", "age": 32},
        "pool": {"age_min": 30, "age_max": 40, "marital": "not_married",
                 "income_min": 60000}})
    assert r.status_code == 422


def test_age_bounds_validation(client):
    r = client.post("/v1/rank", json={
        "seeker": {"sex": "female", "age": 17},
        "pool": {"age_min": 30, "age_max": 40, "marital": "any"}})
    assert r.status_code == 422
    r = client.post("/v1/rank", json={
        "seeker": {"sex": "female", "age": 30},
        "pool": {"age_min": 40, "age_max": 30, "marital": "any"}})
    assert r.status_code == 422
