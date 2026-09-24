"""Engine unit tests, m3.0.0: schema contract, mask semantics (and the
weighted path's sibling), the plain sex-ratio balance and its separate
gate (ADR 0004) — displayed, unscored since ADR 0009 — the eight equal
race groups, the two-value marital contract, the six pillars and four
importance controls (ADR 0005), chances of matching with its four
disclosure combinations, the unweighted-n gate, the deprecated slider
alias, the five-band standing with direction-derived tones, the
never-scored crime block, the feature-level attribution identity, and the
banned-vocabulary rules."""
import json
import re
from pathlib import Path

import numpy as np
import pytest

from atlas import model as engine
from atlas.model.explain import summary_line
from atlas.model.intervals import IntervalModel
from atlas.model.loader import reduce_cube, reduced_key
from atlas.model.preferences import (ALLOWED_MARITAL, INCOME_FLOORS,
                                     balance_masks, importance_weights,
                                     resolve_race_levels, seeker_weights,
                                     slider_weights)
from atlas.model.scoring import match_index, score_components, scored_features
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


def test_weighted_mask_axis_semantics(build):
    """The weighted path's sibling of test_mask_axis_semantics (ADR 0009):
    the reduced cubes summed under the pool's own axis vectors must equal
    pool_flat @ mask for every partial filter — and a weight that picks
    out ONE (age, education, race) cell must recover exactly that cell's
    masked pool, so the (age, edu, race) broadcast can never be
    transposed the way the Phase 1 mask was."""
    body = {"self": {"sex": "female", "age": 32},
            "seeking": {"age": [30, 34], "marital": ["never_married",
                                                     "previously_married"],
                        "education_min": "bachelors", "income_min": 75000,
                        "race_ethnicity": ["black_nh"]}}
    req = engine.parse_request(body)
    mt = match_index(build, req)
    est = (build.pool_flat @ engine.mask_vector(
        req.seeking.sex, 30, 34, req.seeking.marital_levels, "bachelors",
        75000, ("nh_black",))).astype(np.float64)
    assert np.allclose(mt["den"], est, rtol=1e-5, atol=1e-3), (
        "the reduced-cube denominator disagrees with the masked pool")
    # every reduced-cube key reproduces the plain masked sums cell by cell
    n = len(build.metro_levels)
    pool7 = build.pool_flat.reshape(n, 2, 53, 3, 4, 7, 8)
    red = reduce_cube(pool7)
    for mar in ({0}, {1}, {0, 1}):
        for floor_i in range(7):
            mi, fi = reduced_key(frozenset(mar), floor_i)
            want = pool7[:, :, :, sorted(mar), :, floor_i:, :].sum(axis=(3, 5))
            assert np.allclose(red[mi, fi], want, rtol=1e-5, atol=1e-2)
    # a one-cell weight: age 31, bachelors, nh_black only
    a_i, e_i, r_i = 31 - 18, engine.EDU_LEVELS.index("bachelors"), \
        engine.RACE_LEVELS.index("nh_black")
    one = np.zeros((53, 4, 8)); one[a_i, e_i, r_i] = 1.0
    mi, fi = reduced_key(req.seeking.marital_levels, INCOME_FLOORS[75000])
    R = build.reduced_pool[mi, fi, :, engine.SEX_LEVELS.index("male")].astype(np.float64)
    picked = np.einsum("maer,aer->m", R, one)
    cell = pool7[:, engine.SEX_LEVELS.index("male"), a_i, :, e_i, INCOME_FLOORS[75000]:, r_i]
    cell = cell[:, [0, 1], :].sum(axis=(1, 2))
    assert np.allclose(picked, cell, rtol=1e-5, atol=1e-2)


