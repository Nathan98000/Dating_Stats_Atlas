"""Build metro-level crime context from the FBI CDE (Phase 2d item 5) into
results/phase2d/crime_metro.csv + crime_report.json. Standalone (like
pleasant_days): the pull is long, cached and resumable; build.cube consumes
the CSV. Crime is context only and never scored (D01).

Method — see adapters/fbi_cde.py for the two traps this exists to avoid:
rates divide by the COVERED population (never the metro's), and coverage
ships beside the rates with a registry floor below which nothing renders.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from atlas.pipeline.adapters.census import DelineationAdapter
from atlas.pipeline.adapters.fbi_cde import (YEARS, FbiCdeAdapter,
                                             norm_county)
from atlas.pipeline.adapters.noaa_normals import (_haversine_km,
                                                  county_internal_points)
from atlas.pipeline.fetch import RESULTS
from atlas.pipeline.registry.loader import load_registry

P2D = RESULTS / "phase2d"

STATE_FIPS_TO_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY"}


def assign_counties(roster: pd.DataFrame, delin: pd.DataFrame) -> pd.DataFrame:
    """ORI -> county5. Name match within state first (suffix-and-space-
    insensitive); NOT SPECIFIED / Connecticut / unmatched fall back to the
    nearest county internal point within the agency's state."""
    pts = county_internal_points()
    pts["state"] = pts["GEOID"].str[:2].map(STATE_FIPS_TO_ABBR)
    name_map = {}
    for _, r in delin.iterrows():
        st = STATE_FIPS_TO_ABBR.get(r["county5"][:2])
        if st:
            name_map[(st, norm_county(r["County/County Equivalent"]))] = r["county5"]

    def by_name(row) -> str | None:
        if row["state"] == "CT":     # CDE speaks old counties; the pinned
            return None              # delineation speaks planning regions
        key = norm_county(row["primary_county"])
        if key in ("NOTSPECIFIED", ""):
            return None
        return name_map.get((row["state"], key))

    roster = roster.copy()
    roster["county5"] = roster.apply(by_name, axis=1)
    roster["assigned_by"] = np.where(roster["county5"].notna(), "name", "")

    need = roster["county5"].isna() & roster["lat"].notna() & roster["lon"].notna()
    for st, grp in roster[need].groupby("state"):
        cand = pts[pts["state"] == st]
        if cand.empty:
            continue
        for idx, row in grp.iterrows():
            d = _haversine_km(row["lat"], row["lon"],
                              cand["lat"].to_numpy(), cand["lon"].to_numpy())
            j = int(np.argmin(d))
            roster.loc[idx, "county5"] = cand.iloc[j]["GEOID"]
            roster.loc[idx, "assigned_by"] = "latlon"
    return roster


