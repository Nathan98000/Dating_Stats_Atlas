"""API tests against the pinned fixture build — the m4.0.0 contract
(ADR 0018 over ADR 0009/0005/0004): the visitor's own sex, education and
race never reach the server, and the response carries every variant."""
import json
import os
import re
from pathlib import Path

import pytest

FIXTURE_DIR = (Path(__file__).resolve().parents[2] / "model" / "tests"
               / "golden" / "fixture_build")
GOLDENS = (Path(__file__).resolve().parents[2] / "model" / "tests"
           / "golden" / "goldens.json")

os.environ["BUILD_DIR"] = str(FIXTURE_DIR)

from fastapi.testclient import TestClient  # noqa: E402

from atlas.api import app as api  # noqa: E402

BODY = {"self": {"age": 30},
        "seeking": {"sex": "male", "age": [28, 40],
                    "marital": ["never_married", "previously_married"]}}


def request_of(golden: dict) -> tuple[dict, tuple]:
    """A golden vector (a full seeker, the model's reference path) as the
    m4.0.0 request plus the variant it names: the own sex, education and
    race move out of the request; the sought sex is explicit."""
    body = json.loads(json.dumps(golden))
    me = body["self"]
    sex = me.pop("sex")
    variant = (sex, me.pop("education", None), me.pop("race_ethnicity", None))
    body["seeking"].setdefault("sex", "male" if sex == "female" else "female")
    return body, variant


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
    # m3.0.0 (ADR 0009): balance is displayed, never scored; the match
    # pillar carries chances of matching, and the panel's pole labels,
    # the four seeker education levels and every new string come from
    # the registry
    assert m["features"]["pool_balance"]["status"] == "context_only"
    assert m["features"]["pool_balance"]["weight_in_pillar"] == 0
    assert "balance" not in m["pillars"]
    assert m["pillars"]["match"]["display_name"] == "Compatibility"
    assert m["features"]["match_propensity"]["pillar"] == "match"
    assert len(m["features"]["match_propensity"]["band_labels"]) == 5
    assert m["controls"]["slider_labels"] == {"low": "Dating pool size",
                                              "high": "Compatibility"}
    assert m["controls"]["slider_control"] == "pool_vs_match"
    assert m["controls"]["self_education_levels"] == api.engine.EDU_LEVELS
    assert m["measure_page"][0] == {"heading": "people", "pillars": ["pool", "match"],
                                    "features": ["pool_balance"]}
    for k in ("match_how", "self_edu_label",
              "self_race_label", "prefer_not_to_say",
              "edu_hs_or_less", "edu_graduate",
              # m3.1.0 / m3.2.0: the display cap and the same-sex sentence
              "match_display_cap", "match_display_cap_token",
              "match_same_sex_note", "match_same_sex_note_all_fallback",
              # Phase 4b: the panel's two section headings and the overall
              # score's label
              "panel_about_you_heading", "panel_looking_for_heading",
              "overall_score_label"):
        assert m["policy_strings"].get(k), k
    # Phase 4b (ADR 0018 amended): the race switch's strings, the "about
    # you" note and the compatibility figure's own box and link are gone
    for gone in ("self_race_switch_label", "self_race_switch_note", "self_race_same_sex_note",
                 "self_race_choose", "about_you_note", "match_info", "match_how_link"):
        assert gone not in m["policy_strings"], gone
    # Phase 4c (ADR 0018 amended): the race field's explanation on a
    # same-sex search, Nathan's wording verbatim, and its touch button's
    # name; balance applies to every search (ADR 0004 amended), so the
    # "doesn't apply" note is retired and no served string says it
    assert m["policy_strings"]["self_race_same_sex_tip"] == (
        "This information is not used to calculate compatibility for same-sex couples "
        "because not enough data is available to make a reliable estimate.")
    assert m["policy_strings"].get("self_race_same_sex_tip_label")
    assert "balance_same_sex" not in m["policy_strings"]
    for k, text in {**m["policy_strings"], **m["technical_strings"]}.items():
        assert "doesn’t apply" not in text and "doesn't apply" not in text, k
    # Nathan's slider text, verbatim (Phase 4b)
    assert m["policy_strings"]["slider_info"] == (
        "Leaning towards size favors larger cities with the most possible matches. Leaning "
        "towards compatibility favors cities with people who match your search more closely "
        "on age, education, and background, based on historical Census couples data.")
    assert m["features"]["match_propensity"]["display_name"] == "Compatibility"
    assert m["kernel"]["version"] == "kernel_v3"
    assert m["features"]["rent_1br"]["display_name"] == "Rent"
    assert len(m["features"]["rent_1br"]["band_labels"]) == 5
    assert m["features"]["rent_1br"]["band_direction"] == "good_low"
    # the four importance controls carry their registry subtitles (item 4)
    assert m["controls"]["importance_pillars"] == \
        ["cost", "reach", "students", "weather"]
    for p in m["controls"]["importance_pillars"]:
        assert m["pillars"][p].get("control_subtitle"), p
    assert m["pillars"]["reach"]["display_name"] == "Social life"
    assert m["city_cards"][0] == "rent_1br"
    assert m["controls"]["marital"] == ["never_married", "previously_married"]
    assert m["controls"]["race_ethnicity"] == list(api.SELECTABLE_RACES)
    # m2.2.0: eight equal groups, labels from the registry (ADR 0006)
    assert [g["id"] for g in m["race_groups"]] == list(api.SELECTABLE_RACES)
    assert len(m["race_groups"]) == 8
    assert all(g["label"] for g in m["race_groups"])
    assert set(m["controls"]["importance_levels"]) == \
        {"not_much", "some", "a_lot"}
    # registry strings merge into the one policy-strings lookup (item 8's
    # ground rule: every new string lives in the registry). Phase 2f: the
    # review's new strings are here, and the two deleted intro paragraphs
    # are GONE rather than orphaned.
    for k in ("slider_info", "crime_caution", "crime_compare_note",
              "stat_page_link", "home_title", "home_subtitle",
              "card_missing", "crime_see_more", "compare_edge",
              "compare_page_subtitle", "measure_context_heading"):
        assert m["policy_strings"].get(k), k
    for gone in ("stat_page_intro", "measure_page_intro"):
        assert gone not in m["policy_strings"], gone
    # Nathan, 2026-10-10: balance's box (one caption on every search), the
    # points' caption and the same-sex note in his words, verbatim; the
    # compare column is "Comparison", the line under the table and the
    # deleted boxes' strings are gone
    assert m["policy_strings"]["balance_caption"] == (
        "Balance compares all single men with all single women in the ages you picked, "
        "no other filters are used for the calculation.")
    assert m["policy_strings"]["same_sex_pool_note"] == (
        "On a same-sex search, matches count every single {sought_one} in these ages, "
        "not just those looking for {sought}.")
    assert m["policy_strings"]["moved_caption"] == "Compared with the median city"
    assert m["policy_strings"]["compare_edge"] == "Comparison"
    for gone in ("compare_edge_note", "compare_diff_legend", "optional_pill", "sharpen_info",
                 "sharpen_info_label", "sharpen_info_link", "moved_info_label", "balance_more",
                 "balance_caption_same_sex"):
        assert gone not in m["policy_strings"], gone
    # the What-we-measure composition ships from the registry (item 8.5)
    assert [g["heading"] for g in m["measure_page"]] == \
        ["people", "cost", "reach", "students", "weather", "context"]
    assert m["measure_page"][1]["features"] == \
        ["rent_1br", "everyday_prices"]
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
    """Every golden vector, sent without its seeker's own sex, education
    and race, returns a response whose variant for that seeker reproduces
    the golden: the same cities in the same order, the same scores,
    figures, balance and summary lines, the same suppression."""
    goldens = json.loads(GOLDENS.read_text())
    for v in goldens["vectors"]:
        body, (sex, edu, race) = request_of(v["request"])
        r = client.post("/v1/rank", json=body)
        assert r.status_code == 200, r.text
        resp = r.json()
        got = api.engine.select_variant(resp, sex, edu, race)
        e = v["expect"]
        assert [x["cbsa"] for x in got["ranked"]] == e["ranked_cbsas"], v["name"]
        assert {x["cbsa"]: x["score"] for x in got["ranked"]} == e["scores"]
        assert {x["cbsa"]: x["score_display"] for x in got["ranked"]} == e["score_displays"]
        assert {x["cbsa"]: x["match"]["value"] for x in got["ranked"]} == e["match_index"]
        assert {x["cbsa"]: (x["balance"]["per_100"] if x["balance"]["available"] else None)
                for x in got["ranked"]} == e["balance_per_100"]
        assert {x["cbsa"]: x["summary_line"] for x in got["ranked"][:3]} == e["summary_lines"]
        assert {x["cbsa"]: x["reason"] for x in got["suppressed"]} == e["suppressed"]
        assert resp["shown_unranked"] == []
        assert sum(resp["counts"]["suppressed_by_reason"].values()) == \
            resp["counts"]["suppressed"]
        # m4.1.0 (ADR 0004 amended): balance is the search's, sent once
        # (variants.balance, aligned to the rows), never per own sex
        bal = resp["variants"]["balance"]
        assert "by_sex" not in resp["variants"] and "balance_applies" not in resp
        assert set(bal["balance_words"]) == {"sought", "seeker"}
        assert len(bal["ranked"]) == len(resp["ranked"])
        assert len(bal["suppressed"]) == len(resp["suppressed"])
        for row in resp["ranked"]:
            # the served rows carry what no variant changes; the rest is in
            # `variants`
            assert {"display_name", "slug", "pool", "cards", "crime", "stats"} <= set(row)
            assert not {"rank", "score", "score_display", "balance",
                        "summary_line", "top_stats"} & set(row)
            assert set(row["match"]) == {"available", "unit_line"}
            assert "cross_group_pairing_rate" not in row
            assert "ratio" not in row and "rivals" not in row
        for row in got["ranked"]:
            assert row["match"]["available"] and row["match"]["display"]


