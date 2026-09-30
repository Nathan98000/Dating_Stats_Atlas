"""Political lean (Phase 4d): each metro's 2024 presidential vote —
Democratic, Republican and everyone else, each a share of every vote cast
for a presidential candidate — from the MIT Election Data and Science
Lab's county returns (adapters/medsl_president.py). 2020 is computed the
same way, for validation and the record only.

The measure, one rule everywhere:

  * a reporting unit's votes are its TOTAL rows where it has them, and the
    sum of its modes otherwise — never both (`unit_totals`);
  * rows that are no vote for anyone (TOTAL VOTES CAST, UNDERVOTES,
    OVERVOTES, SPOILED) never count, whatever their party; the
    denominator is the votes cast for a candidate, every candidate and
    write-in included;
  * units add up to metros through the build's own county -> CBSA
    crosswalk, OMB Bulletin 23-01's delineation (the county-level sources'):
    votes are summed across a metro's counties and divided once — never an
    average of county percentages (`metro_totals`);
  * a metro is available only if every one of its counties is covered
    exactly: a county missing from the returns makes its metro "Not
    available", never an undercount.

Where the returns' units are not counties, the rule is explicit:

  * Connecticut reports by its eight former counties; the 2023
    delineation builds Connecticut's metros from planning regions, which
    the former counties do not nest in (and no planning region is a union
    of them), so no Connecticut metro can be built exactly;
  * Alaska reports by state house district. A metro is built from
    districts only if some set of whole districts covers it exactly: no
    district that touches it reaches a populated tract outside it
    (`alaska_district_check`, from the Census Bureau's 2024 district-to-
    tract relationship file and 2020 Census tract populations);
  * Kansas City, Missouri reports apart from the four counties it spans;
    all four lie in the Kansas City metro, so its unit adds to that metro
    (asserted), and to no county;
  * Kalawao County, Hawaii has no returns of its own: Hawaii counts its
    few voters with Maui County, which lies in the same metro (asserted).

    PYTHONPATH=. .venv/bin/python -m atlas.pipeline.build.political_lean [build_dir]
        -> results/phase4d/validation.json, results/phase4d/political_lean_metro.csv
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.pipeline.adapters.census import DelineationAdapter
from atlas.pipeline.adapters.medsl_president import (NOT_VOTES, STATE_NOT_VOTES,
                                                     MedslCountyPresidentAdapter,
                                                     MedslStatePresidentAdapter)
from atlas.pipeline.fetch import DATA, RESULTS, api_get, fetch

OUT = RESULTS / "phase4d"
YEARS = ("2020", "2024")
SERVED_YEAR = "2024"
# the brief's stop condition: a state's summed county totals within 0.1% of
# the lab's own state totals, on the Democratic count, the Republican
# count and the votes cast for a candidate alike
STATE_TOLERANCE_PCT = 0.1
# the brief's stop condition: at most 5% of the ranked metros "Not available"
RANKED_NOT_AVAILABLE_MAX = 0.05
# the swing sanity check (fixed before it was first run): a metro whose
# 2020-to-2024 swing in the Democratic-minus-Republican margin differs from
# its state's by more than this many percentage points is listed
SWING_OUTLIER_PP = 5.0

# Alaska's returns are house districts (county_fips = 2000 + district;
# 2099 is the lab's DISTRICT 99, votes the state reports under no district)
ALASKA = "AK"
AK_DISTRICT_REL_URL = ("https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/"
                       "tab20_sldl202420_tract20_st02.txt")
# Kansas City, Missouri: its own returns, apart from the four counties it
# spans (Jackson, Clay, Platte, Cass); the unit's code differs by year
KANSAS_CITY = {"state_po": "MO", "county_name": "KANSAS CITY",
               "counties": ("29095", "29047", "29165", "29037"), "cbsa": "28140"}
# Kalawao County, Hawaii: counted with Maui County (same metro, 27980)
REPORTED_WITH = {"15005": "15009"}
CONNECTICUT = "09"


def _five(fips: str) -> str:
    return fips.zfill(5) if len(fips) <= 5 else fips


# ---- reporting units --------------------------------------------------------

def unit_totals(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per (year, state_po, county_fips) reporting unit: dem, rep,
    valid (every vote for a candidate), other = valid - dem - rep, the
    unit's reported totalvotes, its non-votes in the rows used, and the
    rule applied ("TOTAL", or "modes:" and the modes summed). The rows are
    the adapter's normalised rows (candidate, party, mode, votes,
    totalvotes)."""
    out = []
    for (year, st, fips), g in rows.groupby(["year", "state_po", "county_fips"], sort=True):
        cand = g[~g["candidate"].isin(NOT_VOTES)]
        non = g[g["candidate"].isin(NOT_VOTES) & (g["candidate"] != "TOTAL VOTES CAST")]
        has_total = (cand["mode"] == "TOTAL").any()
        if has_total:
            # never both: a unit with TOTAL rows is its TOTAL rows, and a
            # candidate who appears only in split modes would be lost —
            # counted, so the check can refuse it
            used, non_used = cand[cand["mode"] == "TOTAL"], non[non["mode"] == "TOTAL"]
            rule = "TOTAL"
            split_only = sorted(set(cand.loc[cand["mode"] != "TOTAL", "candidate"])
                                - set(used["candidate"]))
        else:
            used, non_used = cand, non
            rule = "modes:" + "+".join(sorted(set(cand["mode"])))
            split_only = []
        votes = used["votes"].fillna(0.0)
        dem = float(votes[used["party"] == "DEMOCRAT"].sum())
        rep = float(votes[used["party"] == "REPUBLICAN"].sum())
        valid = float(votes.sum())
        tvc = g.loc[g["candidate"] == "TOTAL VOTES CAST", "votes"]
        out.append({
            "year": year, "state_po": st, "county_fips": fips,
            "unit": _five(fips), "county_name": g["county_name"].iloc[0],
            "rule": rule, "dem": dem, "rep": rep, "valid": valid,
            "other": valid - dem - rep,
            "totalvotes": float(g["totalvotes"].iloc[0]),
            "non_votes": float(non_used["votes"].fillna(0.0).sum()),
            "total_votes_cast_row": float(tvc.iloc[0]) if len(tvc) else None,
            "na_cells_used": int(used["votes"].isna().sum()),
            "split_only_candidates": split_only,
        })
    u = pd.DataFrame(out)
    # the unit's own reconciliation: its reported total is the votes for a
    # candidate, or those plus the non-votes the state counts in it
    u["reconciles"] = ((u["totalvotes"] == u["valid"])
                       | (u["totalvotes"] == u["valid"] + u["non_votes"]))
    return u


