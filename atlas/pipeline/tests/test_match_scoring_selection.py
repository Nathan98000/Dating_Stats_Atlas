"""Nathan's call after Phase 3d (ADR 0013, amended): the selection among
the match-scoring candidates carries a match-end margin — a difference in
match-end wobble smaller than MATCH_END_MARGIN of N0's total is no
difference. Synthetic records; no build, no database."""
import copy
import inspect

from atlas.pipeline.build import match_scoring_candidates as MSC


def _rec(match_end, gate_set=250.0, gate=True, outlier=True):
    return {"gate": {"pass": gate}, "outlier_condition": {"passes": outlier},
            "match_end_wobble_total": match_end, "gate_set_wobble_total": gate_set}


def _recs(**candidates):
    """N0 at 1,000 places of match-end wobble, so the margin is 50 places."""
    return {"N0": _rec(1000.0, gate_set=300.0), **candidates}


def test_the_margin_is_the_named_constant_and_main_selects_through_it():
    assert MSC.MATCH_END_MARGIN == 0.05
    assert "select(out[\"rules\"])" in inspect.getsource(MSC.main)
    assert MSC.select(_recs())["margin_places"] == 50.0


def test_exactly_five_percent_below_n0_qualifies_and_4_9_does_not():
    s = MSC.select(_recs(V1=_rec(950.0)))
    assert s["candidates"]["V1"]["at_least_margin_below_N0"] and s["qualifying"] == ["V1"] and s["ships"] == "V1"
    assert s["candidates"]["V1"]["match_end_reduction_vs_N0_fraction"] == 0.05
    s = MSC.select(_recs(V1=_rec(951.0)))
    assert not s["candidates"]["V1"]["qualifies"] and s["qualifying"] == [] and s["ships"] is None


def test_candidates_inside_the_tie_band_go_to_the_lower_gate_set_total():
    # V1 has the lowest match-end total; V2 is 40 places above it, inside the
    # 50-place band, and steadier on the gate's own set, so V2 ships
    recs = _recs(V1=_rec(900.0, gate_set=250.0), V2=_rec(940.0, gate_set=240.0))
    s = MSC.select(recs)
    assert s["lowest_match_end"] == "V1" and s["tied_for_first"] == ["V1", "V2"] and s["ships"] == "V2"
    assert s["settled_by"] == "the lower gate-set total among those tied for first"
    # a difference of exactly the margin is a difference: no tie, the lowest ships
    s = MSC.select(_recs(V1=_rec(900.0, gate_set=250.0), V2=_rec(950.0, gate_set=200.0)))
    assert s["qualifying"] == ["V1", "V2"] and s["tied_for_first"] == ["V1"] and s["ships"] == "V1"
    # the function reads its records and leaves them as they were
    before = copy.deepcopy(recs)
    MSC.select(recs)
    assert recs == before


def test_an_exact_tie_goes_to_the_table_order():
    # given out of table order, with equal gate-set totals, inside the band
    recs = {"V3": _rec(920.0, gate_set=240.0), "N0": _rec(1000.0), "V1": _rec(900.0, gate_set=240.0)}
    s = MSC.select(recs)
    assert s["tied_for_first"] == ["V1", "V3"] and s["ships"] == "V1"
    assert s["settled_by"] == "an exact tie on the gate-set total: the earlier candidate in the table"


def test_n0_never_qualifies():
    # N0 passes everything it can; it is not 5% below itself, and it is the
    # control even when no margin is asked of it
    recs = _recs(V1=_rec(900.0, outlier=False))
    for margin in (MSC.MATCH_END_MARGIN, 0.0):
        s = MSC.select(recs, margin=margin)
        assert not s["candidates"]["N0"]["qualifies"] and "N0" not in s["qualifying"] and s["ships"] is None
    assert MSC.select(recs, margin=0.0)["candidates"]["N0"]["at_least_margin_below_N0"]


def test_no_qualifier_ships_nothing():
    recs = _recs(V1=_rec(800.0, gate=False), V2=_rec(850.0, outlier=False), V3=_rec(970.0))
    s = MSC.select(recs)
    assert s["qualifying"] == [] and s["ships"] is None and s["tied_for_first"] == []
    assert s["settled_by"] == "no candidate qualifies: nothing ships"
    assert [s["candidates"][r]["qualifies"] for r in ("V1", "V2", "V3")] == [False, False, False]
    # and without N0 on the record nothing can be read against it
    assert MSC.select({"V1": _rec(800.0)})["ships"] is None