def test_every_variant_equals_the_single_seeker_ranking(client):
    """ADR 0018: the response's variants are exactly what rank() gives each
    seeker — for every own sex, education and race, on an opposite-sex and
    a same-sex search (the margin is computed there and never rendered, and
    the variants leave it out)."""
    from atlas.model.variants import EDU_KEYS, RACE_KEYS
    for body in (BODY, {"self": {"age": 31},
                        "seeking": {"sex": "male", "age": [27, 38],
                                    "marital": ["never_married"]}}):
        resp = client.post("/v1/rank", json=body).json()
        assert len(resp["variants"]["list"]) == 50
        for sex in ("male", "female"):
            for ek in EDU_KEYS:
                for rk in RACE_KEYS:
                    edu = None if ek == "none" else ek
                    race = None if rk == "off" else rk
                    me = {"sex": sex, "age": body["self"]["age"]}
                    if edu:
                        me["education"] = edu
                    if race:
                        me["race_ethnicity"] = race
                    want = api.engine.rank(api.BUILD, api.engine.parse_request({**body, "self": me}))
                    for row in want["ranked"]:
                        row["match"].pop("moe")
                    got = api.engine.select_variant(resp, sex, edu, race)
                    for k in ("counts", "weights", "balance_words",
                              "match_inputs", "score_median", "ranked", "suppressed"):
                        assert got[k] == want[k], (sex, ek, rk, k)
                    assert "balance_applies" not in got and "balance_applies" not in want