def test_seeker_weights_four_disclosure_combinations(build):
    """Item 5's requirement: an unset field drops its component to the
    population-average marginal, both unset leaves the age term alone,
    and every combination answers validly and suppression-correctly."""
    k = build.kernel
    base = {"self": {"sex": "female", "age": 30},
            "seeking": {"age": [28, 40],
                        "marital": ["never_married", "previously_married"]}}
    combos = {"both": {"education": "bachelors", "race_ethnicity": "black_nh"},
              "edu_only": {"education": "bachelors"},
              "race_only": {"race_ethnicity": "black_nh"},
              "neither": {}}
    results = {}
    for name, extra in combos.items():
        body = json.loads(json.dumps(base))
        body["self"].update(extra)
        res = engine.rank(build, engine.parse_request(body))
        results[name] = res
        assert res["counts"]["ranked"] > 0
        for r in res["ranked"]:
            assert r["match"]["available"] and np.isfinite(r["match"]["value"])
            # m3.1.0: the display is the index rounded to a whole number
            # (from the unrounded index, so it can sit half a point from
            # the two-decimal value) unless the registry ceiling caps it
            # (test_match_display_cap_is_presentational)
            if r["match"]["capped"]:
                assert r["match"]["display"] == (
                    build.manifest["strings"]["match_display_cap"]
                    + build.manifest["strings"]["match_display_cap_token"])
            else:
                assert abs(int(r["match"]["display"].replace(",", ""))
                           - r["match"]["value"]) <= 0.5 + 1e-9
            assert r["match"]["moe"] is not None and r["match"]["moe"] >= 0
        assert res["match_inputs"]["education"] == extra.get("education")
    # suppression is identical across the four: the gate is the unweighted n
    sup = {name: {r["cbsa"]: r["reason"] for r in res["suppressed"]}
           for name, res in results.items()}
    assert len({json.dumps(s, sort_keys=True) for s in sup.values()}) == 1
    # the mixture kernels: both-unset averages over every (edu, race) level
    # of the seeker's sex and age; a disclosed level selects that level
    age_v, W_none = seeker_weights(k, "female", 30, None, None)
    _, W_both = seeker_weights(k, "female", 30, "bachelors", "nh_black")
    _, W_edu = seeker_weights(k, "female", 30, "bachelors", None)
    assert age_v.shape == (len(build.metro_levels), 53) and W_none.shape[1:] == (4, 8)
    assert (W_none > 0).all() and (W_both > 0).all()
    # the disclosed-edu kernel is the mixture over race of that edu's
    # per-race kernels: rebuild it by hand from the artifact
    si, ai = 1, 30 - 18
    e_s = engine.EDU_LEVELS.index("bachelors")
    P = k.avail[si, ai][e_s].astype(float)
    P = P / P.sum()
    mix = P[None, :] * np.exp(k.log_norm[:, si, ai, e_s].astype(float))
    E = np.exp(k.dials[:, 1][:, None] * k.f_edu[si, e_s][None, :])
    Rr = np.exp(k.dials[:, 2][:, None, None] * k.f_race[si][None, :, :])
    if k.f_int is None:
        want = np.einsum("mr,mf,mrg->mfg", mix, E, Rr)
    else:
        # m3.2.0: the race x education interaction multiplies in per
        # (seeker race, partner race, partner edu) for the disclosed edu
        G = np.exp(k.f_int[si, :, :, e_s, :])                     # (r_s, r_c, e_c)
        want = np.einsum("mr,mf,mrg,rgf->mfg", mix, E, Rr, G)
    assert np.allclose(W_edu, want, rtol=1e-6)
    # the index differs between disclosures (the disclosure gap the report
    # measures) but every one is centred on 100 nationally (pool-weighted)
    for name, res in results.items():
        req = engine.parse_request({**base, "self": {**base["self"], **combos[name]}})
        mt = match_index(build, req)
        ok = np.isfinite(mt["index"]) & (mt["den"] > 0)
        assert abs((mt["index"][ok] * mt["den"][ok]).sum() / mt["den"][ok].sum() - 100.0) < 1e-6


