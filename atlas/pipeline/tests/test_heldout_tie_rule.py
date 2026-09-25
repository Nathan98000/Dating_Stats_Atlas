"""Phase 3d R (ADR 0014): the held-out tie rule — a difference smaller than
HELDOUT_TIE_MARGIN_PER_1000 per 1,000 weighted couple-sides is a tie, and a
tie goes to the simpler form. Synthetic forms and records; no build, no
database, no fit."""
import pytest

from atlas.pipeline.build import kernel_refine as KR

D = KR.HELDOUT_TIE_MARGIN_PER_1000
EDGES = (20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 43, 46, 50, 55, 60)     # Phase 3b's seventeen cohorts
SHIPPED = KR.Form(interaction=True, name="shipped")
C1 = KR.Form(age_edges=EDGES, interaction=True, name="C1")
C2 = KR.Form(edu_by_sex=True, interaction=True, name="C2")
C3 = KR.Form(age_edges=EDGES, edu_by_sex=True, interaction=True, name="C3")


def _cands(**gains):
    forms = {"C1": C1, "C2": C2, "C3": C3}
    return {n: {"form": forms[n], "gain_per_1000": g, "qualifies": True, "gate_ratio": 0.97}
            for n, g in gains.items()}


def test_the_margin_is_the_named_constant_and_the_adr_is_recorded():
    assert D == 0.25 and KR.HELDOUT_TIE_ADR == "0014"


def test_a_gain_of_exactly_delta_beats():
    assert KR.beats(D)
    assert KR.beats(D + 1e-12)
    assert KR.beats(2.898)                       # the smallest margin that has decided a served term


def test_a_margin_just_under_delta_ties_whichever_its_sign():
    for g in (D - 1e-9, 0.2, 0.007, 0.0, -0.007, -0.2, -(D - 1e-9)):
        assert not KR.beats(g), g                # A does not beat B ...
        assert not KR.beats(-g), g               # ... and B does not beat A: a tie
    assert KR.beats(-(-D))                       # B ahead by exactly delta: B beats A


def test_a_tie_goes_to_the_nested_form():
    # the A2 reading: C3 ahead of C1 by 0.007, both qualify -> tied; C1 is nested in C3
    r = KR.select_form(_cands(C1=69.707, C2=0.007, C3=69.715))
    assert r["qualifying"] == ["C1", "C3"] and r["largest_gain"] == "C3"
    assert r["tied_for_first"] == ["C1", "C3"] and r["winner"] == "C1"
    assert r["settled_by"].startswith("nesting")
    assert r["candidates"]["C3"]["tied_forms_nested_in_it"] == ["C1"]
    # C3 ahead by just under delta: still a tie, still C1; by exactly delta: C3 beats C1 and ships
    assert KR.select_form(_cands(C1=69.707, C3=69.707 + D - 1e-9))["winner"] == "C1"
    r = KR.select_form(_cands(C1=69.707, C3=69.707 + D))
    assert r["winner"] == "C3" and r["tied_for_first"] == ["C3"]
    # the reverse: C1 ahead of C3 by a hair (Phase 3c's reading) is C1 either way
    assert KR.select_form(_cands(C1=69.705, C3=69.704))["winner"] == "C1"


def test_nesting_is_read_from_the_form():
    assert KR.nested_in(SHIPPED, C1) and KR.nested_in(SHIPPED, C2) and KR.nested_in(C1, C3) and KR.nested_in(C2, C3)
    assert not KR.nested_in(C3, C1) and not KR.nested_in(C1, C2) and not KR.nested_in(C2, C1)
    assert KR.nested_in(C1, C1)
    # a coarser partition is nested in a finer one only if every boundary is kept
    assert KR.nested_in(KR.Form(age_edges=(30,)), KR.Form(age_edges=(30, 45)))
    assert not KR.nested_in(KR.Form(age_edges=(35,)), KR.Form(age_edges=(30, 45)))


def test_free_parameters_are_computed_from_the_form():
    fp = {f.name: KR.free_parameters(f) for f in (SHIPPED, C1, C2, C3, KR.Form(name="baseline"))}
    assert fp["baseline"]["total"] == 2 * (KR.N_GAP - 1) + 4 * 3 + 2 * 8 * 7
    assert fp["C1"]["age"] == 2 * 17 * (KR.N_GAP - 1) and fp["C2"]["edu"] == 2 * 4 * 3
    assert fp["shipped"]["interaction"] == KR.N_INT - 188 and fp["C2"]["interaction"] == KR.N_INT - 200
    # nesting never adds fewer parameters; with the interaction present the
    # per-sex matrix adds no free direction (it moves twelve from under the ridge)
    assert fp["shipped"]["total"] <= fp["C1"]["total"] and fp["C1"]["total"] <= fp["C3"]["total"]
    assert fp["shipped"]["total"] == fp["C2"]["total"] and fp["C1"]["total"] == fp["C3"]["total"]
    assert fp["C2"]["total"] < fp["C1"]["total"]