def test_balance_is_the_searchs_and_a_same_sex_visitor_sees_it(client):
    """m4.1.0 (ADR 0004 amended, Nathan's decision): balance is the single
    people of the sought sex per 100 of the other sex, so every own sex
    sees the same blocks — a man seeking men 27-38 sees the "N men per 100
    women" a woman seeking the same men sees — and the response carries
    them once."""
    body = {"self": {"age": 31}, "seeking": {"sex": "male", "age": [27, 38],
                                             "marital": ["never_married"],
                                             "education_min": "bachelors"}}
    resp = client.post("/v1/rank", json=body).json()
    same = api.engine.select_variant(resp, "male")
    other = api.engine.select_variant(resp, "female")
    assert same["balance_words"] == other["balance_words"] == {"sought": "men", "seeker": "women"}
    by = lambda sel: {r["cbsa"]: r["balance"] for r in sel["ranked"] + sel["suppressed"]}  # noqa: E731
    assert by(same) == by(other)
    shown = [b for b in by(same).values() if b["available"]]
    assert shown, "the fixture's same-sex search shows balance"
    for b in shown:
        assert b["display"] == f"{b['per_100']} men per 100 women"
    # the single-seeker reference agrees, row for row
    me = lambda sex: {**body, "self": {"sex": sex, "age": 31}}  # noqa: E731
    r_same = api.engine.rank(api.BUILD, api.engine.parse_request(me("male")))
    r_other = api.engine.rank(api.BUILD, api.engine.parse_request(me("female")))
    assert by(r_same) == by(r_other) == by(same)


