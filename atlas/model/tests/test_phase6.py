"""Phase 6 (m4.3.0): the result chips' lifestyle movers and the spoken
population figures."""
from __future__ import annotations

from atlas.model.explain import (TOP_STATS_MIN_POINTS, mover_units, pick_lifestyle_movers,
                                 pick_movers)
from atlas.model.spoken import spoken_pop

LEGEND = {
    "pool_size": {"pillar": "pool", "direction": 1, "mover_phrase": "the size of the pool"},
    "match_propensity": {"pillar": "match", "direction": 1, "mover_phrase": "the compatibility figure"},
    "rent_1br": {"pillar": "cost", "direction": -1, "mover_phrase": "rent"},
    "rpp_goods": {"pillar": "cost", "direction": -1, "mover_phrase": "everyday prices"},
    "rpp_services_other": {"pillar": "cost", "direction": -1, "mover_phrase": "everyday prices"},
    "venues_per_100k": {"pillar": "reach", "direction": 1, "mover_phrase": "places to go out"},
    "pleasant_days": {"pillar": "weather", "direction": 1, "mover_phrase": "the weather"},
    "students_per_1k_adults": {"pillar": "students", "direction": 1, "mover_phrase": "the student crowd"},
}
IDS = list(LEGEND)
UNITS = mover_units(IDS, LEGEND)
PHRASES = [u["phrase"] for u in UNITS]


def at(*pairs):
    """Item contributions by phrase (others None) and sides all 0."""
    c = [None] * len(UNITS)
    for phrase, v in pairs:
        c[PHRASES.index(phrase)] = v
    return c, [0] * len(UNITS)


def names(picked):
    return [PHRASES[u] for u in picked]


def test_price_levels_stay_one_item():
    assert PHRASES.count("everyday prices") == 1
    unit = UNITS[PHRASES.index("everyday prices")]
    assert unit["ids"] == ["rpp_goods", "rpp_services_other"] and unit["pillar"] == "cost"


def test_lifestyle_pick_skips_pool_and_compatibility():
    c, s = at(("the size of the pool", 9.0), ("the compatibility figure", 6.0), ("rent", -3.0),
              ("places to go out", 2.0), ("the weather", 1.0), ("the student crowd", 0.8))
    assert names(pick_movers(c, s)) == ["the size of the pool", "the compatibility figure", "rent"]
    assert names(pick_lifestyle_movers(c, s, UNITS)) == ["places to go out", "the weather", "rent"]


def test_two_pluses_largest_first_then_the_biggest_minus():
    c, s = at(("the weather", 1.0), ("places to go out", 4.0), ("the student crowd", 2.0),
              ("rent", -1.0), ("everyday prices", -2.5))
    assert names(pick_lifestyle_movers(c, s, UNITS)) == ["places to go out", "the student crowd",
                                                         "everyday prices"]


def test_threshold_and_sides_rule_apply():
    c, s = at(("places to go out", TOP_STATS_MIN_POINTS - 0.01), ("rent", -2.0))
    assert names(pick_lifestyle_movers(c, s, UNITS)) == ["rent"]
    # a minus where the city's card says better than most is never named
    s[PHRASES.index("rent")] = 1
    assert pick_lifestyle_movers(c, s, UNITS) == []


def test_no_lifestyle_mover_is_empty():
    c, s = at(("the size of the pool", 9.0), ("the compatibility figure", -4.0))
    assert pick_lifestyle_movers(c, s, UNITS) == []


def test_spoken_two_significant_figures():
    assert spoken_pop(183_310) == "180,000"
    assert spoken_pop(125_160) == "130,000"
    assert spoken_pop(124_589) == "120,000"
    assert spoken_pop(80_123) == "80,000"
    assert spoken_pop(4_567_000) == "4.6 million"
    assert spoken_pop(1_281_004) == "1.3 million"


def test_spoken_floor_guard_for_unranked_metros():
    # Daphne and Prescott Valley sit just under the 250,000 floor
    assert spoken_pop(246_979) == "250,000"
    assert spoken_pop(246_979, ceiling=250_000) == "240,000"
    assert spoken_pop(245_424, ceiling=250_000) == "240,000"
    # a figure that rounds below the floor is untouched
    assert spoken_pop(183_310, ceiling=250_000) == "180,000"