def test_match_display_cap_is_presentational(build):
    """m3.1.0 (Phase 3b A3): the display ceiling is registry-owned and
    touches nothing but the display string. Rankings, scores, standings,
    bands and the served value are bit-identical whether the ceiling is
    1 (everything capped) or a million (nothing capped), and a capped
    figure renders as the ceiling plus the registry token."""
    from dataclasses import replace
    from atlas.model.scoring import match_display
    body = {"self": {"sex": "female", "age": 30, "education": "graduate",
                     "race_ethnicity": "asian_nh"},
            "seeking": {"age": [28, 40],
                        "marital": ["never_married", "previously_married"]}}
    req = engine.parse_request(body)
    strings = build.manifest["strings"]
    assert float(strings["match_display_cap"]) > 0 and strings["match_display_cap_token"]

    def with_cap(cap: str):
        m = json.loads(json.dumps(build.manifest))
        m["strings"]["match_display_cap"] = cap
        return replace(build, manifest=m)

    shipped = engine.rank(build, req)
    all_capped = engine.rank(with_cap("1"), req)
    none_capped = engine.rank(with_cap("1000000"), req)
    for a, b in ((shipped, all_capped), (shipped, none_capped)):
        assert [r["cbsa"] for r in a["ranked"]] == [r["cbsa"] for r in b["ranked"]]
        for ra, rb in zip(a["ranked"], b["ranked"]):
            assert ra["score"] == rb["score"] and ra["rank"] == rb["rank"]
            assert ra["match"]["value"] == rb["match"]["value"]
            assert ra["match"].get("band") == rb["match"].get("band")
            assert [s["standing"] for s in ra["stats"]] == [s["standing"] for s in rb["stats"]]
        assert {r["cbsa"] for r in a["suppressed"]} == {r["cbsa"] for r in b["suppressed"]}
    token = strings["match_display_cap_token"]
    for r in all_capped["ranked"]:
        assert r["match"]["capped"] and r["match"]["display"] == "1" + token
        stat = next(s for s in r["stats"] if s["id"] == "match_propensity")
        assert stat["display"] == r["match"]["display"]
    for r in none_capped["ranked"]:
        assert not r["match"]["capped"]
        assert r["match"]["display"] == str(int(round(r["match"]["value"])))
    # the shipped ceiling: capped exactly when the rounded figure exceeds it
    cap = float(strings["match_display_cap"])
    for r in shipped["ranked"]:
        want = round(r["match"]["value"]) > cap
        assert r["match"]["capped"] == want, (r["cbsa"], r["match"])
        if want:
            assert r["match"]["display"] == f"{int(cap):,}" + token
    assert match_display(cap + 0.4, build) == (f"{int(cap):,}", False)
    assert match_display(cap + 0.6, build) == (f"{int(cap):,}" + token, True)
    assert match_display(9999.0, build)[1] is True