def test_about_you_never_accepted(client):
    """ADR 0018: the visitor's own sex, education and race are refused
    with a 422 wherever they appear in self, alone or together, and the
    sought sex is required."""
    for extra in ({"sex": "female"}, {"education": "bachelors"},
                  {"race_ethnicity": "black_nh"},
                  {"sex": "male", "education": "graduate", "race_ethnicity": "asian_nh"}):
        r = client.post("/v1/rank", json={**BODY, "self": {"age": 30, **extra}})
        assert r.status_code == 422, extra
        assert "stay in their browser" in r.text
    no_sought = client.post("/v1/rank", json={
        "self": {"age": 30}, "seeking": {"age": [28, 40], "marital": ["never_married"]}})
    assert no_sought.status_code == 422


def test_permalink_carries_no_about_you(client):
    """The permalink token encodes the own age and the partner filters —
    nothing about the visitor's sex, education or race."""
    import base64
    resp = client.post("/v1/rank", json=BODY).json()
    tok = resp["permalink"].rsplit("/", 1)[1]
    core = json.loads(base64.urlsafe_b64decode(tok + "=" * (-len(tok) % 4)))
    assert core["self"] == {"age": 30}
    assert core["seeking"]["sex"] == "male"


def test_referrer_policy_on_every_response(client):
    """ADR 0018: every response of the API says Referrer-Policy:
    no-referrer — success, validation error, version clash and not found."""
    for r in (client.get("/v1/health"), client.get("/v1/meta"),
              client.post("/v1/rank", json=BODY),
              client.post("/v1/rank", json={**BODY, "self": {"age": 30, "sex": "male"}}),
              client.post("/v1/rank", json={"data_version": "not-a-build", **BODY}),
              client.get("/v1/nowhere")):
        assert r.headers.get("referrer-policy") == "no-referrer", (r.request.url, r.status_code)


def test_sort_reverses_without_changing_ranks(client):
    """Gate 3: worst_first reverses the same ranked array — same cities,
    same scores, same ranks, never widened (m4.0.0: the selected variant
    is reversed; the served rows are the same)."""
    best_r = client.post("/v1/rank", json={**BODY, "sort": "best_first"}).json()
    worst_r = client.post("/v1/rank", json={**BODY, "sort": "worst_first"}).json()
    assert worst_r["sort"] == "worst_first"
    assert best_r["ranked"] == worst_r["ranked"] and best_r["variants"] == worst_r["variants"]
    best = api.engine.select_variant(best_r)
    worst = api.engine.select_variant(worst_r)
    a = [(r["cbsa"], r["rank"], r["score"]) for r in best["ranked"]]
    b = [(r["cbsa"], r["rank"], r["score"]) for r in worst["ranked"]]
    assert b == list(reversed(a))
    assert best["counts"] == worst["counts"]
    assert worst["ranked"][0]["rank"] == len(a), (
        "the city shown first under worst-first keeps its earned rank")


