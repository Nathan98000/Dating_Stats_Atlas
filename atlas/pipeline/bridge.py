"""PUMA -> CBSA allocation bridge, Phase 1: all metros, GQ-aware weights.

2020 tracts nest exactly inside 2020 PUMAs (Census relationship file), and
counties compose exactly into CBSAs (OMB Bulletin 23-01, July 2023). Three
allocation weights are built per (PUMA, target):

    a_hh(p, c)          share of PUMA p's total population in c
                        (ACS 2020-2024 5-year B01003 tract population —
                        household records use this, same as Phase 0)
    a_gq_inst(p, c)     share of p's institutional GQ population in c
    a_gq_noninst(p, c)  share of p's noninstitutional GQ population in c
                        (both from 2020 Census DHC table P5 at tract level;
                        Phase 1 correction 5 — point-mass facilities such as
                        Fort Cavazos barracks must not be smeared by
                        proportional-to-total-population allocation)

Fallback chain when a PUMA has no GQ population of a type in DHC but the PUMS
carries such records (facilities opened after April 2020): type-specific
share -> total-GQ share -> a_hh. Recorded per PUMA.

Correction 6: every relationship-file tract is reconciled against the ACS
tract universe. Unmatched tracts are reported with their 2020 DHC population
and whether their PUMA straddles allocation targets; an unmatched populated
tract inside a straddling PUMA FAILS THE BUILD.

Connecticut: the 2023 delineation is defined on planning regions (county
equivalents since 2022) and the ACS 2024 tract universe uses planning-region
GEOIDs, but the 2020 relationship file and the 2020 DHC use the old counties.
The same physical 2020 tracts exist in both universes; they are re-parented
here by joining on the 6-digit TRACTCE, with statewide-uniqueness assertions
on both sides so a collision fails loudly instead of misassigning.
"""
from __future__ import annotations

import json

import pandas as pd

from fetch import DATA, RESULTS, api_get, fetch

DELINEATION_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/"
    "reference-files/2023/delineation-files/list1_2023.xlsx"
)
REL2020_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/"
    "2020_Census_Tract_to_2020_PUMA.txt"
)
DELINEATION_VINTAGE = "OMB Bulletin No. 23-01 (July 21, 2023), list1_2023.xlsx"
ACS_DATASET = "2024/acs/acs5"   # ACS 2020-2024 5-year
DHC_DATASET = "2020/dec/dhc"    # 2020 Census Demographic and Housing Characteristics
PURITY_THRESHOLD = 0.95

P1 = RESULTS / "phase1"
BRIDGE_PARQUET = DATA / "bridge.parquet"
METROS_CSV = RESULTS / "metros.csv"

# Phase 0's ten metros, still used for persona re-runs and golden fixtures.
PHASE0_PREFIXES = {
    "new_york": "New York-", "washington": "Washington-", "san_jose": "San Jose-",
    "atlanta": "Atlanta-", "minneapolis": "Minneapolis-", "pittsburgh": "Pittsburgh,",
    "austin": "Austin-Round Rock", "provo": "Provo-Orem", "ann_arbor": "Ann Arbor,",
    "killeen": "Killeen-",
}

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
    path = fetch(DELINEATION_URL)
    df = pd.read_excel(path, header=2, dtype=str)
    df = df[df["CBSA Code"].str.fullmatch(r"\d{5}", na=False)].copy()
    df["county5"] = df["FIPS State Code"].str.zfill(2) + df["FIPS County Code"].str.zfill(3)
    df["is_metro"] = df["Metropolitan/Micropolitan Statistical Area"].eq(
        "Metropolitan Statistical Area")
    return df


def target_metros(delin: pd.DataFrame) -> pd.DataFrame:
    """All metropolitan CBSAs lying entirely within the 50 states + DC."""
    pr_cbsas = set(delin.loc[delin["FIPS State Code"] == "72", "CBSA Code"])
    metros = delin[delin["is_metro"] & ~delin["CBSA Code"].isin(pr_cbsas)]
    out = (metros.groupby(["CBSA Code", "CBSA Title"], as_index=False)
           .agg(n_counties=("county5", "size"),
                states=("FIPS State Code", lambda s: "+".join(sorted(s.unique())))))
    return out.rename(columns={"CBSA Code": "cbsa", "CBSA Title": "cbsa_title"})


