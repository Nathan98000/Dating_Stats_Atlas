"""Phase 4d: the political lean measure's aggregation rules, on small
tables shaped like the county returns (adapters/medsl_president.py
normalises the file to these columns). Every rule the measure applies is
held here: TOTAL rows or the sum of the modes, never both; non-votes never
count, whatever their party; a metro across state lines sums its votes and
divides once; Connecticut's former counties and Alaska's districts never
stand in for the delineation's counties; a county missing from the returns
makes its metro Not available rather than an undercount."""
import numpy as np
import pandas as pd
import pytest

from atlas.pipeline.build import political_lean as PL


def unit(fips, st, name, cands, year="2024", mode="TOTAL", total=None):
    """Rows for one reporting unit: cands is [(candidate, party, votes)]."""
    tv = total if total is not None else sum(v for c, p, v in cands
                                             if c not in PL.NOT_VOTES)
    return [{"year": year, "state_po": st, "county_fips": fips, "county_name": name,
             "candidate": c, "party": p, "mode": mode, "votes": float(v),
             "totalvotes": float(tv)} for c, p, v in cands]


def D(v):
    return ("KAMALA D HARRIS", "DEMOCRAT", v)


def R(v):
    return ("DONALD J TRUMP", "REPUBLICAN", v)


def O(v):
    return ("OTHER", "OTHER", v)


def frame(*units):
    return pd.DataFrame([r for u in units for r in u])


def delin(pairs):
    return pd.DataFrame([{"cbsa": c, "county5": f} for c, f in pairs])


def test_total_rows_are_used_where_they_exist_and_modes_are_never_added_to_them():
    total = unit("48001", "TX", "ANDERSON", [D(3635), R(15597), O(126)])
    early = unit("48001", "TX", "ANDERSON", [D(2677), R(11566), O(75)], mode="EARLY VOTING",
                 total=19358)
    u = PL.unit_totals(frame(total, early)).iloc[0]
    assert u["rule"] == "TOTAL"
    assert (u["dem"], u["rep"], u["valid"]) == (3635, 15597, 19358)


def test_a_unit_without_a_total_row_sums_its_modes():
    day = unit("46011", "SD", "BROOKINGS", [D(100), R(200)], mode="ELECTION DAY", total=450)
    vc = unit("46011", "SD", "BROOKINGS", [D(50), R(100)], mode="VOTE CENTER", total=450)
    u = PL.unit_totals(frame(day, vc)).iloc[0]
    assert u["rule"].startswith("modes:")
    assert (u["dem"], u["rep"], u["valid"]) == (150, 300, 450)
    assert u["reconciles"]


def test_rows_with_no_mode_are_the_unit_itself():
    u = PL.unit_totals(frame(unit("16001", "ID", "ADA", [D(116116), R(143759), O(7544)],
                                  mode=""))).iloc[0]
    assert u["rule"] == "modes:" and u["valid"] == 267419


def test_a_candidate_only_in_split_modes_is_named_not_lost_silently():
    total = unit("35001", "NM", "X", [D(10), R(20)])
    split = unit("35001", "NM", "X", [("CHASE OLIVER", "LIBERTARIAN", 3)], mode="EARLY",
                 total=30)
    u = PL.unit_totals(frame(total, split)).iloc[0]
    assert u["split_only_candidates"] == ["CHASE OLIVER"]


def test_non_votes_never_count_whatever_their_party():
    """Arizona's and Iowa's OVERVOTES and UNDERVOTES carry party OTHER; the
    TOTAL VOTES CAST rows (South Carolina) sit in the TOTAL mode."""
    az = unit("04013", "AZ", "MARICOPA",
              [D(100), R(120), O(5), ("OVERVOTES", "OTHER", 3), ("UNDERVOTES", "OTHER", 7)],
              total=235)
    sc = unit("45001", "SC", "ABBEVILLE",
              [D(3399), R(8509), O(140), ("TOTAL VOTES CAST", "", 12048)])
    u = PL.unit_totals(frame(az, sc)).set_index("county_fips")
    assert u.loc["04013", "valid"] == 225 and u.loc["04013", "other"] == 5
    assert u.loc["04013", "non_votes"] == 10 and u.loc["04013", "reconciles"]
    assert u.loc["45001", "valid"] == 12048 and u.loc["45001", "total_votes_cast_row"] == 12048


def test_a_metro_across_state_lines_sums_its_votes_then_divides():
    """Two counties in two states: 90% of a small county and 40% of a large
    one is 42.7% of the metro — not the 65% an average of percentages says."""
    small = unit("34001", "NJ", "A", [D(90), R(10)])
    large = unit("42001", "PA", "B", [D(400), R(600)])
    u = PL.unit_totals(frame(small, large))
    m = PL.metro_totals(u, delin([("99999", "34001"), ("99999", "42001")]), {"99999"})
    r = m.iloc[0]
    assert r["available"] and r["states"] == "34+42" and r["n_counties"] == 2
    assert r["dem_share"] == pytest.approx(490 / 1100)
    assert r["dem_share"] != pytest.approx((0.9 + 0.4) / 2)


def test_a_county_missing_from_the_returns_makes_its_metro_not_available():
    u = PL.unit_totals(frame(unit("01001", "AL", "AUTAUGA", [D(10), R(20)])))
    m = PL.metro_totals(u, delin([("11111", "01001"), ("11111", "01003")]), {"11111"})
    r = m.iloc[0]
    assert not r["available"] and r["reason"] == "county_missing_from_returns"
    assert r["missing_counties"] == ["01003"] and np.isnan(r["valid"])


