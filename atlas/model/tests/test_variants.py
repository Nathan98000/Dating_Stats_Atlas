"""m4.0.0 (ADR 0018): the variant engine — every "about you" variant of a
search, computed at once and selected in the browser. The exactness of
every variant against rank() runs through HTTP in api/tests; here, the
parts it rests on: the variant index and its de-duplication, the default
variant, the vectorised rounding (equal to Python's round, halves
included) and the movers' encoding."""
import json
from pathlib import Path

import numpy as np
import pytest

from atlas import model as engine
from atlas.model.explain import (TOP_STATS_MAX, mover_units, pick_movers, served_movers,
                                 summary_line, unit_contributions)
from atlas.model.scoring import scored_features
from atlas.model.variants import (EDU_KEYS, RACE_KEYS, _explain_codes, _explain_entry,
                                  _explain_key, _explain_of_key, _round_list, _unit_sums,
                                  default_variant,
                                  rank_variants, select_variant, variant_list)

FIXTURE_DIR = Path(__file__).resolve().parent / "golden" / "fixture_build"
BODY = {"self": {"age": 30},
        "seeking": {"sex": "male", "age": [28, 40],
                    "marital": ["never_married", "previously_married"]}}


@pytest.fixture(scope="module")
def build():
    return engine.load_build(FIXTURE_DIR)


def test_fifty_variants_with_same_sex_race_as_one(build):
    variants, index = variant_list(build, "male")
    assert len(variants) == 50
    # opposite-sex (a woman seeking men): 5 educations x 9 race settings
    assert len({index["female"][e][r] for e in EDU_KEYS for r in RACE_KEYS}) == 45
    # same-sex (a man seeking men): race is never used, so 5
    assert len({index["male"][e][r] for e in EDU_KEYS for r in RACE_KEYS}) == 5
    for e in EDU_KEYS:
        assert len({index["male"][e][r] for r in RACE_KEYS}) == 1
    assert default_variant("male") == ("female", "none", "off")
    assert default_variant("female") == ("male", "none", "off")


def test_the_response_names_its_default_and_sought_sex(build):
    resp = rank_variants(build, engine.parse_request(BODY))
    V = resp["variants"]
    assert V["sought_sex"] == "male"
    assert V["list"][V["default"]]["key"] == "female|none|off"
    # the rows are sent in the default variant's order
    d = V["default"]
    assert V["columns"]["order"][d] == list(range(len(resp["ranked"])))
    # a visitor who has told the site nothing sees the default variant
    assert select_variant(resp) == select_variant(resp, "female", None, None)


def test_round_list_is_pythons_round():
    rng = np.random.default_rng(7)
    x = np.concatenate([rng.normal(0, 60, 20000), rng.uniform(-3, 3, 20000),
                        # exact halves and near-halves, where rint of the
                        # product and Python's decimal rounding can part
                        np.arange(-200, 200) / 200.0 + 0.005, np.arange(-50, 50) * 0.05,
                        np.array([2.675, 1.005, 0.125, -0.125, 67.45, 100.005, 249.995])])
    for nd in (1, 2):
        assert _round_list(x, nd) == [round(float(v), nd) for v in x]


def test_movers_encoding_is_explains_rule(build):
    """The vectorised movers (explain codes) pick the items explain.movers
    picks, in its order — the price pair added as one item, an item whose
    sign contradicts its card left out — and the code's entry is the line
    and top_stats built from the row's own stats (m4.1.1), and the served
    movers (m4.2.1: two pluses at most, then the biggest minus)."""
    rng = np.random.default_rng(11)
    ids = [f["id"] for f in scored_features(build)]
    units = mover_units(ids, build.legend)
    assert len(units) == len(ids) - 1, "goods and services prices are one item"
    F, U = len(ids), len(units)
    C = np.round(rng.normal(0, 3, (600, F)), 2)
    C[rng.random((600, F)) < 0.1] = np.nan
    C[:, 3] = np.where(rng.random(600) < 0.3, C[:, 1], C[:, 3])  # ties
    S = rng.integers(-1, 2, (600, U)).astype(float)
    keys = _explain_key(_explain_codes(_unit_sums(C, units), S))
    for i in range(600):
        contribs = [None if np.isnan(C[i, j]) else float(C[i, j]) for j in range(F)]
        uc = unit_contributions(contribs, units)
        moved = [{"phrase": units[u]["phrase"], "ids": units[u]["ids"], "contribution": uc[u]}
                 for u in pick_movers(uc, [int(x) for x in S[i]])]
        entry = _explain_entry(_explain_of_key(int(keys[i]), TOP_STATS_MAX), units)
        assert entry["top_stats"] == [fid for m in moved for fid in m["ids"]]
        assert entry["summary_line"] == summary_line(moved)
        assert entry["movers"] == served_movers(moved)
        signs = [m["sign"] for m in entry["movers"]]
        assert signs.count(1) <= 2 and signs.count(-1) <= 1 and signs == sorted(signs, reverse=True)


def test_no_about_you_detail_in_the_request_shape(build):
    """The request the site sends names no detail about the visitor; the
    model reads the own age and the sought sex, nothing else of `self`."""
    req = engine.parse_request(BODY)
    assert req.self_sex is None and req.self_edu is None and req.self_race is None
    with pytest.raises(ValueError):
        engine.parse_request({"self": {"age": 30},
                              "seeking": {"age": [28, 40], "marital": ["never_married"]}})
    token = engine.permalink("dv", "mv", BODY).rsplit("/", 1)[1]
    import base64
    core = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
    assert core["self"] == {"age": 30}


def test_score_median_is_the_middle_of_each_variants_ranked_scores(build):
    """Phase 5 (commit I): each variant carries the median overall score of
    the cities ranked for the search, from the same unrounded scores the
    rows' scores round — value to one decimal, display a whole number —
    and select_variant hands it on; nothing else moves."""
    resp = rank_variants(build, engine.parse_request(BODY))
    for vi, v in enumerate(resp["variants"]["list"]):
        sex, edu, race = v["sex"], v["education"], v["race_ethnicity"]
        me = {"sex": sex, "age": BODY["self"]["age"]}
        if edu:
            me["education"] = edu
        if race:
            me["race_ethnicity"] = race
        want = engine.rank(build, engine.parse_request({**BODY, "self": me}))
        assert v["score_median"] == want["score_median"]
        scores = [r["score"] for r in want["ranked"]]
        assert abs(v["score_median"]["value"] - float(np.median(scores))) <= 0.051
        assert abs(float(v["score_median"]["display"]) - v["score_median"]["value"]) <= 0.5
        assert select_variant(resp, sex, edu, race)["score_median"] == v["score_median"]
