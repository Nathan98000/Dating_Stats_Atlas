"""API tests against the pinned fixture build — the m2.0.0 contract
(ADR 0004)."""
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

BODY = {"self": {"sex": "female", "age": 30},
        "seeking": {"age": [28, 40],
                    "marital": ["never_married", "previously_married"]}}


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


def test_meta_carries_the_v3_vocabulary(client):
    m = client.get("/v1/meta").json()
    assert m["features"]["pool_balance"]["display_name"] == "Dating pool balance"
    assert m["features"]["median_gross_rent"]["display_name"] == "Rent"
    assert m["features"]["median_gross_rent"]["band_labels"][0] == \
        "Cheaper than most cities"
    assert m["pillars"]["balance"]["display_name"] == "Dating pool balance"
    assert m["city_cards"][0] == "median_gross_rent"
    assert m["controls"]["marital"] == ["never_married", "previously_married"]
    assert m["controls"]["race_ethnicity"] == list(api.SELECTABLE_RACES)
    assert set(m["controls"]["importance_levels"]) == \
        {"not_much", "some", "a_lot"}
    # technical wording exists for the record and stays out of the
    # rendered vocabulary
    assert "at least" in m["technical_strings"]["interval"]
    assert "margin" not in json.dumps(m["policy_strings"]).lower()
    for metro in m["metros"]:
        for k in ("display_name", "display_name_full", "slug", "description"):
            assert metro.get(k)


def test_rank_matches_goldens_through_http(client):
    goldens = json.loads(GOLDENS.read_text())
    for v in goldens["vectors"][:5]:
        r = client.post("/v1/rank", json=v["request"])
        assert r.status_code == 200, r.text
        body = r.json()
        assert [x["cbsa"] for x in body["ranked"]] == v["expect"]["ranked_cbsas"]
        assert {x["cbsa"]: x["reason"] for x in body["suppressed"]} == \
            v["expect"]["suppressed"]
        assert body["shown_unranked"] == []
        assert sum(body["counts"]["suppressed_by_reason"].values()) == \
            body["counts"]["suppressed"]
        for row in body["ranked"]:
            assert {"display_name", "slug", "score_display", "balance",
                    "summary_line", "cards"} <= set(row)
            assert "cross_group_pairing_rate" not in row
            assert "ratio" not in row and "rivals" not in row


def test_sort_reverses_without_changing_ranks(client):
    """Gate 3: worst_first reverses the same ranked array — same cities,
    same scores, same ranks, never widened."""
    best = client.post("/v1/rank", json={**BODY, "sort": "best_first"}).json()
    worst = client.post("/v1/rank", json={**BODY, "sort": "worst_first"}).json()
    a = [(r["cbsa"], r["rank"], r["score"]) for r in best["ranked"]]
    b = [(r["cbsa"], r["rank"], r["score"]) for r in worst["ranked"]]
    assert b == list(reversed(a))
    assert best["counts"] == worst["counts"]
    assert worst["ranked"][0]["rank"] == len(a), (
        "the city shown first under worst-first keeps its earned rank")


def test_marital_restricted_to_two_values(client):
    r = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 32},
        "seeking": {"age": [30, 40], "marital": ["currently_married"]}})
    assert r.status_code == 422


def test_always_counted_race_groups_not_selectable(client):
    r = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 32},
        "seeking": {"age": [30, 40], "marital": ["never_married"],
                    "race_ethnicity": ["two_or_more_nh"]}})
    assert r.status_code == 422
    # zero-of-six arrives as an empty list: treated as no filter, not as
    # the two always-on groups alone
    r0 = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 30},
        "seeking": {"age": [28, 40], "marital": ["never_married"],
                    "race_ethnicity": []}})
    rall = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 30},
        "seeking": {"age": [28, 40], "marital": ["never_married"]}})
    assert r0.status_code == 200
    p0 = {x["cbsa"]: x["pool"] for x in r0.json()["ranked"]}
    pall = {x["cbsa"]: x["pool"] for x in rall.json()["ranked"]}
    assert p0 == pall


def test_named_controls_and_conflicts(client):
    ok = client.post("/v1/rank", json={
        **BODY, "pool_vs_balance": 0.7,
        "importance": {"cost": "a_lot", "reach": "not_much",
                       "lifestyle": "some"}})
    assert ok.status_code == 200
    w = ok.json()["weights"]
    assert w["balance"] > w["pool"]
    assert w["cost"] > w["reach"] > 0
    conflict = client.post("/v1/rank", json={
        **BODY, "pool_vs_balance": 0.5, "size_vs_odds": 0.5})
    assert conflict.status_code == 422
    both = client.post("/v1/rank", json={
        **BODY, "weights": {"pool": 1.0}, "pool_vs_balance": 0.5})
    assert both.status_code == 422


def test_income_floor_validation(client):
    r = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 32},
        "seeking": {"age": [30, 40], "marital": ["never_married"],
                    "income_min": 60000}})
    assert r.status_code == 422


def test_version_pin_mismatch_409(client):
    r = client.post("/v1/rank", json={
        "data_version": "not-a-build", **BODY})
    assert r.status_code == 409


def test_build_fallback_refuses_to_guess(tmp_path, monkeypatch):
    for name in ("aaa111", "bbb222"):
        d = tmp_path / name
        d.mkdir()
        (d / "manifest.json").write_text("{}")
        (d / "pool_cube.npy").write_bytes(b"x")
    monkeypatch.delenv("BUILD_DIR", raising=False)
    monkeypatch.setattr(api, "BUILDS_DEFAULT", tmp_path)
    with pytest.raises(RuntimeError, match="refusing to guess"):
        api._resolve_build_dir()