def test_connecticut_former_counties_never_stand_in_for_planning_regions():
    u = PL.unit_totals(frame(unit("9001", "CT", "FAIRFIELD", [D(300), R(200)]),
                             unit("9009", "CT", "NEW HAVEN", [D(250), R(200)])))
    m = PL.metro_totals(u, delin([("14860", "09120"), ("14860", "09190")]), {"14860"})
    r = m.iloc[0]
    assert not r["available"] and r["reason"] == "connecticut_reports_by_former_county"


def test_alaska_districts_never_join_as_boroughs():
    """DISTRICT 20's code, 2020, reads as 02020 — Anchorage Municipality's.
    Without a clean district mapping the metro is Not available, never
    one district's votes under the borough's name."""
    u = PL.unit_totals(frame(unit("2020", "AK", "DISTRICT 20", [D(3000), R(4000)])))
    m = PL.metro_totals(u, delin([("11260", "02020"), ("11260", "02170")]), {"11260"})
    r = m.iloc[0]
    assert not r["available"] and r["reason"] == "alaska_reports_by_district"


def _rel(rows):
    return pd.DataFrame([{"GEOID_SLDL2024_20": d, "GEOID_TRACT_20": t,
                          "AREALAND_TRACT_20": tl, "AREALAND_PART": p} for d, t, tl, p in rows])


def test_an_alaska_metro_is_built_only_from_districts_wholly_inside_it():
    # districts 01 and 02 lie inside borough 02020; district 03 spans the
    # metro's second borough and a populated tract outside it
    rel = _rel([("02001", "02020000100", 10, 10), ("02002", "02020000200", 10, 10),
                ("02003", "02170000100", 50, 50), ("02003", "02068000100", 90, 90)])
    pop = {"02020000100": 100, "02020000200": 100, "02170000100": 80, "02068000100": 1619}
    v = PL.alaska_district_check(rel, pop, {"clean": {"02020"}, "crossed": {"02020", "02170"}})
    assert v["clean"]["clean"] and v["clean"]["districts"] == ["02001", "02002"]
    assert not v["crossed"]["clean"]
    (x,) = v["crossed"]["crossing"]
    assert x["district"] == "02003" and x["population_2020_of_those_tracts"] == 1619
    u = PL.unit_totals(frame(unit("2001", "AK", "DISTRICT 01", [D(10), R(30)]),
                             unit("2002", "AK", "DISTRICT 02", [D(20), R(40)])))
    m = PL.metro_totals(u, delin([("clean", "02020")]), {"clean"}, {"clean": v["clean"]})
    r = m.iloc[0]
    assert r["available"] and (r["dem"], r["rep"], r["valid"]) == (30, 70, 100)
    m2 = PL.metro_totals(u, delin([("crossed", "02020"), ("crossed", "02170")]), {"crossed"},
                         {"crossed": v["crossed"]})
    assert m2.iloc[0]["reason"] == "alaska_districts_cross_the_metro"


def test_an_unpopulated_outside_tract_does_not_make_a_district_cross():
    rel = _rel([("02001", "02020000100", 10, 10), ("02001", "02063000300", 90, 5)])
    v = PL.alaska_district_check(rel, {"02020000100": 100, "02063000300": 0}, {"m": {"02020"}})
    assert v["m"]["clean"]


def test_kansas_city_adds_to_its_metro_and_kalawao_is_counted_with_maui():
    kc = unit("36000", "MO", "KANSAS CITY", [D(100), R(50)])
    counties = [unit(f, "MO", n, [D(10), R(10)]) for f, n in
                (("29095", "JACKSON"), ("29047", "CLAY"), ("29165", "PLATTE"), ("29037", "CASS"))]
    maui = unit("15009", "HI", "MAUI", [D(40), R(30)])
    u = PL.unit_totals(frame(kc, *counties, maui))
    m = PL.metro_totals(u, delin([("28140", "29095"), ("28140", "29047"), ("28140", "29165"),
                                  ("28140", "29037"), ("27980", "15009"), ("27980", "15005")]),
                        {"28140", "27980"}).set_index("cbsa")
    assert m.loc["28140", "available"] and m.loc["28140", "valid"] == 230
    assert "36000" in m.loc["28140", "units"]
    assert m.loc["27980", "available"] and m.loc["27980", "valid"] == 70


def test_the_state_check_flags_a_state_outside_the_tolerance():
    u = PL.unit_totals(frame(unit("23005", "ME", "CUMBERLAND", [D(1000), R(1000)]),
                             unit("50001", "VT", "ADDISON", [D(500), R(500)])))
    s = pd.DataFrame([
        {"year": "2024", "state_po": "ME", "candidate": "HARRIS", "party_simplified": "DEMOCRAT",
         "votes": 1010.0, "totalvotes": 2010.0},
        {"year": "2024", "state_po": "ME", "candidate": "TRUMP", "party_simplified": "REPUBLICAN",
         "votes": 1000.0, "totalvotes": 2010.0},
        {"year": "2024", "state_po": "VT", "candidate": "HARRIS", "party_simplified": "DEMOCRAT",
         "votes": 500.0, "totalvotes": 1003.0},
        {"year": "2024", "state_po": "VT", "candidate": "TRUMP", "party_simplified": "REPUBLICAN",
         "votes": 500.0, "totalvotes": 1003.0},
        {"year": "2024", "state_po": "VT", "candidate": "UNDERVOTES", "party_simplified": "OTHER",
         "votes": 3.0, "totalvotes": 1003.0}])
    c = PL.state_check(u, s).set_index("state_po")
    assert not c.loc["ME", "within_tolerance"]
    assert c.loc["ME", "dem_diff_pct"] == pytest.approx(-10 / 1010 * 100)
    assert c.loc["VT", "within_tolerance"] and c.loc["VT", "valid_state"] == 1000
