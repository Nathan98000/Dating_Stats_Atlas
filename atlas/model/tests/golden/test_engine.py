"""Engine unit tests: schema contract, mask semantics, D05 slider,
interval conservatism rules, and the missing-data policy."""
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from atlas import model as engine
from atlas.model.intervals import IntervalModel
from atlas.model.preferences import slider_weights
from atlas.model.scoring import _effective_weights, _pillar_z
from atlas.model.suppression import tier_masks

FIXTURE_DIR = Path(__file__).resolve().parent / "fixture_build"


@pytest.fixture(scope="module")
def build():
    return engine.load_build(FIXTURE_DIR)


def test_schema_version_mismatch_refused(tmp_path):
    src = json.loads((FIXTURE_DIR / "manifest.json").read_text())
    src["schema_version"] = "cube-v0"
    (tmp_path / "manifest.json").write_text(json.dumps(src))
    with pytest.raises(AssertionError, match="schema"):
        engine.load_build(tmp_path)


def test_axis_reorder_refused(tmp_path):
    src = json.loads((FIXTURE_DIR / "manifest.json").read_text())
    src["axes"][4], src["axes"][5] = src["axes"][5], src["axes"][4]
    (tmp_path / "manifest.json").write_text(json.dumps(src))
    with pytest.raises(AssertionError):
        engine.load_build(tmp_path)


def test_mask_cardinalities():
    full = engine.mask_vector("male", 18, 70, frozenset({0, 1, 2}), None, None, None)
    assert full.sum() == engine.N_FLAT / 2
    nm = engine.mask_vector("female", 30, 34, frozenset({0}), "bachelors",
                            75000, None)
    assert nm.sum() == 5 * 1 * 2 * 4 * 8
    multi = engine.mask_vector("male", 28, 38, frozenset({0, 1}), "bachelors",
                               75000, ("nh_black", "nh_asian"))
    assert multi.sum() == 11 * 2 * 2 * 4 * 2


def test_income_floor_must_be_band_edge():
    with pytest.raises(AssertionError, match="band edge"):
        engine.mask_vector("male", 18, 70, frozenset({0}), None, 60000, None)


def test_slider_is_a_pure_function():
    defaults = {"pool": 0.30, "balance": 0.25, "reach": 0.20,
                "cost": 0.15, "lifestyle": 0.10}
    w0 = slider_weights(0.0, defaults, 0.55)
    w1 = slider_weights(1.0, defaults, 0.55)
    assert w0["pool"] == pytest.approx(0.55) and w0["balance"] == 0.0
    assert w1["balance"] == pytest.approx(0.55) and w1["pool"] == 0.0
    for w in (w0, w1):
        assert sum(w.values()) == pytest.approx(1.0)
        assert w["reach"] == 0.20 and w["cost"] == 0.15


def test_interval_conservative_composition():
    im = IntervalModel(
        feature_names=[], coef=np.zeros(14), race_levels=engine.RACE_LEVELS,
        offsets=np.zeros(3),
        inflation={"none": 1.1, "nh_black": 1.5, "nh_asian": 1.3},
        meta={})
    n = np.array([500.0, 500, 500]); k = n.copy(); sh = np.full(3, 0.01)
    single = im.served_rse(n, k, sh, frozenset({0, 1}), ["nh_black"])
    multi = im.served_rse(n, k, sh, frozenset({0, 1}), ["nh_black", "nh_asian"])
    assert (multi >= single - 1e-12).all()          # multi-select takes the max
    weird = im.served_rse(n, k, sh, frozenset({1}), None)   # non-canonical marital
    canon = im.served_rse(n, k, sh, frozenset({0, 1}), None)
    assert (weird >= canon - 1e-12).all()           # errs wide, never narrow


def test_tier_masks_full_policy():
    universe = np.array([True] * 5)
    est = np.array([10.0, 1000, 1000, 1000, 0])
    n_gate = np.array([50.0, 500, 500, 500, 0])
    rivals = np.array([1.0, 1, 1, 1, 1])
    cv = np.array([0.05, 0.35, 0.25, 0.10, 0.05])
    sup, mid, rk = tier_masks(universe, est, n_gate, rivals, cv)
    assert sup.tolist() == [True, True, False, False, True]
    assert mid.tolist() == [False, False, True, False, False]
    assert rk.tolist() == [False, False, False, True, False]


def test_missing_feature_policy_renormalizes(build):
    """Work-item-4 requirement: missing never becomes zero — the pillar's
    internal weights renormalize, and a missing pillar's weight is
    redistributed."""
    b2 = replace(build)
    b2.static = {k: v.copy() for k, v in build.static.items()}
    ridx = np.where(build.ranked_set)[0][:4]
    # knock out one cost feature for the first metro, ALL lifestyle for the second
    b2.static["rpp_goods"][ridx[0]] = np.nan
    b2.static["pleasant_days"][ridx[1]] = np.nan
    b2.static["students_per_1k_adults"][ridx[1]] = np.nan
    z, flags = _pillar_z(b2, ridx, np.full(len(ridx), 50.0),
                         np.full(len(ridx), 50.0))
    assert not np.isnan(z[0, 3]), "cost pillar must survive one missing feature"
    assert np.isnan(z[1, 4]), "lifestyle pillar fully missing -> NaN"
    w = _effective_weights(z, {"pool": .3, "balance": .25, "reach": .2,
                               "cost": .15, "lifestyle": .1})
    assert w[1, 4] == 0.0
    assert w.sum(axis=1) == pytest.approx(np.ones(len(ridx)))
    assert w[1, 0] > 0.3  # redistributed pro-rata


def test_permalink_is_deterministic():
    body = {"self": {"sex": "female", "age": 32},
            "seeking": {"age": [30, 40], "marital": ["never_married"]}}
    a = engine.permalink("dv1", "m1.1.0", body)
    b = engine.permalink("dv1", "m1.1.0", dict(body))
    assert a == b and a.startswith("/r/dv1/m1.1.0/")


def test_mask_axis_semantics():
    """The flattened mask must agree with the cube's axis order cell by cell
    — the Phase 1 'samier' transposition (income before education in the
    flat layout) can never come back."""
    m = engine.mask_vector("female", 30, 34, frozenset({0, 1}), "bachelors",
                           75000, ("nh_black",))
    M = m.reshape(2, 53, 3, 4, 7, 8)
    sex_i = engine.SEX_LEVELS.index("female")
    ages = slice(30 - 18, 34 - 18 + 1)
    edu = [2, 3]                      # bachelors, graduate
    inc = [3, 4, 5, 6]                # >= 75k bands
    race = engine.RACE_LEVELS.index("nh_black")
    inside = M[sex_i, ages][:, [0, 1]][:, :, edu][:, :, :, inc][:, :, :, :, race]
    assert inside.min() == 1.0 and inside.max() == 1.0
    assert m.sum() == 5 * 2 * 2 * 4 * 1
    M2 = M.copy()
    M2[sex_i, ages, 0:2, 2:4, 3:7, race] = 0.0
    assert M2.sum() == 0.0, "mask has weight outside the intended cells"
