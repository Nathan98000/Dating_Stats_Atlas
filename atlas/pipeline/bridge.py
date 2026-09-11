"""PUMA -> CBSA allocation bridge.

2020 tracts nest exactly inside 2020 PUMAs (Census relationship file), and
counties compose exactly into CBSAs (OMB Bulletin 23-01, July 2023
delineation). The allocation weight is

    a(p, c) = pop(tracts of p inside c's counties) / pop(all tracts of p)

with tract population from ACS 2020-2024 5-year B01003 — the same vintage as
the PUMS. The 2020-2024 5-year PUMS carries a single PUMA column coded to
2020 Census PUMA definitions (verified in PUMS_Data_Dictionary_2020-2024.csv),
so only the 2020-vintage bridge is needed.

Every county in the delineation file is mapped to its actual CBSA (metro or
micro); counties outside any CBSA map to NONMETRO. The invariant checked here
is that each PUMA's weights across all of those targets sum to exactly 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from fetch import ATLAS, DATA, RESULTS, api_get, fetch

DELINEATION_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/"
    "reference-files/2023/delineation-files/list1_2023.xlsx"
)
REL2020_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/"
    "2020_Census_Tract_to_2020_PUMA.txt"
)
DELINEATION_VINTAGE = "OMB Bulletin No. 23-01 (July 21, 2023), list1_2023.xlsx"
ACS_DATASET = "2024/acs/acs5"  # ACS 2020-2024 5-year
PURITY_THRESHOLD = 0.95

# The ten Phase 0 metros, matched by unambiguous CBSA-title prefix against
# rows typed "Metropolitan Statistical Area". Codes are resolved from the
# delineation file, never hardcoded.
TARGET_PREFIXES = {
    "new_york": "New York-",
    "washington": "Washington-",
    "san_jose": "San Jose-",
    "atlanta": "Atlanta-",
    "minneapolis": "Minneapolis-",
    "pittsburgh": "Pittsburgh,",
    "austin": "Austin-Round Rock",
    "provo": "Provo-Orem",
    "ann_arbor": "Ann Arbor,",
    "killeen": "Killeen-",
}

BRIDGE_PARQUET = DATA / "bridge.parquet"
METROS_CSV = RESULTS / "metros.csv"
COUNTIES_CSV = RESULTS / "metro_counties.csv"
BRIDGE_SUMMARY_CSV = RESULTS / "bridge_summary.csv"

STATE_FIPS_TO_POSTAL = {
    "01": "al", "02": "ak", "04": "az", "05": "ar", "06": "ca", "08": "co",
    "09": "ct", "10": "de", "11": "dc", "12": "fl", "13": "ga", "15": "hi",
    "16": "id", "17": "il", "18": "in", "19": "ia", "20": "ks", "21": "ky",
    "22": "la", "23": "me", "24": "md", "25": "ma", "26": "mi", "27": "mn",
    "28": "ms", "29": "mo", "30": "mt", "31": "ne", "32": "nv", "33": "nh",
    "34": "nj", "35": "nm", "36": "ny", "37": "nc", "38": "nd", "39": "oh",
    "40": "ok", "41": "or", "42": "pa", "44": "ri", "45": "sc", "46": "sd",
    "47": "tn", "48": "tx", "49": "ut", "50": "vt", "51": "va", "53": "wa",
    "54": "wv", "55": "wi", "56": "wy",
}


def load_delineation() -> pd.DataFrame:
    """All CBSA county rows from the 2023 OMB delineation file."""
    path = fetch(DELINEATION_URL)
    df = pd.read_excel(path, header=2, dtype=str)
    df = df[df["CBSA Code"].str.fullmatch(r"\d{5}", na=False)].copy()
    df["county5"] = df["FIPS State Code"].str.zfill(2) + df["FIPS County Code"].str.zfill(3)
    df["is_metro"] = df["Metropolitan/Micropolitan Statistical Area"].eq(
        "Metropolitan Statistical Area"
    )
    return df


def resolve_metros(delin: pd.DataFrame) -> pd.DataFrame:
    """Resolve the ten target metros to CBSA codes; one row per metro."""
    metros = delin[delin["is_metro"]][["CBSA Code", "CBSA Title"]].drop_duplicates()
    rows = []
    for slug, prefix in TARGET_PREFIXES.items():
        hits = metros[metros["CBSA Title"].str.startswith(prefix)]
        if len(hits) != 1:
            raise RuntimeError(
                f"Metro prefix {prefix!r} matched {len(hits)} metropolitan CBSAs: "
                f"{hits['CBSA Title'].tolist()}"
            )
        rows.append({"slug": slug, "cbsa": hits.iloc[0]["CBSA Code"],
                     "cbsa_title": hits.iloc[0]["CBSA Title"]})
    return pd.DataFrame(rows)


def tract_populations(state_fips: list[str]) -> pd.DataFrame:
    """ACS 2020-2024 5-year B01003 total population for every tract in the states."""
    frames = []
    for st in sorted(state_fips):
        rows = api_get(ACS_DATASET, {"get": "B01003_001E", "for": "tract:*", "in": f"state:{st}"})
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df["pop"] = pd.to_numeric(df["B01003_001E"])
        df["geoid"] = df["state"] + df["county"] + df["tract"]
        frames.append(df[["geoid", "pop"]])
        print(f"  tract pops {st}: {len(df):,} tracts, {df['pop'].sum():,} people")
    out = pd.concat(frames, ignore_index=True)
    bad = out[(out["pop"] < 0) | out["pop"].isna()]
    if len(bad):
        raise RuntimeError(f"{len(bad)} tracts with jam/negative population: {bad.head()}")
    return out


def build() -> None:
    delin = load_delineation()
    metros = resolve_metros(delin)
    target_cbsas = set(metros["cbsa"])

    # county -> CBSA for every delineated CBSA (metro and micro)
    county_to_cbsa = dict(zip(delin["county5"], delin["CBSA Code"]))
    dupes = delin["county5"].duplicated()
    if dupes.any():
        raise RuntimeError(f"County assigned to multiple CBSAs: {delin[dupes]}")

    metro_counties = delin[delin["CBSA Code"].isin(target_cbsas)].copy()
    involved_states = sorted(metro_counties["FIPS State Code"].str.zfill(2).unique())

    rel = pd.read_csv(fetch(REL2020_URL), dtype=str, encoding="utf-8-sig")
    rel.columns = [c.strip() for c in rel.columns]
    rel = rel[rel["STATEFP"].isin(involved_states)].copy()
    rel["geoid"] = rel["STATEFP"] + rel["COUNTYFP"] + rel["TRACTCE"]
    rel["county5"] = rel["STATEFP"] + rel["COUNTYFP"]

    pops = tract_populations(involved_states)

    # Tract-level reconciliation between the relationship file (2020 tracts)
    # and the ACS 2020-2024 tract universe. These must match almost exactly.
    merged = rel.merge(pops, on="geoid", how="outer", indicator=True)
    only_rel = merged[merged["_merge"] == "left_only"]
    only_acs = merged[merged["_merge"] == "right_only"]
    if len(only_rel) or len(only_acs):
        print(f"  WARNING: {len(only_rel)} tracts only in relationship file "
              f"(pop unknown), {len(only_acs)} only in ACS "
              f"(pop {only_acs['pop'].sum():,.0f}) — investigate if material")
    merged = merged[merged["_merge"] == "both"].copy()

    merged["cbsa"] = merged["county5"].map(county_to_cbsa).fillna("NONMETRO")
    grp = (merged.groupby(["STATEFP", "PUMA5CE", "cbsa"], as_index=False)["pop"].sum()
           .rename(columns={"STATEFP": "st", "PUMA5CE": "puma"}))
    totals = grp.groupby(["st", "puma"], as_index=False)["pop"].sum().rename(columns={"pop": "puma_pop"})
    bridge = grp.merge(totals, on=["st", "puma"])
    if (bridge["puma_pop"] <= 0).any():
        raise RuntimeError("PUMA with zero population — cannot form allocation weights")
    bridge["a"] = bridge["pop"] / bridge["puma_pop"]

    # THE invariant: each PUMA's weights across all CBSAs + NONMETRO sum to 1.
    sums = bridge.groupby(["st", "puma"])["a"].sum()
    off = sums[(sums - 1.0).abs() > 1e-6]
    if len(off):
        raise RuntimeError(f"PUMA allocation weights do not sum to 1:\n{off}")
    print(f"  bridge: {len(totals):,} PUMAs in {len(involved_states)} states; "
          f"all allocation weights sum to 1 within 1e-6")

    # Identity check: population allocated to each target CBSA through the
    # bridge must equal the direct county-sum of tract population.
    alloc = bridge[bridge["cbsa"].isin(target_cbsas)].copy()
    alloc["alloc_pop"] = alloc["a"] * alloc["puma_pop"]
    by_cbsa = alloc.groupby("cbsa")["alloc_pop"].sum()
    direct = (merged[merged["cbsa"].isin(target_cbsas)].groupby("cbsa")["pop"].sum())
    rel_err = ((by_cbsa - direct).abs() / direct).max()
    if rel_err > 1e-9:
        raise RuntimeError(f"Bridge does not reproduce county sums (max rel err {rel_err})")

    # Tract-population-based allocation purity per metro (share of allocated
    # population coming from PUMAs with a >= 0.95). A PUMS-weighted version is
    # recomputed at pool time; this one is stored as the bridge-side signal.
    alloc["high_a"] = alloc["a"] >= PURITY_THRESHOLD
    purity = (alloc.assign(hp=lambda d: d["alloc_pop"] * d["high_a"])
              .groupby("cbsa")
              .agg(alloc_pop=("alloc_pop", "sum"), high_pop=("hp", "sum"),
                   n_pumas=("a", "size"))
              .assign(purity=lambda d: d["high_pop"] / d["alloc_pop"]))

    metros = metros.merge(purity, left_on="cbsa", right_index=True)
    county_counts = metro_counties.groupby("CBSA Code").size()
    state_lists = (metro_counties.groupby("CBSA Code")["FIPS State Code"]
                   .apply(lambda s: "+".join(sorted(s.unique()))))
    metros["n_counties"] = metros["cbsa"].map(county_counts)
    metros["states"] = metros["cbsa"].map(state_lists)
    metros = metros.sort_values("alloc_pop", ascending=False)

    DATA.mkdir(parents=True, exist_ok=True)
    bridge[["st", "puma", "cbsa", "a", "puma_pop"]].to_parquet(BRIDGE_PARQUET, index=False)
    metros[["slug", "cbsa", "cbsa_title", "n_counties", "states", "alloc_pop",
            "n_pumas", "purity"]].to_csv(METROS_CSV, index=False)
    metro_counties[["CBSA Code", "CBSA Title", "county5", "County/County Equivalent",
                    "State Name", "Central/Outlying County"]].to_csv(COUNTIES_CSV, index=False)

    summary = metros[["cbsa", "cbsa_title", "n_counties", "n_pumas", "alloc_pop", "purity"]]
    summary.to_csv(BRIDGE_SUMMARY_CSV, index=False)
    manifest = {
        "delineation_vintage": DELINEATION_VINTAGE,
        "acs_dataset": ACS_DATASET + " (ACS 2020-2024 5-year)",
        "tract_puma_relationship": REL2020_URL,
        "puma_vintage": "2020 Census PUMAs (single PUMA column in 2020-2024 5-year PUMS)",
        "involved_state_fips": involved_states,
        "pums_states_postal": sorted(STATE_FIPS_TO_POSTAL[s] for s in involved_states),
    }
    (RESULTS / "geography_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    pd.set_option("display.width", 200)
    print(summary.to_string(index=False))
    print(f"  states for PUMS download: {manifest['pums_states_postal']}")


if __name__ == "__main__":
    build()