def test_at_equal_complexity_gate_ratio_then_served_form_then_table_order():
    # two-cohort forms with different boundaries: neither nested in the other, the same count
    X, Y = KR.Form(age_edges=(30,), name="X"), KR.Form(age_edges=(40,), name="Y")
    assert KR.free_parameters(X)["total"] == KR.free_parameters(Y)["total"]

    def cands(rx, ry):
        return {"X": {"form": X, "gain_per_1000": 5.0, "gate_ratio": rx},
                "Y": {"form": Y, "gain_per_1000": 5.1, "gate_ratio": ry}}
    r = KR.select_form(cands(0.98, 0.97))
    assert r["tied_for_first"] == ["X", "Y"] and r["winner"] == "Y" and "gate ratio" in r["settled_by"]
    r = KR.select_form(cands(0.97, 0.97), served="Y")
    assert r["winner"] == "Y" and r["settled_by"] == "the form already served"
    r = KR.select_form(cands(0.97, 0.97))
    assert r["winner"] == "X" and "earlier form" in r["settled_by"]
    r = KR.select_form(cands(None, None), served="Y")
    assert r["winner"] == "Y"                      # no ratios on record: served, then table order


def test_a_yes_no_tie_keeps_the_simpler_option():
    """Whether the interaction rides on same-sex searches (and whether the
    education term ships) goes through beats: the richer option only if it
    beats the simpler one; a tie keeps the interaction off."""
    def lomo(margin_per_1000, edu_gain_per_1000=15.0):
        sides = 1000.0
        rows = []
        for i in range(2):                       # two metros, 1,000 sides each
            base = -50000.0 - i
            rows.append({"cbsa": str(i), "sides": sides, "fallback": base - 300, "all_samesex": base + 100,
                         "only_age": base, "only_edu": base - 290, "only_race": base - 250,
                         "served_m3_2_0": base,
                         "age_edu_ss_no_interaction": base + edu_gain_per_1000 * sides / 1000,
                         "age_edu_ss_with_interaction": base + (edu_gain_per_1000 + margin_per_1000) * sides / 1000})
        return rows
    support = {"supported": {"age": True, "edu": True, "race": False}}
    face = {"age": True, "edu": True, "race": True}
    h = KR.samesex_decision(lomo(D - 1e-6), support, face)
    assert h["interaction_applies"] is False and abs(h["interaction_decision"]["margin_per_1000_sides"] - (D - 1e-6)) < 1e-9
    assert h["vs_m3_2_0_served"]["education_term_improves_on_served"] and h["served_from_same_sex_couples"] == ["age", "edu"]
    h = KR.samesex_decision(lomo(D), support, face)
    assert h["interaction_applies"] is True
    h = KR.samesex_decision(lomo(-3.0), support, face)
    assert h["interaction_applies"] is False
    # the education term itself: a tie with what m3.2.0 serves keeps the served composition
    h = KR.samesex_decision(lomo(0.0, edu_gain_per_1000=D - 1e-6), support, face)
    assert not h["vs_m3_2_0_served"]["education_term_improves_on_served"]
    assert h["stop_condition_education_no_longer_improves"]
    # a component that beats the fallback by less than delta is not served
    rows = lomo(3.0)
    for x in rows:
        x["only_race"] = x["fallback"] + 0.2 * x["sides"] / 1000
    h = KR.samesex_decision(rows, {"supported": {"age": True, "edu": True, "race": True}}, face)
    assert h["components"]["race"]["improves_heldout"] is False and "race" not in h["served_from_same_sex_couples"]
    assert h["tie_rule"] == {"adr": "0014", "margin_per_1000_sides": D, "rule": h["tie_rule"]["rule"]}


def test_a_candidate_within_delta_of_zero_does_not_qualify():
    r = KR.select_form(_cands(C1=69.707, C2=0.007, C3=69.715))
    assert not r["candidates"]["C2"]["beats_reference"] and not r["candidates"]["C2"]["qualifies"]
    assert "C2" not in r["qualifying"]
    for g in (D - 1e-9, 0.0, -0.1, -(D - 1e-9)):
        assert not KR.select_form(_cands(C2=g))["qualifying"]
    assert KR.select_form(_cands(C2=D))["winner"] == "C2"
    # the gate still gates: a large gain with a failing gate does not qualify either
    c = _cands(C1=69.707)
    c["C1"]["qualifies"] = False
    r = KR.select_form(c)
    assert r["winner"] is None and r["settled_by"] == "no candidate qualifies"


def test_the_margin_is_a_parameter_of_both_functions():
    assert KR.beats(0.1, margin=0.1) and not KR.beats(0.1, margin=0.2)
    assert KR.select_form(_cands(C1=69.707, C3=69.715), margin=0.005)["winner"] == "C3"
    assert KR.select_form(_cands(C1=69.707, C3=69.715), margin=0.01)["winner"] == "C1"