def phase0_slugs(metros: pd.DataFrame) -> dict[str, str]:
    out = {}
    for slug, prefix in PHASE0_PREFIXES.items():
        hits = metros[metros["cbsa_title"].str.startswith(prefix)]
        assert len(hits) == 1, (slug, hits["cbsa_title"].tolist())
        out[slug] = hits.iloc[0]["cbsa"]
    return out


def acs_tract_pops(states: list[str], rel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """ACS 2020-2024 B01003 per tract, keyed by RELATIONSHIP-FILE geoid.

    For CT the ACS universe is on planning regions; re-parent onto the
    relationship file's old-county geoids by TRACTCE (asserted unique on
    both sides statewide).
    """
    frames, ct_info = [], {}
    for st in states:
        rows = api_get(ACS_DATASET, {"get": "B01003_001E", "for": "tract:*",
                                     "in": f"state:{st}"})
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df["pop"] = pd.to_numeric(df["B01003_001E"])
        if st == "09":
            # TRACTCE collides statewide only for offshore water tracts
            # (990000/990100). Prove they are harmless (zero population on
            # both sides), join the unique codes, and let the excluded water
            # rows surface in the reconciliation report.
            rel_ct = rel[rel["STATEFP"] == "09"][["geoid", "TRACTCE"]]
            rel_dup = rel_ct[rel_ct["TRACTCE"].duplicated(keep=False)]
            acs_dup = df[df["tract"].duplicated(keep=False)]
            assert rel_dup["TRACTCE"].str.startswith("99").all(), (
                f"CT TRACTCE collision on non-water tracts:\n{rel_dup}")
            assert (acs_dup["pop"] == 0).all(), (
                f"CT colliding ACS tracts carry population:\n{acs_dup}")
            rel_u = rel_ct[~rel_ct["TRACTCE"].duplicated(keep=False)]
            acs_u = df[~df["tract"].duplicated(keep=False)]
            m = rel_u.merge(acs_u[["tract", "pop"]], left_on="TRACTCE",
                            right_on="tract", how="inner")
            ct_info = {"rel_tracts": len(rel_ct), "acs_tracts": len(df),
                       "matched_by_tractce": len(m),
                       "water_collisions_excluded_rel": len(rel_dup),
                       "water_collisions_excluded_acs": len(acs_dup)}
            frames.append(m[["geoid", "pop"]])
            # ACS-side leftovers surface through the global reconciliation.
            leftover = acs_u[~acs_u["tract"].isin(m["tract"])]
            if len(leftover):
                extra = leftover.copy()
                extra["geoid"] = "09???" + extra["tract"]
                frames.append(extra[["geoid", "pop"]])
        else:
            df["geoid"] = df["state"] + df["county"] + df["tract"]
            frames.append(df[["geoid", "pop"]])
    out = pd.concat(frames, ignore_index=True)
    assert not (out["pop"] < 0).any(), "jam/negative tract population from ACS"
    return out, ct_info


def dhc_tract_gq(states: list[str]) -> pd.DataFrame:
    """2020 DHC per tract: total population and GQ by major type (2020 geography,
    which matches the relationship file everywhere, including old CT counties).

    GQ comes from table P18 (GROUP QUARTERS POPULATION BY SEX BY AGE BY MAJOR
    GROUP QUARTERS TYPE). The institutionalized / noninstitutionalized
    subtotals are selected from the group metadata by label — the DHC's P5 is
    a Hispanic-by-race table, so nothing here is positional guesswork.
    """
    import requests as _rq
    meta = _rq.get(f"https://api.census.gov/data/{DHC_DATASET}/groups/P18.json",
                   timeout=60).json()["variables"]
    inst_vars = sorted(v for v, d in meta.items() if v.endswith("N")
                       and "!!Institutionalized population" in d["label"]
                       and d["label"].count("!!") == 4)
    noninst_vars = sorted(v for v, d in meta.items() if v.endswith("N")
                          and "!!Noninstitutionalized population" in d["label"]
                          and d["label"].count("!!") == 4)
    assert len(inst_vars) == 6 and len(noninst_vars) == 6, (inst_vars, noninst_vars)

    get = "P1_001N,P18_001N," + ",".join(inst_vars + noninst_vars)
    frames = []
    for st in states:
        rows = api_get(DHC_DATASET, {"get": get, "for": "tract:*", "in": f"state:{st}"})
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df["geoid"] = df["state"] + df["county"] + df["tract"]
        num = df[inst_vars + noninst_vars + ["P1_001N", "P18_001N"]].apply(pd.to_numeric)
        df["pop2020"] = num["P1_001N"]
        df["gq_total"] = num["P18_001N"]
        df["gq_inst"] = num[inst_vars].sum(axis=1)
        df["gq_noninst"] = num[noninst_vars].sum(axis=1)
        frames.append(df[["geoid", "pop2020", "gq_total", "gq_inst", "gq_noninst"]])
    out = pd.concat(frames, ignore_index=True)
    bad = out[(out[["pop2020", "gq_total", "gq_inst", "gq_noninst"]] < 0).any(axis=1)]
    assert not len(bad), f"negative/jam DHC values:\n{bad.head()}"
    off = out[(out["gq_inst"] + out["gq_noninst"] - out["gq_total"]).abs() > 0]
    assert not len(off), f"DHC P18 inst+noninst != total for {len(off)} tracts"
    return out


def _shares(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Per-(st, puma, target) share of `col`, only for PUMAs where it sums > 0."""
    g = df.groupby(["st", "puma", "target"], as_index=False)[col].sum()
    tot = g.groupby(["st", "puma"])[col].transform("sum")
    g = g[tot > 0].copy()
    g["share"] = g[col] / g.groupby(["st", "puma"])[col].transform("sum")
    return g[["st", "puma", "target", "share"]]


def build() -> None:
    P1.mkdir(parents=True, exist_ok=True)
    delin = load_delineation()
    metros = target_metros(delin)
    target_cbsas = set(metros["cbsa"])
    print(f"  {len(metros)} metropolitan CBSAs in the 50 states + DC "
          f"(delineation lists {delin[delin['is_metro']]['CBSA Code'].nunique()} incl. PR)")

    county_to_cbsa = dict(zip(delin["county5"], delin["CBSA Code"]))
    assert not delin["county5"].duplicated().any()

    involved_states = sorted(
        delin[delin["CBSA Code"].isin(target_cbsas)]["FIPS State Code"].str.zfill(2).unique())
    assert len(involved_states) == 51, f"expected 51 states+DC, got {len(involved_states)}"

    rel = pd.read_csv(fetch(REL2020_URL), dtype=str, encoding="utf-8-sig")
    rel.columns = [c.strip() for c in rel.columns]
    rel = rel[rel["STATEFP"].isin(involved_states)].copy()
    rel["geoid"] = rel["STATEFP"] + rel["COUNTYFP"] + rel["TRACTCE"]
    rel["county5"] = rel["STATEFP"] + rel["COUNTYFP"]

    print("  fetching ACS tract populations (51 states)...")
    acs, ct_info = acs_tract_pops(involved_states, rel)
    print(f"  CT re-parenting: {ct_info}")
    print("  fetching 2020 DHC tract GQ populations (51 states)...")
    dhc = dhc_tract_gq(involved_states)

    # CT county-equivalents in the delineation are planning regions, which do
    # not exist in the relationship file's county field. Map CT tracts to
    # their delineation target through the ACS planning-region county instead.
    # For every other state the county5 lookup is direct.
    ct_target = None
    if "09" in involved_states:
        rows = api_get(ACS_DATASET, {"get": "B01003_001E", "for": "tract:*", "in": "state:09"})
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df["target"] = ("09" + df["county"]).map(county_to_cbsa).fillna("NONMETRO")
        ct_target = dict(zip(df["tract"], df["target"]))

    merged = rel.merge(acs, on="geoid", how="outer", indicator=True)
    rel_only = merged[merged["_merge"] == "left_only"].copy()
    acs_only = merged[merged["_merge"] == "right_only"].copy()
    both = merged[merged["_merge"] == "both"].copy()

    def target_of(row) -> str:
        if row["STATEFP"] == "09":
            return ct_target.get(row["TRACTCE"], "NONMETRO")
        return county_to_cbsa.get(row["county5"], "NONMETRO")

    both["target"] = both.apply(target_of, axis=1)
    rel_only["target"] = rel_only.apply(target_of, axis=1)

    # PUMA straddle map: number of distinct allocation targets per PUMA.
    all_rel = pd.concat([both, rel_only])
    straddle = (all_rel.groupby(["STATEFP", "PUMA5CE"])["target"].nunique()
                .rename("n_targets").reset_index())
    straddle["straddles"] = straddle["n_targets"] > 1

    # ---- Correction 6: tract reconciliation --------------------------------
    recon = rel_only.merge(dhc[["geoid", "pop2020"]], on="geoid", how="left")
    recon = recon.merge(straddle, on=["STATEFP", "PUMA5CE"], how="left")
    recon_out = recon[["geoid", "STATEFP", "PUMA5CE", "target", "pop2020",
                       "straddles"]].sort_values("pop2020", ascending=False)
    recon_out.to_csv(P1 / "tract_reconciliation.csv", index=False)
    n_bad = int(((recon["pop2020"].fillna(0) > 0) & recon["straddles"]).sum())
    print(f"  reconciliation: {len(rel_only)} relationship-file tracts missing from "
          f"ACS universe (2020 pop {recon['pop2020'].fillna(0).sum():,.0f}), "
          f"{len(acs_only)} ACS-only tracts (pop {acs_only['pop'].sum():,.0f}); "
          f"{n_bad} populated unmatched tracts inside straddling PUMAs")
    if len(acs_only) and acs_only["pop"].sum() > 0:
        print("  WARNING: populated ACS-only tracts exist — their population is "
              "excluded from PUMA totals; investigate before trusting affected PUMAs")
    assert n_bad == 0, (
        f"BUILD FAILED (correction 6): {n_bad} populated unmatched tracts sit inside "
        f"straddling PUMAs — see {P1 / 'tract_reconciliation.csv'}")

    # ---- Allocation weights ------------------------------------------------
    both = both.rename(columns={"STATEFP": "st", "PUMA5CE": "puma"})
    a_hh = _shares(both, "pop")
    sums = a_hh.groupby(["st", "puma"])["share"].sum()
    off = sums[(sums - 1.0).abs() > 1e-6]
    assert not len(off), f"a_hh does not sum to 1 for {len(off)} PUMAs:\n{off.head()}"

    gq = all_rel.merge(dhc, on="geoid", how="left").rename(
        columns={"STATEFP": "st", "PUMA5CE": "puma"})
    miss_dhc = gq["pop2020"].isna().sum()
    assert miss_dhc == 0, f"{miss_dhc} relationship-file tracts missing from DHC"
    a_inst = _shares(gq, "gq_inst")
    a_noninst = _shares(gq, "gq_noninst")
    a_gqtot = _shares(gq, "gq_total")
    for name, df in [("a_gq_inst", a_inst), ("a_gq_noninst", a_noninst),
                     ("a_gq_total", a_gqtot)]:
        s = df.groupby(["st", "puma"])["share"].sum()
        off = s[(s - 1.0).abs() > 1e-6]
        assert not len(off), f"{name} does not sum to 1 for {len(off)} PUMAs"

    # Assemble per-(PUMA, target) with the fallback chain, tracked per PUMA.
    base = a_hh.rename(columns={"share": "a_hh"})
    for df, col in [(a_inst, "s_inst"), (a_noninst, "s_noninst"), (a_gqtot, "s_gqtot")]:
        base = base.merge(df.rename(columns={"share": col}),
                          on=["st", "puma", "target"], how="outer")
    base[["a_hh", "s_inst", "s_noninst", "s_gqtot"]] = (
        base[["a_hh", "s_inst", "s_noninst", "s_gqtot"]].fillna(0.0))
    has = base.groupby(["st", "puma"])[["s_inst", "s_noninst", "s_gqtot"]].transform("sum")
    base["a_gq_inst"] = base["s_inst"].where(has["s_inst"] > 0,
                        base["s_gqtot"].where(has["s_gqtot"] > 0, base["a_hh"]))
    base["a_gq_noninst"] = base["s_noninst"].where(has["s_noninst"] > 0,
                           base["s_gqtot"].where(has["s_gqtot"] > 0, base["a_hh"]))
    fb = base.groupby(["st", "puma"]).first()
    n_fb_inst = int((has.groupby([base["st"], base["puma"]]).first()["s_inst"] == 0).sum())
    n_fb_non = int((has.groupby([base["st"], base["puma"]]).first()["s_noninst"] == 0).sum())
    print(f"  GQ fallback: {n_fb_inst} PUMAs with no 2020 institutional GQ, "
          f"{n_fb_non} with no noninstitutional GQ (of {len(fb):,})")

    for col in ["a_gq_inst", "a_gq_noninst"]:
        s = base.groupby(["st", "puma"])[col].sum()
        off = s[(s - 1.0).abs() > 1e-6]
        assert not len(off), f"{col} post-fallback does not sum to 1 for {len(off)} PUMAs"

    # ---- Purity + outputs --------------------------------------------------
    pop_by = both.groupby(["st", "puma"])["pop"].sum().rename("puma_pop")
    alloc = base[base["target"].isin(target_cbsas)].merge(
        pop_by, on=["st", "puma"])
    alloc["alloc_pop"] = alloc["a_hh"] * alloc["puma_pop"]
    pur = (alloc.assign(hp=lambda d: d["alloc_pop"] * (d["a_hh"] >= PURITY_THRESHOLD))
           .groupby("target")
           .agg(alloc_pop=("alloc_pop", "sum"), high=("hp", "sum"), n_pumas=("a_hh", "size")))
    pur["purity_tract_pop"] = pur["high"] / pur["alloc_pop"]

    metros = metros.merge(pur[["alloc_pop", "n_pumas", "purity_tract_pop"]],
                          left_on="cbsa", right_index=True, how="left")
    assert metros["alloc_pop"].notna().all(), "metro with no allocated population"
    metros = metros.sort_values("alloc_pop", ascending=False)

    keep = base[(base["target"].isin(target_cbsas))
                & (base[["a_hh", "a_gq_inst", "a_gq_noninst"]].max(axis=1) > 0)]
    out = keep.rename(columns={"target": "cbsa"})[
        ["st", "puma", "cbsa", "a_hh", "a_gq_inst", "a_gq_noninst"]]
    DATA.mkdir(parents=True, exist_ok=True)
    out.to_parquet(BRIDGE_PARQUET, index=False)
    metros.to_csv(METROS_CSV, index=False)
    straddle.to_csv(P1 / "puma_straddle.csv", index=False)

    slugs = phase0_slugs(metros)
    manifest = {
        "delineation_vintage": DELINEATION_VINTAGE,
        "n_target_metros": len(metros),
        "acs_dataset": ACS_DATASET + " (ACS 2020-2024 5-year)",
        "dhc_dataset": DHC_DATASET + " (2020 Census DHC, tract P1/P5)",
        "tract_puma_relationship": REL2020_URL,
        "puma_vintage": "2020 Census PUMAs (single PUMA column in 2020-2024 5-year PUMS)",
        "gq_allocation": "a_gq_inst/a_gq_noninst from DHC P5; household records use a_hh",
        "ct_reparenting": ct_info,
        "involved_state_fips": involved_states,
        "pums_states_postal": sorted(STATE_FIPS_TO_POSTAL[s] for s in involved_states),
        "phase0_metros": slugs,
        "reconciliation": {
            "rel_only_tracts": int(len(rel_only)),
            "rel_only_pop2020": float(recon["pop2020"].fillna(0).sum()),
            "acs_only_tracts": int(len(acs_only)),
            "acs_only_pop": float(acs_only["pop"].sum()),
            "populated_unmatched_in_straddling_pumas": n_bad,
        },
    }
    (RESULTS / "geography_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"  bridge rows {len(out):,} over {out[['st','puma']].drop_duplicates().shape[0]:,} "
          f"PUMAs; {len(metros)} metros; purity median "
          f"{metros['purity_tract_pop'].median():.3f}, "
          f"min {metros['purity_tract_pop'].min():.3f} "
          f"({metros.loc[metros['purity_tract_pop'].idxmin(), 'cbsa_title']})")


if __name__ == "__main__":
    build()
