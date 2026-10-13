"""Phase 7 (R05): each lifestyle item's contribution, served beside the
pillars' (`unit_contributions`), so "What moved the score" can show cost of
living and social life by item without the browser adding two
contributions."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas import model as engine
from atlas.model.explain import LIFESTYLE_PILLARS, served_unit_contributions
from atlas.model.variants import rank_variants, select_variant
from atlas.model.preferences import SEX_LEVELS

GOLDEN = Path(__file__).resolve().parent / "golden"

LEGEND = {
    "pool_size": {"pillar": "pool", "direction": 1, "mover_phrase": "the size of the pool"},
    "match_propensity": {"pillar": "match", "direction": 1, "mover_phrase": "the compatibility figure"},
    "rent_1br": {"pillar": "cost", "direction": -1, "mover_phrase": "rent"},
    "rpp_goods": {"pillar": "cost", "direction": -1, "mover_phrase": "everyday prices"},
    "rpp_services_other": {"pillar": "cost", "direction": -1, "mover_phrase": "everyday prices"},
    "venues_per_100k": {"pillar": "reach", "direction": 1, "mover_phrase": "places to go out"},
    "pleasant_days": {"pillar": "weather", "direction": 1, "mover_phrase": "the weather"},
}


@pytest.fixture(scope="module")
def build():
    return engine.load_build(GOLDEN / "fixture_build")


@pytest.fixture(scope="module")
def vectors():
    return json.loads((GOLDEN / "goldens.json").read_text())["vectors"]


def test_everyday_prices_is_one_entry_the_sum_of_its_two_stats():
    ids = list(LEGEND)
    raw = [9.0, 5.0, -2.654, 2.3849, 2.2649, 0.5, None]
    got = served_unit_contributions(ids, raw, LEGEND)
    assert got == [
        {"key": "rent_1br", "pillar": "cost", "value": -2.65},
        {"key": "rpp_goods", "pillar": "cost", "value": 4.65},
        {"key": "venues_per_100k", "pillar": "reach", "value": 0.5},
    ]


def test_no_lifestyle_contribution_serves_nothing():
    ids = list(LEGEND)
    raw = [9.0, 5.0, None, None, None, None, None]
    assert served_unit_contributions(ids, raw, LEGEND) == []


def test_items_add_up_to_their_pillar_on_every_golden_search(build, vectors):
    rows = 0
    for v in vectors:
        res = engine.rank(build, engine.parse_request(v["request"]))
        for r in res["ranked"]:
            rows += 1
            pillars = {c["pillar"]: c["value"] for c in r["contributions"]}
            units = r["unit_contributions"]
            assert {u["pillar"] for u in units} <= set(LIFESTYLE_PILLARS)
            # every lifestyle pillar the row has is split into its items
            assert {u["pillar"] for u in units} == {p for p in pillars if p in LIFESTYLE_PILLARS}
            for p in {u["pillar"] for u in units}:
                total = sum(u["value"] for u in units if u["pillar"] == p)
                assert abs(total - pillars[p]) <= 0.01 + 1e-9, (v["name"], r["cbsa"], p, total, pillars[p])
            keys = [u["key"] for u in units]
            assert len(keys) == len(set(keys))
            assert "rpp_services_other" not in keys
            # a chip's sign is its own item's sign
            by_key = {u["key"]: u["value"] for u in units}
            for m in r["lifestyle_movers"]:
                assert m["key"] in by_key and m["sign"] * by_key[m["key"]] > 0, (v["name"], r["cbsa"], m)
    assert rows > 0


def test_no_variant_changes_them(build, vectors):
    """The field rides on the shared row: rank() for each own sex gives
    the same items as the variant response serves."""
    for v in vectors[:6]:
        req = engine.parse_request(v["request"])
        resp = rank_variants(build, req)
        for sex in SEX_LEVELS:
            sel = select_variant(resp, sex=sex)
            body = json.loads(json.dumps(v["request"]))
            body["self"]["sex"] = sex
            body["self"].pop("education", None)
            body["self"].pop("race_ethnicity", None)
            body["seeking"]["sex"] = resp["variants"]["sought_sex"]
            single = engine.rank(build, engine.parse_request(body))
            want = {r["cbsa"]: r["unit_contributions"] for r in single["ranked"]}
            assert {r["cbsa"]: r["unit_contributions"] for r in sel["ranked"]} == want, v["name"]