def test_same_sex_search_says_whose_patterns_it_uses(build):
    """m3.2.0 (Phase 3b B3): a same-sex search's match block carries the
    registry sentence naming which components come from same-sex couples
    and which fall back to opposite-sex couples; an opposite-sex search
    carries no note; the served weights for a same-sex search follow the
    artifact's composition (same-sex terms at dial 1 for the listed
    components, the metro's dialled opposite-sex term for the rest)."""
    from atlas.model.scoring import same_sex_note
    k = build.kernel
    strings = build.manifest["strings"]
    ss_body = {"self": {"sex": "male", "age": 31},
               "seeking": {"sex": "male", "age": [27, 38], "marital": ["never_married"]}}
    os_body = {"self": {"sex": "male", "age": 31},
               "seeking": {"age": [27, 38], "marital": ["never_married"]}}
    res = engine.rank(build, engine.parse_request(ss_body))
    assert res["match_inputs"]["same_sex"] is True
    want = strings["match_same_sex_note"] if (k.same_sex is not None and k.same_sex.components) \
        else strings["match_same_sex_note_all_fallback"]
    assert want == same_sex_note(build)
    assert res["match_inputs"]["same_sex_components"] == (list(k.same_sex.components) if k.same_sex else [])
    for r in res["ranked"]:
        assert r["match"]["note"] == want
        assert not BANNED.search(r["match"]["note"])
    res_os = engine.rank(build, engine.parse_request(os_body))
    assert res_os["match_inputs"]["same_sex"] is False
    assert all("note" not in r["match"] for r in res_os["ranked"])
    # the composition, rebuilt by hand for the undisclosed seeker
    age_v, W = seeker_weights(k, "male", 31, None, None, same_sex=True)
    si, ai = 0, 31 - 18
    gaps = np.arange(53) - ai + k.gap_offset
    ss = k.same_sex
    if ss is not None and "age" in ss.components:
        assert np.allclose(age_v, np.exp(ss.f_age[si, ss.cohort_of_age[ai]][gaps])[None, :])
    else:
        assert np.allclose(age_v, np.exp(k.dials[:, 0:1] * k.f_age[si, k.cohort_of_age[ai]][gaps][None, :]))
    P = k.avail[si, ai].astype(float); P = P / P.sum()
    ln = ss.log_norm if ss is not None else k.log_norm
    mix = P[None] * np.exp(ln[:, si, ai].astype(float))
    M = k.dials.shape[0]
    E = (np.repeat(np.exp(ss.f_edu[si])[None], M, 0) if ss is not None and "edu" in ss.components
         else np.exp(k.dials[:, 1][:, None, None] * k.f_edu[si][None]))
    R = (np.repeat(np.exp(ss.f_race[si])[None], M, 0) if ss is not None and "race" in ss.components
         else np.exp(k.dials[:, 2][:, None, None] * k.f_race[si][None]))
    use_int = k.f_int is not None and not (ss is not None and ("edu" in ss.components or "race" in ss.components))
    if use_int:
        G = np.exp(k.f_int[si]).transpose(2, 0, 3, 1)
        want_W = (mix[:, :, :, None, None] * E[:, :, None, :, None] * R[:, None, :, None, :] * G[None]).sum(axis=(1, 2))
    else:
        want_W = np.einsum("mer,mef,mrg->mfg", mix, E, R)
    assert np.allclose(W, want_W, rtol=1e-6)
    # and the same-sex path differs from the opposite-sex path exactly when
    # the artifact carries same-sex terms
    _, W_os = seeker_weights(k, "male", 31, None, None, same_sex=False)
    if ss is not None and ss.components:
        assert not np.allclose(W, W_os)
    else:
        assert np.allclose(W, W_os)


def test_match_gates_on_unweighted_n(build):
    """The kernel can neither rescue nor condemn a cell: a metro is
    suppressed exactly when min(n_alloc, kish) < 100 on the UNWEIGHTED
    pool, whatever the weights do."""
    body = {"self": {"sex": "female", "age": 30, "education": "graduate",
                     "race_ethnicity": "asian_nh"},
            "seeking": {"age": [25, 35], "marital": ["never_married"],
                        "education_min": "graduate", "income_min": 150000}}
    req = engine.parse_request(body)
    res = engine.rank(build, req)
    mask = engine.mask_vector(req.seeking.sex, 25, 35, req.seeking.marital_levels,
                              "graduate", 150000, None)
    est = (build.pool_flat @ mask).astype(np.float64)
    n_alloc = (build.count_flat @ mask).astype(np.float64)
    sumw2 = (build.sumw2_flat @ mask).astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        kish = np.where(sumw2 > 0, est ** 2 / sumw2, 0.0)
    gate = np.minimum(n_alloc, kish)
    want_suppressed = {build.metro_levels[i] for i in np.where(
        build.ranked_set & ((gate < 100) | (est <= 0)))[0]}
    assert {r["cbsa"] for r in res["suppressed"]} == want_suppressed
    assert res["suppressed"], "the stress shape should suppress something"
    for r in res["suppressed"]:
        assert "match" not in r, "a suppressed row must not carry a match figure"


