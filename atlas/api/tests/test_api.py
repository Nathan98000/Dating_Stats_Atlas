"""API tests against the pinned fixture build — the m2.1.0 contract
(ADR 0005 over ADR 0004)."""
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
    assert len(m["features"]["median_gross_rent"]["band_labels"]) == 5
    assert m["features"]["median_gross_rent"]["band_direction"] == "good_low"
    assert m["pillars"]["balance"]["display_name"] == "Dating pool balance"
    # the four importance controls carry their registry subtitles (item 4)
    assert m["controls"]["importance_pillars"] == \
        ["cost", "reach", "students", "weather"]
    for p in m["controls"]["importance_pillars"]:
        assert m["pillars"][p].get("control_subtitle"), p
    assert m["pillars"]["reach"]["display_name"] == "Social life"
    assert m["city_cards"][0] == "median_gross_rent"
    assert m["controls"]["marital"] == ["never_married", "previously_married"]
    assert m["controls"]["race_ethnicity"] == list(api.SELECTABLE_RACES)
    # m2.2.0: eight equal groups, labels from the registry (ADR 0006)
    assert [g["id"] for g in m["race_groups"]] == list(api.SELECTABLE_RACES)
    assert len(m["race_groups"]) == 8
    assert all(g["label"] for g in m["race_groups"])
    assert set(m["controls"]["importance_levels"]) == \
        {"not_much", "some", "a_lot"}
    # registry strings merge into the one policy-strings lookup (item 8's
    # ground rule: every new string lives in the registry)
    for k in ("slider_info", "crime_caution", "crime_compare_note",
              "stat_page_link", "stat_page_intro"):
        assert m["policy_strings"].get(k), k
    assert m["stat_pages"] and "who_lives_here" in m["stat_pages"]
    assert not any("crime" in s for s in m["stat_pages"])
    assert 0 < m["crime"]["coverage_floor"] < 1
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


def test_eight_race_groups_selectable_and_equal(client):
    """m2.2.0 (ADR 0006): the two formerly always-counted groups are
    ordinary checkboxes; empty and all-eight both mean no filter."""
    r = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 32},
        "seeking": {"age": [30, 40], "marital": ["never_married"],
                    "race_ethnicity": ["two_or_more_nh"]}})
    assert r.status_code == 200
    r2 = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 32},
        "seeking": {"age": [30, 40], "marital": ["never_married"],
                    "race_ethnicity": ["other_nh", "two_or_more_nh"]}})
    assert r2.status_code == 200
    rall = client.post("/v1/rank", json={
        "self": {"sex": "female", "age": 30},
        "seeking": {"age": [28, 40], "marital": ["never_married"]}})
    for body in (
        {"self": {"sex": "female", "age": 30},
         "seeking": {"age": [28, 40], "marital": ["never_married"],
                     "race_ethnicity": []}},
        {"self": {"sex": "female", "age": 30},
         "seeking": {"age": [28, 40], "marital": ["never_married"],
                     "race_ethnicity": list(api.SELECTABLE_RACES)}},
    ):
        resp = client.post("/v1/rank", json=body)
        assert resp.status_code == 200
        got = {x["cbsa"]: x["pool"] for x in resp.json()["ranked"]}
        want = {x["cbsa"]: x["pool"] for x in rall.json()["ranked"]}
        assert got == want, "empty and all-eight are the unfiltered universe"


def test_named_controls_and_conflicts(client):
    ok = client.post("/v1/rank", json={
        **BODY, "pool_vs_balance": 0.7,
        "importance": {"cost": "a_lot", "reach": "not_much",
                       "students": "a_lot", "weather": "not_much"}})
    assert ok.status_code == 200
    w = ok.json()["weights"]
    assert w["balance"] > w["pool"]
    assert w["cost"] > w["reach"] > 0
    assert w["students"] > w["weather"] > 0, (
        "students at a_lot with weather at not_much must order that way — "
        "the split's whole point")
    # the m2.0.0 bundled control: accepted as an alias for exactly this
    # version, contradiction with either half refused
    alias = client.post("/v1/rank", json={
        **BODY, "importance": {"lifestyle": "a_lot"}})
    assert alias.status_code == 200
    wa = alias.json()["weights"]
    assert wa["weather"] > w["weather"] and wa["students"] > 0
    clash = client.post("/v1/rank", json={
        **BODY, "importance": {"lifestyle": "a_lot", "weather": "some"}})
    assert clash.status_code == 422
    # size_vs_odds served its one deprecation version (m2.0.0) and is gone
    svo = client.post("/v1/rank", json={**BODY, "size_vs_odds": 0.5})
    assert svo.status_code == 422
    both = client.post("/v1/rank", json={
        **BODY, "weights": {"pool": 1.0}, "pool_vs_balance": 0.5})
    assert both.status_code == 422


def test_crime_block_served_never_scored(client):
    """Item 5 through HTTP: every row carries the composed crime block
    (figures + coverage + caution, or the blank state), crime never
    appears among the scored stats, and the weights never name it."""
    r = client.post("/v1/rank", json=BODY).json()
    assert set(r["weights"]) == {"pool", "balance", "reach", "cost",
                                 "weather", "students"}
    for row in r["ranked"] + r["suppressed"]:
        blk = row["crime"]
        assert "caution" in blk
        if blk["available"]:
            assert "coverage_line" in blk and len(blk["stats"]) == 2
        else:
            assert blk["note"]
        for s in row.get("stats", []):
            assert "crime" not in s["id"]


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