# ---- units -> metros --------------------------------------------------------

def metro_totals(units: pd.DataFrame, delin: pd.DataFrame, site: set[str],
                 alaska: dict[str, dict] | None = None) -> pd.DataFrame:
    """Per (year, site metro): dem, rep, other, valid summed over its
    counties' units, n_counties, the units used, and `available` with the
    reason when not. `delin` is the delineation (cbsa, county5); `alaska`
    is alaska_district_check's verdict per Alaska metro (absent: not
    buildable)."""
    alaska = alaska or {}
    d = delin[delin["cbsa"].isin(site)][["cbsa", "county5"]]
    out = []
    for year in sorted(units["year"].unique()):
        u = units[units["year"] == year]
        county_units = u[u["state_po"] != ALASKA]
        by_unit = county_units.set_index("unit")
        kc = county_units[(county_units["state_po"] == KANSAS_CITY["state_po"])
                          & (county_units["county_name"] == KANSAS_CITY["county_name"])]
        for cbsa, g in d.groupby("cbsa", sort=True):
            counties = list(g["county5"])
            row = {"year": year, "cbsa": cbsa, "n_counties": len(counties),
                   "states": "+".join(sorted({c[:2] for c in counties})),
                   "units": [], "dem": np.nan, "rep": np.nan, "other": np.nan,
                   "valid": np.nan, "available": False, "reason": None}
            if any(c.startswith("02") for c in counties):
                verdict = alaska.get(cbsa)
                if verdict and verdict.get("clean"):
                    dist = u[(u["state_po"] == ALASKA) & u["unit"].isin(verdict["districts"])]
                    row.update(units=sorted(dist["unit"]), available=True,
                               **{k: float(dist[k].sum()) for k in ("dem", "rep", "other", "valid")})
                else:
                    row["reason"] = ("alaska_districts_cross_the_metro" if verdict
                                     else "alaska_reports_by_district")
                out.append(row)
                continue
            missing = [c for c in counties if c not in by_unit.index
                       and not (c in REPORTED_WITH and REPORTED_WITH[c] in counties
                                and REPORTED_WITH[c] in by_unit.index)]
            if missing:
                row["reason"] = ("connecticut_reports_by_former_county"
                                 if all(c.startswith(CONNECTICUT) for c in missing)
                                 else "county_missing_from_returns")
                row["missing_counties"] = missing
                out.append(row)
                continue
            used = [c for c in counties if c in by_unit.index]
            parts = by_unit.loc[used]
            sums = {k: float(parts[k].sum()) for k in ("dem", "rep", "other", "valid")}
            if cbsa == KANSAS_CITY["cbsa"] and len(kc):
                assert set(KANSAS_CITY["counties"]) <= set(counties), (
                    "Kansas City's four counties must all lie in its metro")
                for k in sums:
                    sums[k] += float(kc[k].sum())
                used = used + list(kc["unit"])
            row.update(units=used, available=True, **sums)
            out.append(row)
    m = pd.DataFrame(out)
    for k in ("dem", "rep", "other"):
        m[f"{k}_share"] = m[k] / m["valid"]
    return m