def test_marital_restricted_to_two_values(client):
    r = client.post("/v1/rank", json={
        "self": {"age": 32},
        "seeking": {"sex": "male", "age": [30, 40], "marital": ["currently_married"]}})
    assert r.status_code == 422


def test_eight_race_groups_selectable_and_equal(client):
    """m2.2.0 (ADR 0006): the two formerly always-counted groups are
    ordinary checkboxes; empty and all-eight both mean no filter."""
    r = client.post("/v1/rank", json={
        "self": {"age": 32},
        "seeking": {"sex": "male", "age": [30, 40], "marital": ["never_married"],
                    "race_ethnicity": ["two_or_more_nh"]}})
    assert r.status_code == 200
    r2 = client.post("/v1/rank", json={
        "self": {"age": 32},
        "seeking": {"sex": "male", "age": [30, 40], "marital": ["never_married"],
                    "race_ethnicity": ["other_nh", "two_or_more_nh"]}})
    assert r2.status_code == 200
    rall = client.post("/v1/rank", json={
        "self": {"age": 30},
        "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married"]}})
    for body in (
        {"self": {"age": 30},
         "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married"],
                     "race_ethnicity": []}},
        {"self": {"age": 30},
         "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married"],
                     "race_ethnicity": list(api.SELECTABLE_RACES)}},
    ):
        resp = client.post("/v1/rank", json=body)
        assert resp.status_code == 200
        got = {x["cbsa"]: x["pool"] for x in resp.json()["ranked"]}
        want = {x["cbsa"]: x["pool"] for x in rall.json()["ranked"]}
        assert got == want, "empty and all-eight are the unfiltered universe"


def test_slider_alias_and_stray_weight(client):
    """The deprecated pool_vs_balance name still maps to the slider (same
    weights, same permalink); naming both is a 422, and a stray
    weights.balance key fails loudly."""
    new = client.post("/v1/rank", json={**BODY, "pool_vs_match": 0.8}).json()
    old = client.post("/v1/rank", json={**BODY, "pool_vs_balance": 0.8}).json()
    assert new["weights"] == old["weights"] and new["permalink"] == old["permalink"]
    both = client.post("/v1/rank", json={**BODY, "pool_vs_match": 0.8,
                                         "pool_vs_balance": 0.2})
    assert both.status_code == 422
    stray = client.post("/v1/rank", json={**BODY, "weights": {"pool": 0.5, "balance": 0.5}})
    assert stray.status_code == 422


def test_named_controls_and_conflicts(client):
    ok = client.post("/v1/rank", json={
        **BODY, "pool_vs_match": 0.7,
        "importance": {"cost": "a_lot", "reach": "not_much",
                       "students": "a_lot", "weather": "not_much"}})
    assert ok.status_code == 200
    w = ok.json()["weights"]
    assert w["match"] > w["pool"]
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
        **BODY, "weights": {"pool": 1.0}, "pool_vs_match": 0.5})
    assert both.status_code == 422


