"""Engine unit tests: schema contract, mask semantics, D05 slider,
interval conservatism rules, the n-only suppression gate (ADR 0002), the
feature-level attribution identity and terminology rules (ADR 0003), and
the missing-data policy."""
import json
import re
from pathlib import Path

import numpy as np
import pytest

from atlas import model as engine
from atlas.model.explain import render_explanation
from atlas.model.intervals import IntervalModel
from atlas.model.preferences import slider_weights
from atlas.model.scoring import score_components
from atlas.model.suppression import POLICY_STRINGS, tier_masks
from atlas.model.versions import MODEL_VERSION

FIXTURE_DIR = Path(__file__).resolve().parent / "fixture_build"
BANNED = re.compile(r"\b(rivals?|markets?|supply|inventory|competitors?)\b",
                    re.IGNORECASE)


@pytest.fixture(scope="module")
def build():
    return engine.load_build(FIXTURE_DIR)


@pytest.fixture(scope="module")
def response(build):
    body = {"self": {"sex": "female", "age": 32},
            "seeking": {"age": [28, 40],
                        "marital": ["never_married", "previously_married"]}}
    return engine.rank(build, engine.parse_request(body))


def test_schema_version_mismatch_refused(tmp_path):
    src = json.loads((FIXTURE_DIR / "manifest.json").read_text())
    src["schema_version"] = "cube-v0"
    (tmp_path / "manifest.json").write_text(json.dumps(src))
    with pytest.raises(AssertionError, match="schema"):
        engine.load_build(tmp_path)


def test_model_version_mismatch_refused(tmp_path):
    """A build produced under one model version must not load silently into
    another — the same class of failure as the Phase 1 mask bug."""
    src = json.loads((FIXTURE_DIR / "manifest.json").read_text())
    src["model_version"] = "m0.9.9"
    (tmp_path / "manifest.json").write_text(json.dumps(src))
    with pytest.raises(AssertionError, match="model_version"):
        engine.load_build(tmp_path)
    # the explicit opt-out gets past the version check and fails later,
    # on the missing cube files — never silently
    with pytest.raises(Exception) as e:
        engine.load_build(tmp_path, allow_model_mismatch=True)
    assert "model_version" not in str(e.value)


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


def test_tier_masks_gate_on_n_alone():
    """ADR 0002: min(n_alloc, kish) < 100, empty pool or empty rivals
    suppress; nothing else does — a 35% true CV with n over the gate RANKS,
    because no CV rule exists to demote it."""
    universe = np.array([True] * 5)
    est = np.array([10.0, 1000, 1000, 1000, 0])
    n_gate = np.array([50.0, 500, 100, 500, 0])
    rivals = np.array([1.0, 1, 1, 0, 1])
    sup, rk = tier_masks(universe, est, n_gate, rivals)
    assert sup.tolist() == [True, False, False, True, True]
    assert rk.tolist() == [False, True, True, False, False]
    assert not any(k.startswith("cv_above") for k in POLICY_STRINGS), (
        "retired CV reason strings must not exist")


def test_missing_feature_policy_renormalizes(build):
    """Missing never becomes zero — the pillar's internal weights
    renormalize, and a fully-missing pillar's weight is redistributed."""
    b2 = engine.load_build(FIXTURE_DIR)
    b2.static = {k: v.copy() for k, v in build.static.items()}
    ridx = np.where(build.ranked_set)[0][:4]
    # knock out one cost feature for the first metro, ALL lifestyle for the second
    b2.static["rpp_goods"][ridx[0]] = np.nan
    b2.static["pleasant_days"][ridx[1]] = np.nan
    b2.static["students_per_1k_adults"][ridx[1]] = np.nan
    weights = {"pool": .3, "balance": .25, "reach": .2, "cost": .15,
               "lifestyle": .1}
    sc = score_components(b2, ridx, np.full(len(ridx), 1000.0),
                          np.full(len(ridx), 0.9), weights)
    feats = [f["id"] for f in sc["feats"]]
    w = sc["w_eff"]
    j_rpp = feats.index("rpp_goods")
    j_rent = feats.index("median_gross_rent")
    j_pd = feats.index("pleasant_days")
    j_st = feats.index("students_per_1k_adults")
    j_pool = feats.index("pool_size")
    assert w[0, j_rpp] == 0.0
    assert w[0, j_rent] > 0.15 * 0.5, "cost pillar must renormalize internally"
    assert w[1, j_pd] == 0.0 and w[1, j_st] == 0.0
    assert w[1, j_pool] > 0.3, "missing pillar's weight redistributes pro-rata"
    assert w.sum(axis=1) == pytest.approx(np.ones(len(ridx)))