def test_match_index_is_a_rate_with_the_delta_method_margin(build):
    """Unit weights give an index of exactly 100 everywhere with a zero
    margin; scaling every weight by a constant changes nothing (a rate,
    normalised to the national average); the margin follows
    Var(R) = sum s2 (w - R)^2 / D^2."""
    body = {"self": {"sex": "male", "age": 35},
            "seeking": {"age": [30, 42],
                        "marital": ["never_married", "previously_married"]}}
    req = engine.parse_request(body)
    k = build.kernel
    from dataclasses import replace
    flat_k = replace(k, f_age=np.zeros_like(k.f_age), f_edu=np.zeros_like(k.f_edu),
                     f_race=np.zeros_like(k.f_race), log_norm=np.zeros_like(k.log_norm),
                     dials=np.ones_like(k.dials), f_int=None, same_sex=None)
    b2 = replace(build, kernel=flat_k)
    mt = match_index(b2, req)
    ok = mt["den"] > 0
    # (the mixture weights sum to 1 - 1e-16, so the margin is ~1e-7, not 0)
    assert np.allclose(mt["index"][ok], 100.0) and np.allclose(mt["moe"][ok], 0.0, atol=1e-5)
    # scaling: log_norm + c multiplies every weight by e^c
    scaled = replace(flat_k, log_norm=np.full_like(k.log_norm, 0.7))
    mt2 = match_index(replace(build, kernel=scaled), req)
    assert np.allclose(mt2["index"][ok], 100.0)
    # the real kernel: recompute the margin by hand for one metro
    mt3 = match_index(build, req)
    i = int(np.where(ok)[0][0])
    age_v, W = seeker_weights(k, "male", 35, None, None)
    a = np.zeros(53); a[30 - 18:42 - 18 + 1] = 1.0
    mi, fi = reduced_key(req.seeking.marital_levels, 0)
    tau = engine.SEX_LEVELS.index("female")
    R = build.reduced_pool[mi, fi, i, tau].astype(float)
    S2 = build.reduced_sumw2[mi, fi, i, tau].astype(float)
    w = (age_v[i] * a)[:, None, None] * W[i][None, :, :]
    msk = a[:, None, None] * np.ones((1, 4, 8))
    D = (R * msk).sum(); Rt = (R * w).sum() / D
    var = (S2 * msk * (w - Rt) ** 2).sum() / D ** 2
    assert np.isclose(mt3["rate"][i], Rt)
    assert np.isclose(mt3["moe"][i], 1.645 * np.sqrt(var) * 100 / mt3["national_rate"])


def test_balance_displayed_never_scored(build, response):
    """ADR 0009: pool_balance keeps its block on every row and its
    computation, and is nowhere in the scored set or the weights."""
    scored_ids = [f["id"] for f in scored_features(build)]
    assert "pool_balance" not in scored_ids
    assert scored_ids[:2] == ["pool_size", "match_propensity"]
    assert set(response["weights"]) == {"pool", "match", "reach", "cost",
                                        "weather", "students"}
    for r in response["ranked"]:
        assert r["balance"]["available"] and r["balance"]["per_100"] > 0
        assert not any(s["id"] == "pool_balance" for s in r["stats"])
        ms = next(s for s in r["stats"] if s["id"] == "match_propensity")
        assert ms["weight"] > 0 and ms["band"]["label"] in \
            build.legend["match_propensity"]["band_labels"]
        assert r["match"]["band"] == ms["band"]


def test_slider_alias_accepted_for_one_version(build):
    """pool_vs_balance is the deprecated name for pool_vs_match in
    m3.0.0: same weights, same permalink; both together is a contradiction."""
    base = {"self": {"sex": "female", "age": 29},
            "seeking": {"age": [27, 36], "marital": ["never_married"]}}
    new = engine.rank(build, engine.parse_request({**base, "pool_vs_match": 0.8}))
    old = engine.rank(build, engine.parse_request({**base, "pool_vs_balance": 0.8}))
    assert new["weights"] == old["weights"]
    assert [r["cbsa"] for r in new["ranked"]] == [r["cbsa"] for r in old["ranked"]]
    assert engine.permalink("dv", MODEL_VERSION, {**base, "pool_vs_balance": 0.8}) == \
        engine.permalink("dv", MODEL_VERSION, {**base, "pool_vs_match": 0.8})
    with pytest.raises(ValueError, match="deprecated name"):
        engine.rank(build, engine.parse_request(
            {**base, "pool_vs_match": 0.8, "pool_vs_balance": 0.2}))
    with pytest.raises(ValueError, match="self.education"):
        engine.parse_request({**base, "self": {"sex": "female", "age": 29,
                                               "education": "phd"}})


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