def kansas_city_units(units: pd.DataFrame) -> pd.DataFrame:
    return units[(units["state_po"] == KANSAS_CITY["state_po"])
                 & (units["county_name"] == KANSAS_CITY["county_name"])]


# ---- Alaska ---------------------------------------------------------------

def alaska_district_check(rel: pd.DataFrame, tract_pop: dict[str, int],
                          metros: dict[str, set[str]]) -> dict[str, dict]:
    """Whether each Alaska metro is exactly a union of whole house districts.

    rel: the Census Bureau's 2024 district-to-tract relationship rows
    (GEOID_SLDL2024_20, GEOID_TRACT_20, AREALAND_TRACT_20, AREALAND_PART);
    tract_pop: 2020 Census population per tract; metros: cbsa -> its
    boroughs (5-digit). A district touches a metro when any of its land
    lies in the metro's boroughs, and reaches outside when any of its land
    lies in a populated tract outside them; the metro is clean only if no
    district does both (and the districts touching it then cover it,
    since districts cover the state). For the record, each crossing
    district names the outside tracts it holds whole, with their
    population — people certainly voting in that district from outside
    the metro."""
    rel = rel[rel["AREALAND_PART"] > 0].copy()
    rel["county5"] = rel["GEOID_TRACT_20"].str[:5]
    out = {}
    for cbsa, boroughs in metros.items():
        inside = rel["county5"].isin(boroughs)
        touching = sorted(set(rel.loc[inside, "GEOID_SLDL2024_20"]))
        crossing = []
        for dist in touching:
            parts = rel[(rel["GEOID_SLDL2024_20"] == dist) & ~rel["county5"].isin(boroughs)]
            populated = parts[parts["GEOID_TRACT_20"].map(lambda t: tract_pop.get(t, 0)) > 0]
            if len(populated):
                whole = populated[populated["AREALAND_PART"] == populated["AREALAND_TRACT_20"]]
                crossing.append({
                    "district": dist,
                    "outside_boroughs": sorted(set(populated["county5"])),
                    "outside_tracts_held_whole": sorted(whole["GEOID_TRACT_20"]),
                    "population_2020_of_those_tracts": int(sum(
                        tract_pop[t] for t in whole["GEOID_TRACT_20"])),
                    "outside_tracts_held_in_part": sorted(
                        set(populated["GEOID_TRACT_20"]) - set(whole["GEOID_TRACT_20"]))})
        out[cbsa] = {"districts": [f"02{d[-3:]}" for d in touching],
                     "clean": not crossing, "crossing": crossing}
    return out