def test_attribution_identity_and_pillar_sums(build, response):
    """ADR 0003: the feature is the primitive and §7.5 exactness holds —
    contributions sum to score minus the (single) feature-level reference
    score, and each pillar's contribution equals the sum of its features'."""
    rows = response["ranked"]
    assert len(rows) >= 3
    for r in rows:
        scored = [s for s in r["stats"] if s.get("contribution") is not None]
        by_pillar = {}
        for s in scored:
            by_pillar[s["pillar"]] = by_pillar.get(s["pillar"], 0.0) + s["contribution"]
        for c in r["contributions"]:
            assert abs(by_pillar[c["pillar"]] - c["value"]) < 0.05
        w_sum = sum(s["weight"] for s in scored)
        assert w_sum == pytest.approx(1.0, abs=0.002), (
            "effective feature weights must sum to 1")
    # the exact identity is asserted inside score_components on every call;
    # exercise it directly with a deliberately missing feature
    ridx = np.where(build.ranked_set)[0][:5]
    sc = score_components(build, ridx, np.linspace(1e3, 5e4, 5),
                          np.linspace(0.5, 1.2, 5),
                          {"pool": .3, "balance": .25, "reach": .2,
                           "cost": .15, "lifestyle": .1})
    ref_score = (sc["w_eff"] * np.where(~np.isnan(sc["z"]),
                                        sc["ref"][None, :], 0.0)).sum(axis=1)
    assert np.allclose(sc["contrib"].sum(axis=1), sc["score"] - ref_score)


def test_no_banned_terminology_reaches_a_rendered_string(build, response):
    """§12.3 / ADR 0003: 'rival', 'market', 'supply', 'inventory',
    'competitor' never reach a rendered string — explanations, policy
    strings, or any display field in the legend."""
    for s in POLICY_STRINGS.values():
        assert not BANNED.search(s), s
    for fid, e in build.legend.items():
        for k in ("display_name", "unit", "definition"):
            assert not BANNED.search(str(e.get(k, ""))), (fid, k)
    for p, e in build.pillars.items():
        assert not BANNED.search(e["display_name"] + " " + e["definition"]), p
    for r in response["ranked"]:
        assert not BANNED.search(r["explanation"]), r["explanation"]


def test_explanation_lead_is_position_unique(build, response):
    """The committed Phase 2a face panel duplicated its lead sentence
    because a pre-commit renderer keyed phrasing on magnitude bucket alone —
    two large-bucket strengths both read 'Its biggest edge is'. Found by
    reading the panel by hand; checked by machine ever since: the lead
    phrase appears at most once, whatever the contributions look like."""
    for r in response["ranked"]:
        assert r["explanation"].count("What moved it most") <= 1, r["explanation"]
    # force the historical trigger: two same-bucket large contributions
    row = dict(response["ranked"][0])
    row["stats"] = [
        {"id": "pool_size", "pillar": "pool", "value": 84200.0,
         "contribution": 12.0},
        {"id": "median_gross_rent", "pillar": "cost", "value": 1830.0,
         "contribution": 11.0},
    ]
    out = render_explanation(row, build.legend)
    assert out.count("What moved it most") == 1
    assert not BANNED.search(out)


def test_balance_displays_as_matches_per_10(build, response):
    """ADR 0003 terminology: the ratio renders as matches per 10 people
    looking — stored ratio x 10, one decimal, computed server-side."""
    le = build.legend["partners_per_rival"]
    assert le["display_scale"] == 10 and le["display_decimals"] == 1
    r = response["ranked"][0]
    s = next(s for s in r["stats"] if s["id"] == "partners_per_rival")
    assert s["display"] == f"{r['ratio'] * 10:,.1f}"


def test_permalink_is_deterministic():
    body = {"self": {"sex": "female", "age": 32},
            "seeking": {"age": [30, 40], "marital": ["never_married"]}}
    a = engine.permalink("dv1", MODEL_VERSION, body)
    b = engine.permalink("dv1", MODEL_VERSION, dict(body))
    assert a == b and a.startswith(f"/r/dv1/{MODEL_VERSION}/")


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


def test_pairing_counterweight_gates_and_margins(build):
    """§10.4: with a race filter active the counterweight arrives with a
    replicate-measured margin, or arrives suppressed — never a bare
    number."""
    body = {"self": {"sex": "female", "age": 29},
            "seeking": {"age": [28, 38], "marital": ["never_married"],
                        "race_ethnicity": ["black_nh"]}}
    res = engine.rank(build, engine.parse_request(body))
    saw_value = False
    for r in res["ranked"]:
        if r["cross_group_pairing_rate"] is not None:
            saw_value = True
            assert 0.0 <= r["cross_group_pairing_rate"] <= 1.0
            assert r["cross_group_pairing_moe"] > 0
            assert r["cross_group_pairing_n"] >= 100
        else:
            assert r.get("cross_group_pairing_suppressed") == "n_below_100"
    assert saw_value, "no metro cleared the pairing gate in the fixture"
    # multi-select race aggregates cells and still carries a margin
    body["seeking"]["race_ethnicity"] = ["black_nh", "hispanic"]
    res2 = engine.rank(build, engine.parse_request(body))
    assert any(r["cross_group_pairing_rate"] is not None
               for r in res2["ranked"])