def test_eight_equal_race_groups(build):
    """m2.2.0 (ADR 0006, reversing ADR 0004's always-counted rule): the
    selection IS the filter. Three assertions the brief named: ticking
    only two_or_more_nh masks that one cube level; a partial selection's
    pool equals the sum of its ticked groups' pools to float tolerance;
    and no served figure includes a level the visitor did not tick."""
    assert len(engine.SELECTABLE_RACES) == 8
    assert resolve_race_levels(None) is None
    assert resolve_race_levels([]) is None
    assert resolve_race_levels(list(engine.SELECTABLE_RACES)) is None, (
        "all eight ticked is the same universe as none ticked")

    # 1. the newly selectable groups are ordinary filters
    got = resolve_race_levels(["two_or_more_nh"])
    assert got == ("nh_twoplus",)
    m = engine.mask_vector("male", 28, 38, frozenset({0}), None, None, got)
    M = m.reshape(2, 53, 3, 4, 7, 8)
    r_i = engine.RACE_LEVELS.index("nh_twoplus")
    assert M[..., r_i].sum() == m.sum(), "weight outside the ticked level"

    # 2. a partial selection adds NOTHING: its pool is exactly the sum of
    # its ticked groups' pools, per metro, to float tolerance
    sel = ["white_nh", "asian_nh", "other_nh"]
    spec = engine.parse_request({
        "self": {"sex": "female", "age": 30},
        "seeking": {"age": [28, 40], "marital": ["never_married"],
                    "race_ethnicity": sel}}).seeking
    pool = build.pool_flat @ engine.mask_vector(
        spec.sex, spec.age_min, spec.age_max, spec.marital_levels,
        None, None, spec.race_cube_levels)
    parts = np.zeros_like(pool)
    for r in sel:
        parts += build.pool_flat @ engine.mask_vector(
            spec.sex, spec.age_min, spec.age_max, spec.marital_levels,
            None, None, resolve_race_levels([r]))
    assert np.allclose(pool, parts, rtol=1e-6), (
        "the arithmetic a visitor can check: ticked groups sum to the pool")

    # 3. no served figure includes an unticked level: the selection mask
    # carries zero weight on every level outside the selection
    mask = engine.mask_vector(spec.sex, spec.age_min, spec.age_max,
                              spec.marital_levels, None, None,
                              spec.race_cube_levels)
    Msel = mask.reshape(2, 53, 3, 4, 7, 8)
    unticked = [i for i, lv in enumerate(engine.RACE_LEVELS)
                if lv not in set(spec.race_cube_levels)]
    assert Msel[..., unticked].sum() == 0.0, (
        "a figure must never include a group the visitor did not tick")


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
    # ADR 0009: balance is no longer a stat at all; the weights still sum
    # to one over the scored set, and the match figure is served
    assert not any(s["id"] == "pool_balance" for s in row["stats"])
    assert row["match"]["available"]
    scored = [s for s in row["stats"] if s.get("contribution") is not None]
    assert sum(s["weight"] for s in scored) == pytest.approx(1.0, abs=0.002)


def test_importance_controls_map_through_registry(build):
    """m2.1.0: FOUR controls (cost, reach, students, weather), each mapped
    through the registry level table; neutral settings reproduce the
    six-pillar registry defaults exactly."""
    defaults = build.manifest["model_defaults"]
    w = importance_weights(0.4545, {"cost": "a_lot", "reach": "not_much",
                                    "students": "a_lot",
                                    "weather": "not_much"}, defaults)
    tot = sum(w.values())
    w = {k: v / tot for k, v in w.items()}
    assert w["cost"] > w["reach"], "a_lot must outweigh not_much"
    assert "match" in w and "balance" not in w
    assert min(w.values()) > 0, "'Not much' is a floor, never zero"
    assert sum(w.values()) == pytest.approx(1.0)
    # students and weather move INDEPENDENTLY — the reason for the split
    w_s = importance_weights(0.4545, {"students": "a_lot"}, defaults)
    assert w_s["students"] > w_s["weather"] / 0.06 * 0.04, (
        "raising students must not raise weather")
    assert w_s["weather"] == pytest.approx(defaults["pillar_weights"]["weather"])
    # neutral settings reproduce the registry defaults exactly
    w0 = importance_weights(defaults["size_vs_odds"]["default_s"],
                            {}, defaults)
    tot0 = sum(w0.values())
    for p, v in defaults["pillar_weights"].items():
        assert w0[p] / tot0 == pytest.approx(v, abs=1e-3)