def alaska_inputs() -> tuple[pd.DataFrame, dict[str, int]]:
    rel = pd.read_csv(fetch(AK_DISTRICT_REL_URL), sep="|", dtype=str, encoding="utf-8-sig")
    for c in ("AREALAND_TRACT_20", "AREALAND_PART"):
        rel[c] = pd.to_numeric(rel[c])
    rows = api_get("2020/dec/dhc", {"get": "P1_001N", "for": "tract:*", "in": "state:02"})
    hdr = rows[0]
    pop = {r[hdr.index("state")] + r[hdr.index("county")] + r[hdr.index("tract")]:
           int(r[hdr.index("P1_001N")]) for r in rows[1:]}
    return rel, pop


# ---- the state totals -------------------------------------------------------

def state_check(units: pd.DataFrame, state_rows: pd.DataFrame) -> pd.DataFrame:
    """Per (year, state): the Democratic count, the Republican count and the
    votes for a candidate, summed over every reporting unit of the county
    file (districts, Kansas City and any statewide unit included), against
    the lab's state file (its non-vote rows dropped the same way)."""
    cty = units.groupby(["year", "state_po"])[["dem", "rep", "valid"]].sum()
    s = state_rows[~state_rows["candidate"].isin(STATE_NOT_VOTES)]
    st = s.groupby(["year", "state_po"]).apply(lambda g: pd.Series({
        "dem_state": float(g.loc[g["party_simplified"] == "DEMOCRAT", "votes"].sum()),
        "rep_state": float(g.loc[g["party_simplified"] == "REPUBLICAN", "votes"].sum()),
        "valid_state": float(g["votes"].sum()),
        "totalvotes_state": float(g["totalvotes"].iloc[0])}))
    j = cty.join(st, how="outer")
    for k in ("dem", "rep", "valid"):
        j[f"{k}_diff"] = j[k] - j[f"{k}_state"]
        j[f"{k}_diff_pct"] = j[f"{k}_diff"] / j[f"{k}_state"] * 100
    j["within_tolerance"] = (j[[f"{k}_diff_pct" for k in ("dem", "rep", "valid")]].abs()
                             <= STATE_TOLERANCE_PCT).all(axis=1)
    return j.reset_index()


# ---- the swing check --------------------------------------------------------

def swing_check(metros: pd.DataFrame, units: pd.DataFrame, delin: pd.DataFrame) -> dict:
    """Each metro's 2020-to-2024 swing in the Democratic-minus-Republican
    margin (percentage points of the votes for a candidate) against its
    state's, the state's taken from the same county file; a metro across
    states is held to its states' swings weighted by its 2024 votes in
    each. Listed when the two differ by more than SWING_OUTLIER_PP."""
    st = units.groupby(["year", "state_po"])[["dem", "rep", "valid"]].sum()
    margin = (st["dem"] - st["rep"]) / st["valid"] * 100
    state_swing = (margin.xs("2024") - margin.xs("2020"))
    u24 = units[(units["year"] == "2024") & (units["state_po"] != ALASKA)].set_index("unit")
    wide = metros.pivot(index="cbsa", columns="year",
                        values=["dem", "rep", "valid", "available"])
    rows = []
    for cbsa in wide.index:
        if not (wide.loc[cbsa, ("available", "2020")] and wide.loc[cbsa, ("available", "2024")]):
            continue
        m = {y: (wide.loc[cbsa, ("dem", y)] - wide.loc[cbsa, ("rep", y)])
             / wide.loc[cbsa, ("valid", y)] * 100 for y in YEARS}
        counties = delin.loc[delin["cbsa"] == cbsa, "county5"]
        w: dict[str, float] = {}
        for c in counties:
            if c in u24.index:
                po = STATE_FIPS_PO[c[:2]]
                w[po] = w.get(po, 0.0) + float(u24.loc[c, "valid"])
        if cbsa == KANSAS_CITY["cbsa"]:
            kc = kansas_city_units(units)
            w["MO"] = w.get("MO", 0.0) + float(kc.loc[kc["year"] == "2024", "valid"].sum())
        expected = sum(state_swing[po] * v for po, v in w.items()) / sum(w.values())
        sw = m["2024"] - m["2020"]
        rows.append({"cbsa": cbsa, "margin_2020_pp": round(m["2020"], 2),
                     "margin_2024_pp": round(m["2024"], 2), "swing_pp": round(sw, 2),
                     "state_swing_pp": round(expected, 2),
                     "difference_pp": round(sw - expected, 2)})
    df = pd.DataFrame(rows)
    out = df[df["difference_pp"].abs() > SWING_OUTLIER_PP].sort_values("difference_pp")
    return {"threshold_pp": SWING_OUTLIER_PP, "metros_compared": int(len(df)),
            "state_swings_pp": {k: round(float(v), 2) for k, v in state_swing.items()},
            "difference_quantiles_pp": {q: round(float(df["difference_pp"].quantile(q)), 2)
                                        for q in (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)},
            "outliers": out.to_dict("records")}