def build() -> None:
    P2D.mkdir(parents=True, exist_ok=True)
    reg = load_registry()
    crime_cfg = reg.crime
    metros = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})
    quality = pd.read_csv(RESULTS / "phase1" / "metro_quality.csv",
                          dtype={"cbsa": str})
    census_pop = dict(zip(quality["cbsa"], quality["pop_total"]))
    delin_ad = DelineationAdapter()
    delin = delin_ad.normalize(delin_ad.fetch())
    known = set(metros["cbsa"])
    county_to_cbsa = dict(zip(
        delin[delin["cbsa"].isin(known)]["county5"],
        delin[delin["cbsa"].isin(known)]["cbsa"]))

    ad = FbiCdeAdapter()
    roster = ad.roster()
    print(f"roster: {len(roster):,} agencies in {roster['state'].nunique()} states")
    roster = assign_counties(roster, delin)
    roster["cbsa"] = roster["county5"].map(county_to_cbsa)
    work = roster[roster["cbsa"].notna()].reset_index(drop=True)
    report: dict = {
        "roster_agencies": int(len(roster)),
        "metro_agencies": int(len(work)),
        "assigned_by_latlon": int((work["assigned_by"] == "latlon").sum()),
        "unassigned_no_coords": int(
            (roster["county5"].isna()).sum()),
        "years": list(range(YEARS[0], YEARS[1] + 1)),
    }
    print(json.dumps({k: report[k] for k in
                      ("roster_agencies", "metro_agencies",
                       "assigned_by_latlon")}, indent=1))

    # ---- the long pull: two cached series per agency --------------------
    def pull(ori: str) -> tuple[str, dict | None, dict | None]:
        try:
            v = ad.monthly(ori, "violent-crime")
        except Exception:
            v = None
        try:
            p = ad.monthly(ori, "property-crime")
        except Exception:
            p = None
        return ori, v, p

    results: dict[str, tuple[dict | None, dict | None]] = {}
    # 14 workers ~ 6-7 req/s sustained, under the key's 10/s burst limit;
    # _get_json backs off on 429 so a squeeze degrades rather than fails
    with ThreadPoolExecutor(max_workers=14) as ex:
        for n, (ori, v, p) in enumerate(ex.map(pull, work["ori"])):
            results[ori] = (v, p)
            if (n + 1) % 500 == 0:
                print(f"  pulled {n + 1:,}/{len(work):,} agencies")

    # ---- aggregate per metro-year ---------------------------------------
    min_pop = float(crime_cfg["implausible_min_pop"])
    bar_v = float(crime_cfg["implausible_violent_per_100k"])
    bar_p = float(crime_cfg["implausible_property_per_100k"])
    excluded_implausible = []
    rows = []
    for _, a in work.iterrows():
        v, p = results.get(a["ori"], (None, None))
        for y in range(YEARS[0], YEARS[1] + 1):
            ys = str(y)
            vm = (v or {}).get("months", {}).get(ys, [None] * 12)
            pm = (p or {}).get("months", {}).get(ys, [None] * 12)
            full = (all(x is not None for x in vm)
                    and all(x is not None for x in pm))
            pop = ((v or {}).get("pop_by_year", {}).get(ys)
                   or (p or {}).get("pop_by_year", {}).get(ys) or 0.0)
            vt = float(sum(x for x in vm if x is not None))
            pt = float(sum(x for x in pm if x is not None))
            if full and pop >= min_pop:
                if (vt / pop * 1e5 < bar_v) and (pt / pop * 1e5 < bar_p):
                    excluded_implausible.append(
                        {"ori": a["ori"], "agency": a["agency_name"],
                         "year": y, "pop": pop, "violent": vt, "property": pt})
                    full = False
            rows.append({"cbsa": a["cbsa"], "year": y, "ori": a["ori"],
                         "type": a["agency_type"], "pop": pop,
                         "full_year": full, "violent": vt, "property": pt})
    df = pd.DataFrame(rows)

    agg = []
    for (cbsa, y), g in df.groupby(["cbsa", "year"]):
        fy = g[g["full_year"]]
        fy_pop = fy[fy["pop"] > 0]
        covered = float(fy_pop["pop"].sum())
        cpop = float(census_pop.get(cbsa, np.nan))
        zero_pop_offenses = float(fy[fy["pop"] <= 0][["violent", "property"]]
                                  .to_numpy().sum())
        agg.append({
            "cbsa": cbsa, "year": y,
            "agencies": int(len(g)),
            "agencies_full_year": int(len(fy)),
            "covered_pop": covered,
            "coverage": min(1.0, covered / cpop) if cpop > 0 else np.nan,
            "violent_per_100k": (float(fy_pop["violent"].sum()) / covered * 1e5
                                 if covered > 0 else np.nan),
            "property_per_100k": (float(fy_pop["property"].sum()) / covered * 1e5
                                  if covered > 0 else np.nan),
            "agency_pop_over_census": (float(g[g["pop"] > 0]
                                             .drop_duplicates("ori")["pop"].sum())
                                       / cpop if cpop > 0 else np.nan),
            "zero_pop_offense_share": (
                zero_pop_offenses
                / max(1.0, zero_pop_offenses
                      + float(fy_pop[["violent", "property"]].to_numpy().sum()))),
        })
    out = pd.DataFrame(agg).sort_values(["cbsa", "year"])
    out.to_csv(P2D / "crime_metro.csv", index=False)

    by_year = out.groupby("year").agg(
        median_coverage=("coverage", "median"),
        p25_coverage=("coverage", lambda s: float(s.quantile(0.25))),
        metros_ge_floor=("coverage",
                         lambda s: int((s >= float(crime_cfg["coverage_floor"])).sum())),
    ).reset_index()
    report.update({
        "coverage_by_year": by_year.to_dict("records"),
        "excluded_implausible": excluded_implausible,
        "coverage_floor": float(crime_cfg["coverage_floor"]),
        "chosen_year": int(crime_cfg["year"]),
        "zero_pop_offense_share_median": float(
            out["zero_pop_offense_share"].median()),
        "agency_pop_over_census_median": float(
            out["agency_pop_over_census"].median()),
    })
    (P2D / "crime_report.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: report[k] for k in
                      ("coverage_by_year", "chosen_year",
                       "zero_pop_offense_share_median")},
                     indent=1, default=str))
    print(f"excluded as implausible partial submissions: "
          f"{len(excluded_implausible)}")
    print(f"-> {P2D / 'crime_metro.csv'}")


if __name__ == "__main__":
    build()