def test_lifestyle_alias_maps_to_both_halves(build):
    """The m2.0.0 bundled control is accepted for exactly this version:
    its level lands on weather AND students, which reproduces what it used
    to mean; naming it alongside either half is a contradiction."""
    defaults = build.manifest["model_defaults"]
    w = importance_weights(0.4545, {"lifestyle": "a_lot"}, defaults)
    mult = float(defaults["importance_levels"]["a_lot"])
    assert w["weather"] == pytest.approx(
        defaults["pillar_weights"]["weather"] * mult)
    assert w["students"] == pytest.approx(
        defaults["pillar_weights"]["students"] * mult)
    with pytest.raises(ValueError, match="deprecated name"):
        importance_weights(0.5, {"lifestyle": "a_lot", "weather": "some"},
                           defaults)
    with pytest.raises(ValueError, match="unknown importance"):
        importance_weights(0.5, {"nightlife": "a_lot"}, defaults)


def test_size_vs_odds_removed(build):
    """Accepted-but-deprecated for exactly m2.0.0 (ADR 0004); m2.1.0
    removes it with a loud error naming the replacement."""
    body = {"self": {"sex": "female", "age": 29},
            "seeking": {"age": [27, 36], "marital": ["never_married"]},
            "size_vs_odds": 1.0}
    with pytest.raises(ValueError, match="pool_vs_match"):
        engine.rank(build, engine.parse_request(body))