def test_crime_block_served_never_scored(client):
    """Item 5 through HTTP: every row carries the composed crime block
    (figures + coverage + caution, or the blank state), crime never
    appears among the scored stats, and the weights never name it."""
    r = client.post("/v1/rank", json=BODY).json()
    assert set(r["weights"]) == {"pool", "match", "reach", "cost",
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


def _property_names(schema) -> set[str]:
    """Every property name anywhere in a JSON schema."""
    out: set[str] = set()
    if isinstance(schema, dict):
        out |= set((schema.get("properties") or {}))
        for v in schema.values():
            out |= _property_names(v)
    elif isinstance(schema, list):
        for v in schema:
            out |= _property_names(v)
    return out


def test_political_lean_is_served_apart_and_never_scored_or_asked(client):
    """Phase 4d (ADR 0019, Nathan's decision): political lean has its own
    read-only endpoint. /v1/rank neither carries it nor accepts it: no
    request field names it, the weights and the scored stats never do, and
    a stray field is refused (top level, weights, importance) or dropped
    (seeking) — the response byte for byte the same."""
    lean = client.get("/v1/political_lean")
    assert lean.status_code == 200
    body = lean.json()
    assert body["year"] == "2024" and len(body["metros"]) == 12
    assert all(b["available"] for b in body["metros"].values())
    named = {n for n in _property_names(api.RankRequest.model_json_schema())
             if re.search(r"politic|lean|party|vote|democrat|republican", n, re.I)}
    assert not named, named
    r = client.post("/v1/rank", json=BODY)
    assert r.status_code == 200 and b"politic" not in r.content.lower()
    out = r.json()
    assert set(out["weights"]) == {"pool", "match", "reach", "cost", "weather", "students"}
    for row in out["ranked"] + out["suppressed"]:
        assert "political_lean" not in row
        assert all(s["id"] != "political_lean" for s in row.get("stats", []))
    assert client.post("/v1/rank", json={**BODY, "political_lean": "x"}).status_code == 422
    assert client.post("/v1/rank", json={**BODY, "weights": {"pool": 1.0, "political_lean": 1.0}}
                       ).status_code == 422
    assert client.post("/v1/rank", json={**BODY, "importance": {"political_lean": "a_lot"}}
                       ).status_code == 422
    stray = json.loads(json.dumps(BODY))
    stray["seeking"]["political_lean"] = "Democratic"
    r2 = client.post("/v1/rank", json=stray)
    assert r2.status_code == 200 and r2.content == r.content
    m = client.get("/v1/meta").json()
    assert m["features"]["political_lean"]["status"] == "context_only"
    assert m["features"]["political_lean"]["weight_in_pillar"] == 0
    assert "political_lean" in m["stat_pages"] and "political_lean" not in m["city_cards"]
    assert m["measure_page"][-1]["features"] == ["who_lives_here", "political_lean"]


def test_every_metro_has_a_profile_the_rank_rows_agree_with(client):
    """POST /v1/profile: every metro of the build — the ranked set's and the
    one below its population floor (Eagle Pass), which no search returns —
    has its stat cards and crime block; a ranked or suppressed row carries
    the same blocks; /v1/rank's response is byte for byte the same before
    and after a profile is read. The body names the metro and nothing else,
    so no search detail reaches it and no access line names the city."""
    m = client.get("/v1/meta").json()
    below = [x["cbsa"] for x in m["metros"] if not x["ranked_set"]]
    assert below == ["20580"]
    before = client.post("/v1/rank", json=BODY)
    assert before.status_code == 200
    rows = {r["cbsa"]: r for r in before.json()["ranked"] + before.json()["suppressed"]}
    assert set(rows) == {x["cbsa"] for x in m["metros"] if x["ranked_set"]}
    for x in m["metros"]:
        r = client.post("/v1/profile", json={"cbsa": x["cbsa"]})
        assert r.status_code == 200, x["cbsa"]
        assert r.headers.get("referrer-policy") == "no-referrer"
        p = r.json()
        assert set(p) == {"data_version", "cbsa", "cards", "crime"}
        assert p["cbsa"] == x["cbsa"] and p["data_version"] == m["data_version"]
        assert [c["id"] for c in p["cards"]] == m["city_cards"]
        assert all(c.get("display") and c.get("band") for c in p["cards"]), x["cbsa"]
        assert p["crime"]["caution"] and p["crime"]["compare_banner"]
        if x["cbsa"] in rows:
            assert p["cards"] == rows[x["cbsa"]]["cards"]
            assert p["crime"] == rows[x["cbsa"]]["crime"]
    assert client.post("/v1/rank", json=BODY).content == before.content
    assert client.post("/v1/profile", json={"cbsa": "99999"}).status_code == 404
    assert client.post("/v1/profile", json={"cbsa": "20580", "self": {"age": 30}}).status_code == 422
    assert client.post("/v1/profile", json={}).status_code == 422
    assert client.get("/v1/profile").status_code == 405
    assert client.get("/v1/profile/20580").status_code == 404


def test_income_floor_validation(client):
    r = client.post("/v1/rank", json={
        "self": {"age": 32},
        "seeking": {"sex": "male", "age": [30, 40], "marital": ["never_married"],
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
