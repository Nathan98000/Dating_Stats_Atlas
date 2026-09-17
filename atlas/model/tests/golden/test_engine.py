"""Engine unit tests, m2.0.0: schema contract, mask semantics, the plain
sex-ratio balance and its separate gate (ADR 0004), the always-counted
race groups, the two-value marital contract, the importance controls, the
feature-level attribution identity, and the banned-vocabulary rules."""
import json
import re
from pathlib import Path

import numpy as np
import pytest

from atlas import model as engine
from atlas.model.explain import summary_line
from atlas.model.intervals import IntervalModel
from atlas.model.preferences import (ALLOWED_MARITAL, balance_masks,
                                     importance_weights, resolve_race_levels,
                                     slider_weights)
from atlas.model.scoring import score_components
from atlas.model.suppression import (POLICY_STRINGS, TECHNICAL_STRINGS,
                                     tier_masks)
from atlas.model.versions import MODEL_VERSION

FIXTURE_DIR = Path(__file__).resolve().parent / "fixture_build"
BANNED = re.compile(r"\b(odds|rivals?|markets?|supply|inventory|competitors?)\b",
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
    src = json.loads((FIXTURE_DIR / "manifest.json").read_text())
    src["model_version"] = "m1.2.0"
    (tmp_path / "manifest.json").write_text(json.dumps(src))
    with pytest.raises(AssertionError, match="model_version"):
        engine.load_build(tmp_path)


def test_axis_reorder_refused(tmp_path):
    src = json.loads((FIXTURE_DIR / "manifest.json").read_text())
    src["axes"][4], src["axes"][5] = src["axes"][5], src["axes"][4]
    (tmp_path / "manifest.json").write_text(json.dumps(src))
    with pytest.raises(AssertionError):
        engine.load_build(tmp_path)


def test_mask_axis_semantics():
    """The flattened mask must agree with the cube's axis order cell by cell
    — the Phase 1 'samier' transposition can never come back."""
    m = engine.mask_vector("female", 30, 34, frozenset({0, 1}), "bachelors",
                           75000, ("nh_black",))
    M = m.reshape(2, 53, 3, 4, 7, 8)
    sex_i = engine.SEX_LEVELS.index("female")
    ages = slice(30 - 18, 34 - 18 + 1)
    edu = [2, 3]
    inc = [3, 4, 5, 6]
    race = engine.RACE_LEVELS.index("nh_black")
    inside = M[sex_i, ages][:, [0, 1]][:, :, edu][:, :, :, inc][:, :, :, :, race]
    assert inside.min() == 1.0 and inside.max() == 1.0
    assert m.sum() == 5 * 2 * 2 * 4 * 1
    M2 = M.copy()
    M2[sex_i, ages, 0:2, 2:4, 3:7, race] = 0.0
    assert M2.sum() == 0.0, "mask has weight outside the intended cells"


def test_balance_masks_are_the_plain_sex_ratio():
    """ADR 0004: balance carries ONLY sex, the seeking age range and the
    marital selection — race, education and income never touch it."""
    body = {"self": {"sex": "female", "age": 32},
            "seeking": {"age": [30, 40], "marital": ["never_married"],
                        "education_min": "graduate", "income_min": 250000,
                        "race_ethnicity": ["nhpi_nh"]}}
    req = engine.parse_request(body)
    sought, seeker = balance_masks(req)
    # full slices: 11 ages x 1 marital level x ALL edu x ALL inc x ALL race
    assert sought.sum() == 11 * 1 * 4 * 7 * 8
    assert seeker.sum() == 11 * 1 * 4 * 7 * 8
    S = sought.reshape(2, 53, 3, 4, 7, 8)
    K = seeker.reshape(2, 53, 3, 4, 7, 8)
    assert S[engine.SEX_LEVELS.index("male")].sum() == sought.sum()
    assert K[engine.SEX_LEVELS.index("female")].sum() == seeker.sum()
    # identical windows, opposite sexes: the two masks are disjoint and
    # their union is symmetric in sex
    assert float(sought @ seeker) == 0.0


def test_balance_ignores_filters_end_to_end(build):
    """The displayed balance may not move when race/education/income
    filters move — that stability is the redefinition's whole point."""
    base = {"self": {"sex": "female", "age": 30},
            "seeking": {"age": [28, 40],
                        "marital": ["never_married", "previously_married"]}}
    heavy = json.loads(json.dumps(base))
    heavy["seeking"].update({"education_min": "graduate",
                             "income_min": 100000,
                             "race_ethnicity": ["black_nh"]})
    r1 = engine.rank(build, engine.parse_request(base))
    r2 = engine.rank(build, engine.parse_request(heavy))
    b1 = {r["cbsa"]: r["balance"]["per_100"] for r in r1["ranked"]
          if r["balance"]["available"]}
    rows2 = {r["cbsa"]: r for r in r2["ranked"] + r2["suppressed"]}
    checked = 0
    for cbsa, v in b1.items():
        row = rows2.get(cbsa)
        if row and row["balance"]["available"]:
            assert row["balance"]["per_100"] == v, cbsa
            checked += 1
    assert checked >= 5


def test_always_counted_race_groups():
    """'Two or more races' and 'Another race' are ORed into every race
    selection in the MODEL, and zero-of-six (or all six) means no filter."""
    assert resolve_race_levels(None) is None
    assert resolve_race_levels([]) is None
    assert resolve_race_levels(list(engine.SELECTABLE_RACES)) is None
    got = resolve_race_levels(["white_nh"])
    assert set(got) == {"nh_white", "nh_twoplus", "nh_other"}
    with pytest.raises(AssertionError, match="always counted"):
        resolve_race_levels(["two_or_more_nh"])
    # and the pool reconciles: one selected group NEVER yields less than
    # the bare single-group mask would
    m_with = engine.mask_vector("male", 28, 38, frozenset({0}), None, None,
                                got)
    m_alone = engine.mask_vector("male", 28, 38, frozenset({0}), None, None,
                                 ("nh_white",))
    assert m_with.sum() > m_alone.sum()


def test_marital_contract_is_two_values():
    body = {"self": {"sex": "female", "age": 32},
            "seeking": {"age": [30, 40], "marital": ["currently_married"]}}
    with pytest.raises(ValueError, match="never_married or previously"):
        engine.parse_request(body)
    assert set(ALLOWED_MARITAL) == {"never_married", "previously_married"}


def test_tier_masks_no_rival_condition():
    universe = np.array([True] * 4)
    est = np.array([10.0, 1000, 0, 1000])
    n_gate = np.array([50.0, 500, 0, 100])
    sup, rk = tier_masks(universe, est, n_gate)
    assert sup.tolist() == [True, False, True, False]
    assert rk.tolist() == [False, True, False, True]
    assert "no_rivals" not in POLICY_STRINGS


def test_balance_gate_is_separate(build):
    """A search that suppresses every pool still serves balance wherever
    its own two counts clear the bar (ADR 0004)."""
    body = {"self": {"sex": "female", "age": 30},
            "seeking": {"age": [25, 35], "marital": ["never_married"],
                        "education_min": "graduate", "income_min": 250000,
                        "race_ethnicity": ["nhpi_nh"]}}
    res = engine.rank(build, engine.parse_request(body))
    assert res["counts"]["ranked"] == 0
    with_balance = [r for r in res["suppressed"] if r["balance"]["available"]]
    assert len(with_balance) >= 6, (
        "balance should survive suppression almost everywhere")
    for r in with_balance:
        assert isinstance(r["balance"]["per_100"], int)
        assert "per 100" in r["balance"]["display"]
    assert "pool" not in res["suppressed"][0], (
        "a suppressed row must not leak a pool figure")


def test_same_sex_balance_is_not_applicable(build):
    """The plain sex ratio does not exist for a same-sex search — both
    sides are the same people, the ratio is 1 by construction, and serving
    it would hand a quarter of the model to a constant (found when rank
    stability collapsed to 0.05 on this shape). Served not-applicable with
    a plain note; the pillar's weight redistributes pro-rata."""
    body = {"self": {"sex": "male", "age": 31},
            "seeking": {"sex": "male", "age": [27, 38],
                        "marital": ["never_married"],
                        "education_min": "bachelors"}}
    res = engine.rank(build, engine.parse_request(body))
    assert res["balance_applies"] is False
    for r in res["ranked"] + res["suppressed"]:
        assert r["balance"]["available"] is False
        assert "doesn’t apply" in r["balance"]["note"]
    row = res["ranked"][0]
    bal_stat = next(s for s in row["stats"] if s["id"] == "pool_balance")
    assert bal_stat["value"] is None and bal_stat["weight"] == 0.0
    scored = [s for s in row["stats"] if s.get("contribution") is not None]
    assert sum(s["weight"] for s in scored) == pytest.approx(1.0, abs=0.002)


def test_importance_controls_map_through_registry(build):
    defaults = build.manifest["model_defaults"]
    w = importance_weights(0.4545, {"cost": "a_lot", "reach": "not_much",
                                    "lifestyle": "some"}, defaults)
    tot = sum(w.values())
    w = {k: v / tot for k, v in w.items()}
    assert w["cost"] > w["reach"], "a_lot must outweigh not_much"
    assert min(w.values()) > 0, "'Not much' is a floor, never zero"
    assert sum(w.values()) == pytest.approx(1.0)
    # neutral settings reproduce the registry defaults exactly
    w0 = importance_weights(defaults["size_vs_odds"]["default_s"],
                            {}, defaults)
    tot0 = sum(w0.values())
    for p, v in defaults["pillar_weights"].items():
        assert w0[p] / tot0 == pytest.approx(v, abs=1e-3)


def test_deprecated_slider_still_accepted(build):
    body = {"self": {"sex": "female", "age": 29},
            "seeking": {"age": [27, 36], "marital": ["never_married"]},
            "size_vs_odds": 1.0}
    res = engine.rank(build, engine.parse_request(body))
    assert res["weights"]["balance"] == pytest.approx(0.55)
    assert res["weights"]["pool"] == 0.0


def test_slider_is_a_pure_function():
    defaults = {"pool": 0.30, "balance": 0.25, "reach": 0.20,
                "cost": 0.15, "lifestyle": 0.10}
    w0 = slider_weights(0.0, defaults, 0.55)
    w1 = slider_weights(1.0, defaults, 0.55)
    assert w0["pool"] == pytest.approx(0.55) and w0["balance"] == 0.0
    assert w1["balance"] == pytest.approx(0.55) and w1["pool"] == 0.0


def test_interval_machinery_still_computes(build, response):
    """ADR 0004 hides margins; it does not delete them. Every ranked row
    still returns pool_moe > 0 and the manifest still carries Gate 0."""
    for r in response["ranked"]:
        assert r["pool_moe"] > 0
        assert 0 < r["cv"] < 1
    v = build.manifest["interval_model"]["validation"]
    assert v["coverage"] >= 0.95
    im = IntervalModel(
        feature_names=[], coef=np.zeros(14), race_levels=engine.RACE_LEVELS,
        offsets=np.zeros(3),
        inflation={"none": 1.1, "nh_black": 1.5, "nh_asian": 1.3}, meta={})
    n = np.array([500.0, 500, 500]); k = n.copy(); sh = np.full(3, 0.01)
    multi = im.served_rse(n, k, sh, frozenset({0, 1}), ["nh_black", "nh_asian"])
    single = im.served_rse(n, k, sh, frozenset({0, 1}), ["nh_black"])
    assert (multi >= single - 1e-12).all()


def test_attribution_identity_and_pillar_sums(build, response):
    rows = response["ranked"]
    assert len(rows) >= 3
    for r in rows:
        scored = [s for s in r["stats"] if s.get("contribution") is not None]
        by_pillar = {}
        for s in scored:
            by_pillar[s["pillar"]] = by_pillar.get(s["pillar"], 0.0) + s["contribution"]
        for c in r["contributions"]:
            assert abs(by_pillar[c["pillar"]] - c["value"]) < 0.05
    ridx = np.where(build.ranked_set)[0][:5]
    sc = score_components(build, ridx, np.linspace(1e3, 5e4, 5),
                          np.linspace(0.8, 1.3, 5),
                          {"pool": .3, "balance": .25, "reach": .2,
                           "cost": .15, "lifestyle": .1})
    ref_score = (sc["w_eff"] * np.where(~np.isnan(sc["z"]),
                                        sc["ref"][None, :], 0.0)).sum(axis=1)
    assert np.allclose(sc["contrib"].sum(axis=1), sc["score"] - ref_score)


def test_no_banned_terminology_anywhere(build, response):
    """Gate 2's word list, now including 'odds', over policy strings, the
    legend, and every composed line."""
    for s in POLICY_STRINGS.values():
        assert not BANNED.search(s), s
    for fid, e in build.legend.items():
        if e.get("status") == "retired":
            continue
        for k in ("display_name", "unit", "unit_short", "definition",
                  "mover_phrase", "unit_template"):
            assert not BANNED.search(str(e.get(k) or "")), (fid, k)
        for lab in e.get("band_labels") or []:
            assert not BANNED.search(lab), (fid, lab)
    for p, e in build.pillars.items():
        assert not BANNED.search(e["display_name"] + " " + e["definition"]), p
    for r in response["ranked"]:
        assert not BANNED.search(r["summary_line"]), r["summary_line"]
        assert not BANNED.search(r["balance"]["display"])
    for d in build.descriptions:
        assert not BANNED.search(d), d


def test_summary_line_lead_is_position_unique(build, response):
    for r in response["ranked"]:
        assert r["summary_line"].count(POLICY_STRINGS["pluses_lead"]) <= 1
    row = dict(response["ranked"][0])
    row["stats"] = [
        {"id": "pool_size", "pillar": "pool", "value": 84200.0,
         "contribution": 12.0},
        {"id": "median_gross_rent", "pillar": "cost", "value": 1830.0,
         "contribution": 11.0},
        {"id": "pleasant_days", "pillar": "lifestyle", "value": 90.0,
         "contribution": -6.0},
    ]
    out = summary_line(row, build.legend)
    assert out.count("Biggest pluses:") == 1
    assert out.endswith("counts against it")
    assert not BANNED.search(out)


def test_cards_carry_bands_from_the_build(build, response):
    """Gate 4: every card figure — value, unit line, band, label — arrives
    computed; the band comes from the national standing in the artifact."""
    row = response["ranked"][0]
    cards = {c["id"]: c for c in row["cards"]}
    assert set(cards) == set(build.manifest["city_cards"])
    for cid, c in cards.items():
        if c.get("missing"):
            continue
        assert "display" in c and "unit_line" in c
        band = c.get("band")
        assert band and band["key"] in ("low", "mid", "high")
        assert band["label"] in build.legend[cid]["band_labels"]
        assert band["tone"] in ("good", "neutral", "poor")
    wlh = cards["who_lives_here"]
    assert "adults" in wlh["unit_line"], (
        "who_lives_here composes its adults figure server-side")


def test_score_display_is_a_whole_number(response):
    for r in response["ranked"]:
        assert r["score_display"] == str(int(round(r["score"])))
        assert 0 <= int(r["score_display"]) <= 100


def test_permalink_is_deterministic():
    body = {"self": {"sex": "female", "age": 32},
            "seeking": {"age": [30, 40], "marital": ["never_married"]},
            "pool_vs_balance": 0.7,
            "importance": {"cost": "a_lot", "reach": "some",
                           "lifestyle": "some"}}
    a = engine.permalink("dv1", MODEL_VERSION, body)
    b = engine.permalink("dv1", MODEL_VERSION, dict(body))
    assert a == b and a.startswith(f"/r/dv1/{MODEL_VERSION}/")


def test_missing_feature_policy_renormalizes(build):
    """Missing never becomes zero — the pillar's internal weights
    renormalize, and a fully-missing pillar's weight redistributes."""
    b2 = engine.load_build(FIXTURE_DIR)
    b2.static = {k: v.copy() for k, v in build.static.items()}
    ridx = np.where(build.ranked_set)[0][:4]
    b2.static["rpp_goods"][ridx[0]] = np.nan
    b2.static["pleasant_days"][ridx[1]] = np.nan
    b2.static["students_per_1k_adults"][ridx[1]] = np.nan
    weights = {"pool": .3, "balance": .25, "reach": .2, "cost": .15,
               "lifestyle": .1}
    sc = score_components(b2, ridx, np.full(len(ridx), 1000.0),
                          np.full(len(ridx), 1.1), weights)
    feats = [f["id"] for f in sc["feats"]]
    w = sc["w_eff"]
    assert w[0, feats.index("rpp_goods")] == 0.0
    assert w[0, feats.index("median_gross_rent")] > 0.15 * 0.5
    assert w[1, feats.index("pleasant_days")] == 0.0
    assert w[1, feats.index("pool_size")] > 0.3
    assert w.sum(axis=1) == pytest.approx(np.ones(len(ridx)))


def test_technical_strings_are_separate():
    """The margin wording survives — for the API record and the methodology
    page — but lives apart from the rendered vocabulary."""
    assert "at least" in TECHNICAL_STRINGS["interval"]
    assert not any("margin" in v.lower() for v in POLICY_STRINGS.values()), (
        "rendered policy strings must not speak of margins (ADR 0004)")