def test_slider_is_a_pure_function():
    defaults = {"pool": 0.30, "match": 0.25, "reach": 0.20,
                "cost": 0.15, "weather": 0.06, "students": 0.04}
    w0 = slider_weights(0.0, defaults, 0.55)
    w1 = slider_weights(1.0, defaults, 0.55)
    assert w0["pool"] == pytest.approx(0.55) and w0["match"] == 0.0
    assert w1["match"] == pytest.approx(0.55) and w1["pool"] == 0.0


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
                          np.linspace(80, 130, 5),
                          {"pool": .3, "match": .25, "reach": .2,
                           "cost": .15, "weather": .06, "students": .04})
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
        {"id": "rent_1br", "pillar": "cost", "value": 1830.0,
         "contribution": 11.0},
        {"id": "pleasant_days", "pillar": "weather", "value": 90.0,
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
    band_keys = tuple(build.manifest["standing_bands"]["keys"])
    assert len(band_keys) == 5, "five bands since m2.1.0 (item 6)"
    for cid, c in cards.items():
        if c.get("missing"):
            continue
        assert "display" in c and "unit_line" in c
        band = c.get("band")
        assert band and band["key"] in band_keys
        assert band["label"] in build.legend[cid]["band_labels"]
        assert band["tone"] in ("good_strong", "good", "neutral", "poor",
                                "poor_strong")
        # the tone comes from the registry's band_direction, one rule for
        # every feature — position labels can never colour as virtue by
        # accident (item 6). Phase 2f item 1: FIVE tones — the extremes
        # read harder than the middles, still direction crossed with
        # position and nothing else.
        direction = build.legend[cid]["band_direction"]
        pos = band_keys.index(band["key"])
        expect_tone = {
            "good_low": ("good_strong", "good", "neutral", "poor",
                         "poor_strong"),
            "good_high": ("poor_strong", "poor", "neutral", "good",
                          "good_strong"),
            "neutral": ("neutral",) * 5}[direction][pos]
        assert band["tone"] == expect_tone, (cid, band)
    wlh = cards["who_lives_here"]
    assert "adults" in wlh["unit_line"], (
        "who_lives_here composes its adults figure server-side")


def test_score_display_is_a_whole_number(response):
    for r in response["ranked"]:
        # score_display rounds the UNROUNDED score; r["score"] is already
        # rounded to one decimal, so re-rounding it can disagree by one
        # exactly at a .5 (first seen when m2.4.0's rent swap landed a
        # score at 41.5: display 41 from 41.4x, round(41.5) -> 42). The
        # display must be a whole number within half a point of the
        # served score, never recomputed from it.
        assert r["score_display"] == str(int(r["score_display"]))
        assert abs(int(r["score_display"]) - r["score"]) <= 0.55
        assert 0 <= int(r["score_display"]) <= 100


def test_permalink_is_deterministic():
    body = {"self": {"sex": "female", "age": 32},
            "seeking": {"age": [30, 40], "marital": ["never_married"]},
            "pool_vs_match": 0.7,
            "importance": {"cost": "a_lot", "students": "not_much"}}
    a = engine.permalink("dv1", MODEL_VERSION, body)
    b = engine.permalink("dv1", MODEL_VERSION, dict(body))
    assert a == b and a.startswith(f"/r/dv1/{MODEL_VERSION}/")


def test_crime_is_context_never_scored(build, response):
    """Gate 4 of the phase (D01 standing): crime arrives as a composed
    context block with its coverage figure and the FBI's caution — and no
    crime feature ever enters the scored set, the stats list, or a weight.
    Where coverage misses the registry floor, the blank state serves
    instead of a figure."""
    from atlas.model.scoring import scored_features
    scored_ids = {f["id"] for f in scored_features(build)}
    assert not any("crime" in fid for fid in scored_ids)
    floor = float(build.manifest["crime"]["coverage_floor"])
    seen_available = 0
    for r in response["ranked"] + response["suppressed"]:
        assert "crime" in r
        blk = r["crime"]
        assert BANNED.search(blk["caution"]) is None
        # Phase 2f item 5.3: the approved caution names comparing cities
        # rather than ranking them; the sentence must still be the FBI's
        # caution, composed from the registry
        assert "caution" in blk["caution"].lower() and "compare" in blk[
            "caution"].lower(), "the FBI's caution renders"
        for s in r.get("stats", []):
            assert "crime" not in s["id"], "crime may never enter stats"
        if blk["available"]:
            seen_available += 1
            assert blk["coverage_pct"] >= floor * 100
            assert "coverage_line" in blk
            labels = {s["label"] for s in blk["stats"]}
            assert labels == {"Violent crime", "Property crime"}
            for s in blk["stats"]:
                assert s["value"] >= 0 and s["display"]
        else:
            assert "note" in blk and blk["note"]
    assert seen_available >= 1, (
        "the fixture should carry at least one metro above the coverage "
        "floor — if this fails, the coverage table itself is the finding")


def test_missing_feature_policy_renormalizes(build):
    """Missing never becomes zero — the pillar's internal weights
    renormalize, and a fully-missing pillar's weight redistributes."""
    b2 = engine.load_build(FIXTURE_DIR)
    b2.static = {k: v.copy() for k, v in build.static.items()}
    ridx = np.where(build.ranked_set)[0][:4]
    b2.static["rpp_goods"][ridx[0]] = np.nan
    b2.static["pleasant_days"][ridx[1]] = np.nan
    b2.static["students_per_1k_adults"][ridx[1]] = np.nan
    weights = {"pool": .3, "match": .25, "reach": .2, "cost": .15,
               "weather": .06, "students": .04}
    sc = score_components(b2, ridx, np.full(len(ridx), 1000.0),
                          np.full(len(ridx), 100.0), weights)
    feats = [f["id"] for f in sc["feats"]]
    w = sc["w_eff"]
    assert w[0, feats.index("rpp_goods")] == 0.0
    assert w[0, feats.index("rent_1br")] > 0.15 * 0.5
    assert w[1, feats.index("pleasant_days")] == 0.0
    assert w[1, feats.index("pool_size")] > 0.3
    assert w.sum(axis=1) == pytest.approx(np.ones(len(ridx)))


def test_technical_strings_are_separate():
    """The margin wording survives — for the API record and the methodology
    page — but lives apart from the rendered vocabulary."""
    assert "at least" in TECHNICAL_STRINGS["interval"]
    assert not any("margin" in v.lower() for v in POLICY_STRINGS.values()), (
        "rendered policy strings must not speak of margins (ADR 0004)")