# ---- the effect of a state gap on the shown figure ---------------------------

def whole(x: float) -> str:
    return f"{x * 100:.0f}"


def gap_effect(metros: pd.DataFrame, states: pd.DataFrame, delin: pd.DataFrame,
               year: str = SERVED_YEAR) -> list[dict]:
    """For each metro in a state outside the tolerance: its three shares as
    whole percentages, and the same if every vote of the state's gap (the
    state file's count minus the county sums, per party and for the rest)
    belonged to this one metro — the most the gap could move what a metro
    shows."""
    bad = states[(states["year"] == year) & ~states["within_tolerance"]].set_index("state_po")
    if bad.empty:
        return []
    m = metros[(metros["year"] == year) & metros["available"]]
    out = []
    for _, r in m.iterrows():
        counties = delin.loc[delin["cbsa"] == r["cbsa"], "county5"]
        pos = sorted({STATE_FIPS_PO[c[:2]] for c in counties} & set(bad.index))
        if not pos:
            continue
        dem, rep, valid = r["dem"], r["rep"], r["valid"]
        gd = sum(-bad.loc[p, "dem_diff"] for p in pos)
        gr = sum(-bad.loc[p, "rep_diff"] for p in pos)
        gv = sum(-bad.loc[p, "valid_diff"] for p in pos)
        shown = [whole(dem / valid), whole(rep / valid), whole((valid - dem - rep) / valid)]
        d2, r2, v2 = dem + gd, rep + gr, valid + gv
        worst = [whole(d2 / v2), whole(r2 / v2), whole((v2 - d2 - r2) / v2)]
        out.append({"cbsa": r["cbsa"], "states_outside_tolerance": pos,
                    "shown_dem_rep_other_pct": shown,
                    "if_the_whole_gap_were_here_pct": worst,
                    "shown_figure_would_change": shown != worst})
    return out


STATE_FIPS_PO = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
    "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
    "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY"}


# ---- the run ----------------------------------------------------------------

