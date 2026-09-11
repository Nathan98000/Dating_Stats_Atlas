"""Engine unit tests: schema contract enforcement and mask semantics."""
import json

import numpy as np
import pytest

import score as engine
from conftest import FIXTURE_DIR


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
    full = engine.mask_vector("male", 18, 70, "any", None, None, None)
    assert full.sum() == engine.N_FLAT / 2  # one sex
    never = engine.mask_vector("female", 30, 34, "never", "bachelors", 75000, None)
    # 5 ages x 1 marital x 2 edu x 4 income bands x 8 races
    assert never.sum() == 5 * 1 * 2 * 4 * 8
    e = engine.mask_vector("male", 28, 38, "not_married", "bachelors", 75000, "nh_black")
    assert e.sum() == 11 * 2 * 2 * 4 * 1


def test_income_floor_must_be_band_edge():
    with pytest.raises(AssertionError, match="band edge"):
        engine.mask_vector("male", 18, 70, "any", None, 60000, None)


def test_pool_sums_match_between_masks(build):
    """Additivity: never + previously == not_married."""
    kw = dict(age_min=25, age_max=40, education_min=None, income_min=None, race=None)
    m_never = engine.mask_vector("female", marital="never", **kw)
    m_prev = engine.mask_vector("female", marital="not_married", **kw) - m_never
    est_nm = build.pool_flat @ engine.mask_vector("female", marital="not_married", **kw)
    est_split = build.pool_flat @ m_never + build.pool_flat @ m_prev
    assert np.allclose(est_nm, est_split, rtol=1e-6)


def test_weights_normalised(build):
    r1 = engine.rank(build, "female", 32,
                     {"age_min": 30, "age_max": 40, "marital": "not_married"},
                     {"pool": 2.0, "balance": 2.0})
    r2 = engine.rank(build, "female", 32,
                     {"age_min": 30, "age_max": 40, "marital": "not_married"},
                     {"pool": 0.5, "balance": 0.5})
    assert [x["cbsa"] for x in r1["ranked"]] == [x["cbsa"] for x in r2["ranked"]]
    assert r1["ranked"][0]["score"] == r2["ranked"][0]["score"]