def _num(x):
    if isinstance(x, (np.floating, float)):
        return None if np.isnan(x) else (int(x) if float(x).is_integer() else round(float(x), 6))
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def run(build_dir: Path) -> dict:
    t0 = time.time()
    ca = MedslCountyPresidentAdapter()
    craw = ca.fetch()
    crep = ca.validate(craw)
    assert crep.passed, crep.failures
    rows = ca.normalize(craw)
    sa = MedslStatePresidentAdapter()
    sraw = sa.fetch()
    srep = sa.validate(sraw)
    assert srep.passed, srep.failures
    state_rows = sa.normalize(sraw)

    delin_ad = DelineationAdapter()
    delin = delin_ad.normalize(delin_ad.fetch())
    meta = {m["cbsa"]: m for m in json.loads((Path(build_dir) / "metros.json").read_text())}
    site = set(meta)
    assert len(site) == 387, len(site)
    # Kalawao is counted with Maui: both must lie in one site metro
    for c, host in REPORTED_WITH.items():
        cb = delin.loc[delin["county5"].isin([c, host]), "cbsa"]
        assert cb.nunique() == 1, (c, host, sorted(cb))

    units = unit_totals(rows)
    ak_metros = {cbsa: set(delin.loc[delin["cbsa"] == cbsa, "county5"])
                 for cbsa in sorted(site)
                 if delin.loc[delin["cbsa"] == cbsa, "county5"].str.startswith("02").any()}
    rel, tract_pop = alaska_inputs()
    alaska = alaska_district_check(rel, tract_pop, ak_metros)
    metros = metro_totals(units, delin, site, alaska)
    states = state_check(units, state_rows)

    def year_block(y: str) -> dict:
        u = units[units["year"] == y]
        m = metros[metros["year"] == y]
        ranked = m["cbsa"].map(lambda c: meta[c]["ranked_set"])
        s = states[states["year"] == y]
        return {
            "units": int(len(u)),
            "units_by_rule": {k: int(v) for k, v in u["rule"].map(
                lambda r: "TOTAL" if r == "TOTAL" else ("no mode" if r == "modes:" else "modes summed")
            ).value_counts().items()},
            "modes_summed_units": sorted(f"{a} {b}" for a, b in u.loc[
                ~u["rule"].isin(["TOTAL", "modes:"]), ["state_po", "county_name"]].itertuples(index=False)),
            "units_not_reconciling": u.loc[~u["reconciles"], ["state_po", "county_name", "totalvotes",
                                                              "valid", "non_votes"]].to_dict("records"),
            "units_with_candidates_only_in_split_modes": u.loc[
                u["split_only_candidates"].map(len) > 0,
                ["state_po", "county_name", "split_only_candidates"]].to_dict("records"),
            "units_with_na_cells_used": u.loc[u["na_cells_used"] > 0,
                                              ["state_po", "county_name", "na_cells_used"]].to_dict("records"),
            "total_votes_cast_rows_disagreeing": int(
                (u["total_votes_cast_row"].notna() & (u["total_votes_cast_row"] != u["totalvotes"])).sum()),
            "votes_for_a_candidate": int(u["valid"].sum()),
            "coverage": {
                "all_metros": {"metros": int(len(m)), "available": int(m["available"].sum()),
                               "not_available": int((~m["available"]).sum())},
                "ranked_metros": {"metros": int(ranked.sum()),
                                  "available": int((m["available"] & ranked).sum()),
                                  "not_available": int((~m["available"] & ranked).sum())},
            },
            "not_available": [{"cbsa": r.cbsa, "metro": meta[r.cbsa]["display_name"],
                               "ranked": bool(meta[r.cbsa]["ranked_set"]), "reason": r.reason,
                               **({"missing_counties": r.missing_counties}
                                  if isinstance(getattr(r, "missing_counties", None), list) else {})}
                              for r in m[~m["available"]].itertuples()],
            "states": {
                "compared": int(len(s)),
                "within_tolerance": int(s["within_tolerance"].sum()),
                "outside_tolerance": [{k: _num(v) for k, v in r.items()} for r in s.loc[
                    ~s["within_tolerance"], ["state_po", "dem", "dem_state", "dem_diff_pct", "rep",
                                            "rep_state", "rep_diff_pct", "valid", "valid_state",
                                            "valid_diff_pct"]].to_dict("records")],
                "exact": {k: int((s[k] == s[f"{k}_state"]).sum()) for k in ("dem", "rep", "valid")},
                "max_abs_diff_pct": {k: round(float(s[f"{k}_diff_pct"].abs().max()), 4)
                                     for k in ("dem", "rep", "valid")},
            },
        }

    served = year_block(SERVED_YEAR)
    ranked_na = served["coverage"]["ranked_metros"]["not_available"]
    n_ranked = served["coverage"]["ranked_metros"]["metros"]
    stop = {
        "licence_cc0": ca.license.name.startswith("CC0 1.0"),
        "ranked_not_available_share": round(ranked_na / n_ranked, 4),
        "ranked_not_available_within_5pct": ranked_na / n_ranked <= RANKED_NOT_AVAILABLE_MAX,
        "states_outside_0_1pct_in_2024": [r["state_po"] for r in served["states"]["outside_tolerance"]],
        "state_totals_within_0_1pct": not served["states"]["outside_tolerance"],
    }
    stop["halt"] = not (stop["licence_cc0"] and stop["ranked_not_available_within_5pct"]
                        and stop["state_totals_within_0_1pct"])

    listing = []
    wide = metros.set_index(["cbsa", "year"])
    for cbsa in sorted(site):
        e = {"cbsa": cbsa, "metro": meta[cbsa]["display_name"],
             "ranked": bool(meta[cbsa]["ranked_set"])}
        for y in YEARS:
            r = wide.loc[(cbsa, y)]
            e[y] = {"n_counties": int(r["n_counties"]), "available": bool(r["available"]),
                    "votes": _num(r["valid"]),
                    **({"dem_pct": round(r["dem_share"] * 100, 2), "rep_pct": round(r["rep_share"] * 100, 2),
                        "other_pct": round(r["other_share"] * 100, 2)} if r["available"]
                       else {"reason": r["reason"]})}
        listing.append(e)

    rec = {
        "source": {"county_file": {"doi": "doi:10.7910/DVN/VOQCHQ", "version": "V20",
                                   "licence": ca.license.name, "citation": ca.license.citations[0],
                                   "checks": crep.checks},
                   "state_file": {"doi": "doi:10.7910/DVN/42MVDX", "licence": sa.license.name,
                                  "use": "check only"},
                   "alaska": {"relationship_file": AK_DISTRICT_REL_URL,
                              "tract_population": "2020 Census DHC P1_001N"}},
        "rules": {
            "modes": "TOTAL where a unit has it, otherwise the sum of its modes; never both",
            "not_votes": list(NOT_VOTES),
            "denominator": "votes cast for a candidate (every candidate and write-in)",
            "metro": "votes summed over the metro's counties (OMB 23-01), then divided once",
            "missing_county": "the metro is Not available, never an undercount",
            "kansas_city": KANSAS_CITY,
            "reported_with": REPORTED_WITH,
            "state_tolerance_pct": STATE_TOLERANCE_PCT,
            "swing_outlier_pp": SWING_OUTLIER_PP,
        },
        "stop_conditions": stop,
        "years": {y: year_block(y) for y in YEARS},
        "alaska": alaska,
        "kansas_city_units": kansas_city_units(units)[["year", "county_fips", "dem", "rep", "valid"]]
            .to_dict("records"),
        "state_gap_effect_2024": gap_effect(metros, states, delin),
        "swing_check": swing_check(metros, units, delin),
        "metros": listing,
        "state_totals": [{k: _num(v) for k, v in r.items()} for r in states.to_dict("records")],
        "build": Path(build_dir).name,
        "seconds": round(time.time() - t0, 1),
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "validation.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False,
                                                    default=_num) + "\n")
    cols = ["cbsa", "year", "n_counties", "states", "available", "reason", "dem", "rep",
            "other", "valid", "dem_share", "rep_share", "other_share"]
    metros[cols].sort_values(["year", "cbsa"]).to_csv(OUT / "political_lean_metro.csv", index=False)
    return rec


if __name__ == "__main__":
    bd = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA / "builds" / "5b780e4f2444"
    r = run(bd)
    print(json.dumps({"stop_conditions": r["stop_conditions"],
                      "coverage_2024": r["years"]["2024"]["coverage"],
                      "states_2024": {k: r["years"]["2024"]["states"][k] for k in
                                      ("compared", "within_tolerance", "exact", "max_abs_diff_pct")}},
                     indent=1, default=_num))
