"""Calibration at scale: PUMS-derived, GQ-aware allocated estimates vs
published ACS 2020-2024 5-year tables for all 387 metros — including the
education and income axes Phase 0 never tested (Phase 1 correction 1) — plus
the Phase 0 persona re-runs under the corrected respondent-count and
symmetric-rival definitions (corrections 2 and 4).

A failing check is a finding. Calibration queries include institutional GQ
(published universes contain it); persona pools exclude it.
"""
from __future__ import annotations

import json
import math
import re

import pandas as pd

from fetch import RESULTS, SESSION, api_get
from pool import (open_pool, pool_all_metros, pool_grouped, ratio_grouped,
                  weighted_median_by, household_income_bands, tier)

ACS = "2024/acs/acs5"
GEO = "metropolitan statistical area/micropolitan statistical area"
P1 = RESULTS / "phase1"

AGE_BANDS = [(18, 24), (25, 29), (30, 34), (35, 39), (40, 44),
             (45, 49), (50, 54), (55, 59), (60, 64), (65, 69)]

RACE_MAP = {
    "white alone": "rac1p = 1",
    "black or african american alone": "rac1p = 2",
    "american indian and alaska native alone": "rac1p IN (3,4,5)",
    "asian alone": "rac1p = 6",
    "native hawaiian and other pacific islander alone": "rac1p = 7",
    "some other race alone": "rac1p = 8",
    "two or more races": "rac1p = 9",
}

EDU_MAP_B15002 = {
    "no schooling completed": "hs_or_less", "nursery to 4th grade": "hs_or_less",
    "5th and 6th grade": "hs_or_less", "7th and 8th grade": "hs_or_less",
    "9th grade": "hs_or_less", "10th grade": "hs_or_less", "11th grade": "hs_or_less",
    "12th grade, no diploma": "hs_or_less",
    "high school graduate (includes equivalency)": "hs_or_less",
    "some college, less than 1 year": "some_college",
    "some college, 1 or more years, no degree": "some_college",
    "associate's degree": "some_college",
    "bachelor's degree": "bachelors",
    "master's degree": "graduate", "professional school degree": "graduate",
    "doctorate degree": "graduate",
}
EDU_MAP_B15001 = {
    "less than 9th grade": "hs_or_less",
    "9th to 12th grade, no diploma": "hs_or_less",
    "high school graduate (includes equivalency)": "hs_or_less",
    "some college, no degree": "some_college",
    "associate's degree": "some_college",
    "bachelor's degree": "bachelors",
    "graduate or professional degree": "graduate",
}
B15001_AGE = {"18 to 24 years": (18, 24), "25 to 34 years": (25, 34),
              "35 to 44 years": (35, 44), "45 to 64 years": (45, 64),
              "65 years and over": (65, 200)}

# Regroup buckets for earnings (B20001, individual earnings 16+ with earnings)
EARN_BUCKETS = [(-10**9, 25_000), (25_000, 50_000), (50_000, 75_000),
                (75_000, 100_000), (100_000, 10**9)]
# Regroup buckets for household income (B19001) — 150/200 are B19001 edges;
# this tests HINCP*ADJINC banding machinery, not the cube's person-income axis.
HH_EDGES = [25_000, 50_000, 75_000, 100_000, 150_000, 200_000]


def _num(x):
    if x is None or x in ("", "null"):
        return None
    v = float(x)
    return None if v <= -111111111 else v


def _moe(x):
    if x is None or x in ("", "null"):
        return None
    v = float(x)
    if v == -555555555:
        return 0.0
    return None if v <= -111111111 else v


def published(table: str, cbsas: set[str]) -> pd.DataFrame:
    rows = api_get(ACS, {"get": f"group({table})", "for": f"{GEO}:*"})
    df = pd.DataFrame(rows[1:], columns=rows[0]).set_index(rows[0][-1])
    hit = df.index.intersection(cbsas)
    assert len(hit) == len(cbsas), f"{table}: missing CBSAs {cbsas - set(df.index)}"
    return df.loc[sorted(cbsas)]


def group_labels(table: str) -> dict[str, str]:
    r = SESSION.get(f"https://api.census.gov/data/{ACS}/groups/{table}.json", timeout=60)
    r.raise_for_status()
    return {k: v["label"] for k, v in r.json()["variables"].items() if k.endswith("E")}


def _parse_age(text: str):
    text = text.strip().rstrip(":")
    if text.startswith("Under"):
        return (0, int(text.split()[1]) - 1)
    if "and over" in text:
        return (int(text.split()[0]), 200)
    parts = text.replace(" years", "").strip()
    for sep in (" to ", " and "):
        if sep in parts:
            lo, hi = parts.split(sep)
            return (int(lo), int(hi))
    return (int(parts), int(parts)) if parts.isdigit() else None


def _money_bounds(label: str):
    """Bounds of a published money band label, e.g. '$2,500 to $4,999',
    'Less than $10,000', '$200,000 or more', '$1 to $2,499 or loss'."""
    nums = [int(n.replace(",", "")) for n in re.findall(r"\$([\d,]+)", label)]
    low = label.lower()
    if low.startswith("less than"):
        return (-10**9, nums[0])
    if "or more" in low:
        return (nums[0], 10**9)
    lo, hi = nums[0], nums[1] + 1
    if "or loss" in low:
        lo = -10**9
    return (lo, hi)


def _bucket_of(bounds, buckets):
    for i, (lo, hi) in enumerate(buckets):
        if bounds[0] >= lo and bounds[1] <= hi:
            return i
    raise AssertionError(f"band {bounds} does not nest in {buckets}")


def _cmp(ours: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
    """Attach gap and the two pass columns; `ours` must carry est/moe and
    published/pub_moe."""
    df = ours.copy()
    df["gap"] = df["est"] - df["published"]
    df["pass_pub_moe"] = df["gap"].abs() <= df["pub_moe"]
    df["pass_combined_moe"] = df["gap"].abs() <= (
        (df["pub_moe"] ** 2 + df["moe"] ** 2) ** 0.5)
    return df[key_cols + ["est", "published", "gap", "pub_moe", "moe",
                          "pass_pub_moe", "pass_combined_moe"]]


def summarize(name: str, df: pd.DataFrame, tolerance_col: str = "pass_combined_moe",
              metric: str = "gap") -> dict:
    by_metro = df.groupby("cbsa")[tolerance_col].mean()
    worst = by_metro.nsmallest(10)
    return {
        "check": name, "cells": len(df),
        "pass_pub_moe": f"{int(df['pass_pub_moe'].sum())}/{len(df)}"
        if "pass_pub_moe" in df else None,
        "pass_combined_moe": f"{int(df[tolerance_col].sum())}/{len(df)}",
        "worst_10_metros": {k: round(float(v), 3) for k, v in worst.items()},
    }


# ------------------------------------------------------------- the checks ---

def check_total_pop(con, metros) -> pd.DataFrame:
    pub = published("B01003", set(metros["cbsa"]))
    ours = pool_grouped(con, ["cbsa"], include_inst=True).rename(columns={"d0": "cbsa"})
    ours = ours.merge(metros[["cbsa", "cbsa_title"]], on="cbsa")
    ours["published"] = ours["cbsa"].map(lambda c: _num(pub.loc[c, "B01003_001E"]))
    ours["gap_pct"] = (ours["est"] - ours["published"]) / ours["published"] * 100
    ours["pass"] = ours["gap_pct"].abs() <= 2.0
    return ours[["cbsa", "cbsa_title", "est", "published", "gap_pct", "n_alloc", "pass"]]


def check_sex_age(con, metros) -> pd.DataFrame:
    labels = group_labels("B01001")
    pub = published("B01001", set(metros["cbsa"]))
    cells = {}
    for var, lab in labels.items():
        parts = lab.split("!!")
        if len(parts) == 4 and parts[2].rstrip(":") in ("Male", "Female"):
            age = _parse_age(parts[3])
            if age:
                cells[var] = (parts[2].rstrip(":"), age)
    band_case = ("CASE " + " ".join(
        f"WHEN agep BETWEEN {lo} AND {hi} THEN '{lo}-{hi}'" for lo, hi in AGE_BANDS)
        + " END")
    ours = pool_grouped(con, ["cbsa", "sex", band_case],
                        "agep BETWEEN 18 AND 69", include_inst=True)
    ours.columns = ["cbsa", "sex", "band"] + list(ours.columns[3:])
    ours["sex"] = ours["sex"].map({1: "Male", 2: "Female"})
    rows = []
    for (lo, hi) in AGE_BANDS:
        for sex in ("Male", "Female"):
            comp = [v for v, (s, (alo, ahi)) in cells.items()
                    if s == sex and alo >= lo and ahi <= hi]
            width = sum(cells[v][1][1] - cells[v][1][0] + 1 for v in comp)
            assert width == hi - lo + 1, (lo, hi, sex)
            pe = pub[comp].apply(pd.to_numeric).sum(axis=1)
            pm = (pub[[v.replace("E", "M") for v in comp]]
                  .apply(pd.to_numeric).clip(lower=0) ** 2).sum(axis=1) ** 0.5
            rows.append(pd.DataFrame({"cbsa": pe.index, "sex": sex,
                                      "band": f"{lo}-{hi}", "published": pe.values,
                                      "pub_moe": pm.values}))
    pubdf = pd.concat(rows)
    df = ours.merge(pubdf, on=["cbsa", "sex", "band"], how="inner")
    assert len(df) == len(metros) * 20, len(df)
    return _cmp(df, ["cbsa", "sex", "band"])


def check_never_married(con, metros) -> pd.DataFrame:
    lab12 = group_labels("B12002")
    nm_vars = {}
    for var, lab in lab12.items():
        parts = [p.rstrip(":") for p in lab.split("!!")]
        if parts[-1] == "30 to 34 years" and "Never married" in parts:
            nm_vars["Male" if "Male" in parts else "Female"] = var
    lab01 = group_labels("B01001")
    den_vars = {}
    for var, lab in lab01.items():
        parts = lab.split("!!")
        if len(parts) == 4 and parts[2].rstrip(":") in ("Male", "Female"):
            if _parse_age(parts[3]) == (30, 34):
                den_vars[parts[2].rstrip(":")] = var
    pub12 = published("B12002", set(metros["cbsa"]))
    pub01 = published("B01001", set(metros["cbsa"]))

    ours = ratio_grouped(con, ["cbsa", "sex"], "CASE WHEN msp = 6 THEN 1.0 ELSE 0.0 END",
                         "1.0", "agep BETWEEN 30 AND 34", include_inst=True)
    ours.columns = ["cbsa", "sex"] + list(ours.columns[2:])
    ours["sex"] = ours["sex"].map({1: "Male", 2: "Female"})
    rows = []
    for _, r in ours.iterrows():
        nv, dv = nm_vars[r["sex"]], den_vars[r["sex"]]
        num = _num(pub12.loc[r["cbsa"], nv]); nm_moe = _moe(pub12.loc[r["cbsa"], nv.replace("E", "M")])
        den = _num(pub01.loc[r["cbsa"], dv]); dn_moe = _moe(pub01.loc[r["cbsa"], dv.replace("E", "M")])
        if not den:
            continue
        share_pub = num / den
        inner = (nm_moe or 0) ** 2 - share_pub ** 2 * (dn_moe or 0) ** 2
        if inner < 0:
            inner = (nm_moe or 0) ** 2 + share_pub ** 2 * (dn_moe or 0) ** 2
        pub_moe = math.sqrt(inner) / den
        gap = r["ratio"] - share_pub
        rows.append({"cbsa": r["cbsa"], "sex": r["sex"], "est": r["ratio"],
                     "published": share_pub, "gap": gap, "pub_moe": pub_moe,
                     "moe": r["moe"], "n_alloc": r["n_alloc"],
                     "pass_pub_moe": abs(gap) <= pub_moe,
                     "pass_combined_moe": abs(gap) <= math.sqrt(pub_moe ** 2 + r["moe"] ** 2)})
    return pd.DataFrame(rows)


def check_race(con, metros) -> pd.DataFrame:
    labels = group_labels("B02001")
    var_for = {}
    for var, lab in labels.items():
        tail = lab.split("!!")[-1].rstrip(":").lower()
        if tail in RACE_MAP and lab.count("!!") == 2:
            var_for[tail] = var
    assert len(var_for) == 7
    pub_race = published("B02001", set(metros["cbsa"]))
    pub_hisp = published("B03003", set(metros["cbsa"]))

    cat_case = ("CASE " + " ".join(
        f"WHEN {cond} THEN '{cat}'" for cat, cond in RACE_MAP.items()) + " END")
    ours = pool_grouped(con, ["cbsa", cat_case], include_inst=True)
    ours.columns = ["cbsa", "category"] + list(ours.columns[2:])
    ours["published"] = [
        _num(pub_race.loc[r["cbsa"], var_for[r["category"]]]) for _, r in ours.iterrows()]
    ours["pub_moe"] = [
        _moe(pub_race.loc[r["cbsa"], var_for[r["category"]].replace("E", "M")])
        for _, r in ours.iterrows()]

    hisp = pool_grouped(con, ["cbsa"], "hisp >= 2", include_inst=True).rename(
        columns={"d0": "cbsa"})
    hisp["category"] = "hispanic (any race)"
    hisp["published"] = hisp["cbsa"].map(lambda c: _num(pub_hisp.loc[c, "B03003_003E"]))
    hisp["pub_moe"] = hisp["cbsa"].map(lambda c: _moe(pub_hisp.loc[c, "B03003_003M"]))
    df = pd.concat([ours, hisp], ignore_index=True)
    return _cmp(df, ["cbsa", "category"])


def check_education_25(con, metros) -> pd.DataFrame:
    """Sex x edu4 for 25+, vs B15002 regrouped."""
    labels = group_labels("B15002")
    pub = published("B15002", set(metros["cbsa"]))
    groups: dict[tuple, list] = {}
    for var, lab in labels.items():
        parts = [p.rstrip(":") for p in lab.split("!!")]
        if len(parts) == 4 and parts[2] in ("Male", "Female"):
            tail = parts[3].lower()
            assert tail in EDU_MAP_B15002, f"unmapped B15002 level: {tail!r}"
            groups.setdefault((parts[2], EDU_MAP_B15002[tail]), []).append(var)
    assert len(groups) == 8 and sum(len(v) for v in groups.values()) == 32

    ours = pool_grouped(con, ["cbsa", "sex", "edu4"], "agep >= 25", include_inst=True)
    ours.columns = ["cbsa", "sex", "edu4"] + list(ours.columns[3:])
    ours["sex"] = ours["sex"].map({1: "Male", 2: "Female"})
    rows = []
    for (sex, edu), comp in groups.items():
        pe = pub[comp].apply(pd.to_numeric).sum(axis=1)
        pm = (pub[[v.replace("E", "M") for v in comp]]
              .apply(pd.to_numeric).clip(lower=0) ** 2).sum(axis=1) ** 0.5
        rows.append(pd.DataFrame({"cbsa": pe.index, "sex": sex, "edu4": edu,
                                  "published": pe.values, "pub_moe": pm.values}))
    df = ours.merge(pd.concat(rows), on=["cbsa", "sex", "edu4"], how="right")
    df[["est", "moe", "n_alloc"]] = df[["est", "moe", "n_alloc"]].fillna(0.0)
    assert len(df) == len(metros) * 8, len(df)
    return _cmp(df, ["cbsa", "sex", "edu4"])


def check_education_age(con, metros) -> pd.DataFrame:
    """Sex x age band x edu4 for 18+, vs B15001 regrouped (age-crossed read)."""
    labels = group_labels("B15001")
    pub = published("B15001", set(metros["cbsa"]))
    groups: dict[tuple, list] = {}
    for var, lab in labels.items():
        parts = [p.rstrip(":") for p in lab.split("!!")]
        if len(parts) == 5 and parts[2] in ("Male", "Female"):
            band = B15001_AGE.get(parts[3])
            tail = parts[4].lower()
            assert band and tail in EDU_MAP_B15001, f"unmapped B15001: {lab!r}"
            groups.setdefault((parts[2], band, EDU_MAP_B15001[tail]), []).append(var)
    assert len(groups) == 40, len(groups)

    band_case = ("CASE " + " ".join(
        f"WHEN agep BETWEEN {lo} AND {min(hi, 500)} THEN '{lo}-{hi}'"
        for lo, hi in B15001_AGE.values()) + " END")
    ours = pool_grouped(con, ["cbsa", "sex", band_case, "edu4"],
                        "agep >= 18", include_inst=True)
    ours.columns = ["cbsa", "sex", "band", "edu4"] + list(ours.columns[4:])
    ours["sex"] = ours["sex"].map({1: "Male", 2: "Female"})
    rows = []
    for (sex, band, edu), comp in groups.items():
        pe = pub[comp].apply(pd.to_numeric).sum(axis=1)
        pm = (pub[[v.replace("E", "M") for v in comp]]
              .apply(pd.to_numeric).clip(lower=0) ** 2).sum(axis=1) ** 0.5
        rows.append(pd.DataFrame({"cbsa": pe.index, "sex": sex,
                                  "band": f"{band[0]}-{band[1]}", "edu4": edu,
                                  "published": pe.values, "pub_moe": pm.values}))
    df = ours.merge(pd.concat(rows), on=["cbsa", "sex", "band", "edu4"], how="right")
    df[["est", "moe", "n_alloc"]] = df[["est", "moe", "n_alloc"]].fillna(0.0)
    assert len(df) == len(metros) * 40, len(df)
    return _cmp(df, ["cbsa", "sex", "band", "edu4"])


def check_earnings_bands(con, metros) -> pd.DataFrame:
    """Sex x earnings bucket for 16+ with earnings (PERNP*ADJINC), vs B20001."""
    labels = group_labels("B20001")
    pub = published("B20001", set(metros["cbsa"]))
    groups: dict[tuple, list] = {}
    for var, lab in labels.items():
        parts = [p.rstrip(":") for p in lab.split("!!")]
        if len(parts) == 4 and parts[2] in ("Male", "Female") and "$" in parts[3]:
            b = _bucket_of(_money_bounds(parts[3]), EARN_BUCKETS)
            groups.setdefault((parts[2], b), []).append(var)
    assert len(groups) == 10, sorted(groups)

    bucket_case = ("CASE " + " ".join(
        f"WHEN pernp_adj >= {lo} AND pernp_adj < {hi} THEN {i}"
        for i, (lo, hi) in enumerate(EARN_BUCKETS)) + " END")
    ours = pool_grouped(con, ["cbsa", "sex", bucket_case],
                        "agep >= 16 AND pernp IS NOT NULL AND pernp <> 0",
                        include_inst=True)
    ours.columns = ["cbsa", "sex", "bucket"] + list(ours.columns[3:])
    ours["sex"] = ours["sex"].map({1: "Male", 2: "Female"})
    rows = []
    for (sex, b), comp in groups.items():
        pe = pub[comp].apply(pd.to_numeric).sum(axis=1)
        pm = (pub[[v.replace("E", "M") for v in comp]]
              .apply(pd.to_numeric).clip(lower=0) ** 2).sum(axis=1) ** 0.5
        rows.append(pd.DataFrame({"cbsa": pe.index, "sex": sex, "bucket": b,
                                  "published": pe.values, "pub_moe": pm.values}))
    df = ours.merge(pd.concat(rows), on=["cbsa", "sex", "bucket"], how="right")
    df[["est", "moe", "n_alloc"]] = df[["est", "moe", "n_alloc"]].fillna(0.0)
    assert len(df) == len(metros) * 10, len(df)
    return _cmp(df, ["cbsa", "sex", "bucket"])


def check_median_earnings(con, metros) -> pd.DataFrame:
    """Median earnings by sex vs B20002 — point estimates against the
    published MOE (no replicate median; this is the independent ADJINC read)."""
    labels = group_labels("B20002")
    var_for = {}
    for var, lab in labels.items():
        tail = lab.split("!!")[-1].rstrip(":").lower()
        if tail in ("male", "female"):
            var_for[tail.capitalize()] = var
    pub = published("B20002", set(metros["cbsa"]))
    ours = weighted_median_by(con, ["cbsa", "sex"], "pernp_adj",
                              "agep >= 16 AND pernp IS NOT NULL AND pernp <> 0",
                              include_inst=True)
    ours.columns = ["cbsa", "sex", "median"]
    ours["sex"] = ours["sex"].map({1: "Male", 2: "Female"})
    ours["published"] = [_num(pub.loc[r["cbsa"], var_for[r["sex"]]])
                         for _, r in ours.iterrows()]
    ours["pub_moe"] = [_moe(pub.loc[r["cbsa"], var_for[r["sex"]].replace("E", "M")])
                       for _, r in ours.iterrows()]
    ours = ours.dropna(subset=["published"])
    ours["gap"] = ours["median"] - ours["published"]
    ours["gap_pct"] = ours["gap"] / ours["published"] * 100
    ours["pass_pub_moe"] = ours["gap"].abs() <= ours["pub_moe"]
    ours["pass_within_3pct"] = ours["gap_pct"].abs() <= 3.0
    return ours


def check_percap_income(con, metros) -> pd.DataFrame:
    """Per-capita income (PINCP*ADJINC over total population) vs B19301 —
    the one published table that reads the cube's exact income variable."""
    pub = published("B19301", set(metros["cbsa"]))
    ours = ratio_grouped(con, ["cbsa"], "coalesce(inc_adj, 0)", "1.0",
                         include_inst=True)
    ours.columns = ["cbsa"] + list(ours.columns[1:])
    ours["est"] = ours["ratio"]
    ours["published"] = ours["cbsa"].map(lambda c: _num(pub.loc[c, "B19301_001E"]))
    ours["pub_moe"] = ours["cbsa"].map(lambda c: _moe(pub.loc[c, "B19301_001M"]))
    ours = ours.dropna(subset=["published"])
    return _cmp(ours, ["cbsa"])


def check_hh_income(con, metros) -> pd.DataFrame:
    """Household income (HINCP*ADJINC, household universe from the housing
    files) vs B19001 regrouped to 7 buckets at B19001's own edges."""
    labels = group_labels("B19001")
    pub = published("B19001", set(metros["cbsa"]))
    buckets = []
    lo = -10**9
    for e in HH_EDGES:
        buckets.append((lo, e)); lo = e
    buckets.append((lo, 10**9))
    groups: dict[int, list] = {}
    for var, lab in labels.items():
        parts = [p.rstrip(":") for p in lab.split("!!")]
        if len(parts) == 3 and "$" in parts[2]:
            groups.setdefault(_bucket_of(_money_bounds(parts[2]), buckets), []).append(var)
    assert len(groups) == 7 and sum(len(v) for v in groups.values()) == 16

    ours = household_income_bands(con, [float(e) for e in HH_EDGES])
    ours["bucket"] = ours["band"].str.slice(0, 2).astype(int)
    rows = []
    for b, comp in groups.items():
        pe = pub[comp].apply(pd.to_numeric).sum(axis=1)
        pm = (pub[[v.replace("E", "M") for v in comp]]
              .apply(pd.to_numeric).clip(lower=0) ** 2).sum(axis=1) ** 0.5
        rows.append(pd.DataFrame({"cbsa": pe.index, "bucket": b,
                                  "published": pe.values, "pub_moe": pm.values}))
    df = ours.merge(pd.concat(rows), on=["cbsa", "bucket"], how="right")
    df[["est", "moe", "n_alloc"]] = df[["est", "moe", "n_alloc"]].fillna(0.0)
    assert len(df) == len(metros) * 7, len(df)
    return _cmp(df, ["cbsa", "bucket"])


def check_gq_total(con, metros) -> pd.DataFrame:
    """Total GQ vs B26001 after GQ-aware allocation; target |gap| <= 4%."""
    pub = published("B26001", set(metros["cbsa"]))
    ours = pool_grouped(con, ["cbsa"], "gq IN (1,2)", include_inst=True).rename(
        columns={"d0": "cbsa"})
    ours["published"] = ours["cbsa"].map(lambda c: _num(pub.loc[c, "B26001_001E"]))
    ours["pub_moe"] = ours["cbsa"].map(lambda c: _moe(pub.loc[c, "B26001_001M"]))
    ours["gap_pct"] = (ours["est"] - ours["published"]) / ours["published"].where(
        ours["published"] > 0) * 100
    ours["pass_4pct"] = ours["gap_pct"].abs() <= 4.0
    ours["pass_combined_moe"] = (ours["est"] - ours["published"]).abs() <= (
        (ours["pub_moe"].fillna(0) ** 2 + ours["moe"] ** 2) ** 0.5)
    ours["gq_flag"] = ~(ours["pass_4pct"] | ours["pass_combined_moe"])
    return ours[["cbsa", "est", "published", "gap_pct", "pub_moe", "moe",
                 "pass_4pct", "pass_combined_moe", "gq_flag"]]


# --------------------------------------------------- quality + ranked set ---

def metro_quality(con, metros) -> pd.DataFrame:
    q = con.execute("""
        SELECT cbsa,
            sum(pwgtp * a_eff) FILTER (WHERE a_eff >= 0.95) / sum(pwgtp * a_eff)
                AS purity_pums,
            sum(pwgtp * a_eff) AS pop_total,
            sum(pwgtp * a_eff) FILTER (WHERE gq <> 2 AND agep BETWEEN 18 AND 70)
                AS pop_pool_18_70,
            sum(a_eff) FILTER (WHERE gq <> 2 AND agep BETWEEN 18 AND 70)
                AS n_alloc_adults,
            sum(pwgtp * a_eff) FILTER (WHERE gq = 1 AND agep BETWEEN 18 AND 70)
              / sum(pwgtp * a_eff) FILTER (WHERE gq <> 2 AND agep BETWEEN 18 AND 70)
                AS noninst_gq_share_18_70,
            sum(pwgtp * a_eff) FILTER (WHERE gq = 2) / sum(pwgtp * a_eff)
                AS inst_gq_share
        FROM contrib GROUP BY cbsa
    """).df()
    out = metros[["cbsa", "cbsa_title", "purity_tract_pop"]].merge(q, on="cbsa")
    out["ranked_set"] = (out["pop_total"] >= 250_000) & (out["n_alloc_adults"] >= 5_000)
    return out


# ----------------------------------------------------- persona re-runs ------

BA_PLUS = "edu4 IN ('bachelors','graduate')"
NOT_MARRIED = "msp IN (3,4,5,6)"

# persona: (pool_where, seeker_sex, seeker_age, rival_edu_floor)
PERSONAS = {
    "A": (f"sex = 1 AND agep BETWEEN 30 AND 40 AND {BA_PLUS} AND inc_adj >= 75000 "
          f"AND {NOT_MARRIED}", 2, 32, BA_PLUS, NOT_MARRIED),
    "B": ("sex = 2 AND agep BETWEEN 25 AND 33 AND msp = 6", 1, 28, "TRUE", "msp = 6"),
    "C": (f"sex = 1 AND agep BETWEEN 35 AND 48 AND {BA_PLUS} AND inc_adj >= 100000 "
          f"AND {NOT_MARRIED}", 2, 38, BA_PLUS, NOT_MARRIED),
    "D": (f"sex = 2 AND agep BETWEEN 32 AND 45 AND inc_adj >= 50000 "
          f"AND {NOT_MARRIED}", 1, 41, "TRUE", NOT_MARRIED),
    "E": (f"sex = 1 AND agep BETWEEN 28 AND 38 AND {BA_PLUS} AND inc_adj >= 75000 "
          f"AND race8 = 'nh_black' AND {NOT_MARRIED}", 2, 29, BA_PLUS, NOT_MARRIED),
}


def rival_wheres(persona: str) -> tuple[str, str]:
    """(symmetric, crude) rival filters. Symmetric = same marital screen as
    the pool (correction 4); no income floor on rivals (rivals compete for the
    pool regardless of their own income — documented decision) and no race
    screen (the crude kernel stays race-blind; the empirical pairing kernel is
    Phase 3)."""
    _, sex, age, edu_floor, marital = PERSONAS[persona]
    base = f"sex = {sex} AND agep BETWEEN {age - 5} AND {age + 5} AND {edu_floor}"
    return f"{base} AND {marital}", base


def personas_rerun(con, phase0_cbsas: dict[str, str], quality: pd.DataFrame) -> pd.DataFrame:
    """Phase 0's 5 personas x 10 metros under Phase 1 definitions, with the
    crude-rival and raw-n variants alongside for corrections 2 and 4."""
    cbsas = set(phase0_cbsas.values())
    qual = quality.set_index("cbsa")
    rows = []
    for p, (pool_where, *_rest) in PERSONAS.items():
        sym_where, crude_where = rival_wheres(p)
        P = pool_all_metros(con, pool_where)
        Rs = pool_all_metros(con, sym_where)
        Rc = pool_all_metros(con, crude_where)
        for cb in sorted(cbsas):
            pe = P.loc[cb] if cb in P.index else None
            rs = Rs.loc[cb] if cb in Rs.index else None
            rc = Rc.loc[cb] if cb in Rc.index else None
            est = float(pe["est"]) if pe is not None else 0.0
            cv = pe["cv_pct"] if pe is not None else None
            n_raw = int(pe["n_raw"]) if pe is not None else 0
            n_alloc = float(pe["n_alloc"]) if pe is not None else 0.0
            n_kish = float(pe["n_kish"]) if pe is not None else 0.0
            n_gate = min(n_alloc, n_kish)
            rows.append({
                "cbsa": cb, "metro_name": qual.loc[cb, "cbsa_title"], "persona": p,
                "pool": round(est), "pool_moe": round(float(pe["moe"])) if pe is not None else 0,
                "cv": round(cv, 1) if cv is not None else None,
                "n_raw": n_raw, "n_alloc": round(n_alloc, 1),
                "n_kish": round(n_kish, 1), "n_gate": round(n_gate, 1),
                "rivals_sym": round(float(rs["est"])) if rs is not None else 0,
                "ratio_sym": round(est / float(rs["est"]), 3)
                if rs is not None and rs["est"] > 0 else None,
                "rivals_crude": round(float(rc["est"])) if rc is not None else 0,
                "ratio_crude": round(est / float(rc["est"]), 3)
                if rc is not None and rc["est"] > 0 else None,
                "tier_gate": tier(n_gate, cv),
                "tier_raw_n": tier(n_raw, cv),
                "allocation_purity": round(float(qual.loc[cb, "purity_pums"]), 4),
                "gq_share": round(float(qual.loc[cb, "noninst_gq_share_18_70"]), 4),
            })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------- main ---

def main() -> None:
    P1.mkdir(parents=True, exist_ok=True)
    con = open_pool()
    metros = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})
    geo = json.loads((RESULTS / "geography_manifest.json").read_text())

    quality = metro_quality(con, metros)
    quality.to_csv(P1 / "metro_quality.csv", index=False)
    print(f"ranked set: {int(quality['ranked_set'].sum())}/{len(quality)} metros "
          f"(pop>=250k and n_alloc_adults>=5000)")

    summaries = []
    t = check_total_pop(con, metros)
    t.to_csv(P1 / "calibration_total_pop.csv", index=False)
    s = {"check": "total_pop_B01003", "cells": len(t),
         "pass": f"{int(t['pass'].sum())}/{len(t)}",
         "worst_10_metros": t.reindex(t["gap_pct"].abs().sort_values(ascending=False).index)
         .head(10).set_index("cbsa")["gap_pct"].round(2).to_dict()}
    summaries.append(s); print(s["check"], s["pass"])

    have_h = "hcontrib" in {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    checks_to_run = [("sex_age_B01001", check_sex_age),
                     ("never_married_B12002", check_never_married),
                     ("race_B02001_B03003", check_race),
                     ("education_25_B15002", check_education_25),
                     ("education_age_B15001", check_education_age),
                     ("earnings_B20001", check_earnings_bands),
                     ("percap_income_B19301", check_percap_income)]
    if have_h:
        checks_to_run.append(("hh_income_B19001", check_hh_income))
    else:
        print("hh_income_B19001 deferred (housing extract incomplete); "
              "run `checks.py hh` after it finishes")
    for name, fn in checks_to_run:
        df = fn(con, metros)
        df.to_csv(P1 / f"calibration_{name}.csv", index=False)
        s = summarize(name, df)
        summaries.append(s)
        print(s["check"], "pub:", s["pass_pub_moe"], "combined:", s["pass_combined_moe"])

    me = check_median_earnings(con, metros)
    me.to_csv(P1 / "calibration_median_earnings_B20002.csv", index=False)
    s = {"check": "median_earnings_B20002", "cells": len(me),
         "pass_pub_moe": f"{int(me['pass_pub_moe'].sum())}/{len(me)}",
         "pass_within_3pct": f"{int(me['pass_within_3pct'].sum())}/{len(me)}",
         "median_abs_gap_pct": round(float(me["gap_pct"].abs().median()), 2)}
    summaries.append(s); print(s["check"], s)

    gq = check_gq_total(con, metros)
    gq.to_csv(P1 / "calibration_gq_total_B26001.csv", index=False)
    s = {"check": "gq_total_B26001", "cells": len(gq),
         "pass_4pct": f"{int(gq['pass_4pct'].sum())}/{len(gq)}",
         "pass_4pct_or_combined_moe": f"{int((gq['pass_4pct'] | gq['pass_combined_moe']).sum())}/{len(gq)}",
         "flagged": gq[gq["gq_flag"]]["cbsa"].tolist()}
    summaries.append(s); print(s["check"], s["pass_4pct"], "flags:", len(s["flagged"]))

    # carry GQ flags into quality
    quality = quality.merge(gq[["cbsa", "gap_pct", "gq_flag"]]
                            .rename(columns={"gap_pct": "gq_b26001_gap_pct"}), on="cbsa")
    quality.to_csv(P1 / "metro_quality.csv", index=False)

    pers = personas_rerun(con, geo["phase0_metros"], quality)
    pers.to_csv(P1 / "personas_rerun.csv", index=False)
    flips_n = pers[pers["tier_gate"] != pers["tier_raw_n"]]
    print(f"personas: {len(pers)} cells; tier flips from n-definition "
          f"(raw -> gate): {len(flips_n)}")

    (P1 / "calibration_summary.json").write_text(
        json.dumps({"summaries": summaries}, indent=2, default=str) + "\n")


def hh_only() -> None:
    """Run just the deferred B19001 household-income check and append its
    summary to calibration_summary.json."""
    con = open_pool()
    metros = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})
    df = check_hh_income(con, metros)
    df.to_csv(P1 / "calibration_hh_income_B19001.csv", index=False)
    s = summarize("hh_income_B19001", df)
    blob = json.loads((P1 / "calibration_summary.json").read_text())
    blob["summaries"] = [x for x in blob["summaries"]
                         if x.get("check") != "hh_income_B19001"] + [s]
    (P1 / "calibration_summary.json").write_text(
        json.dumps(blob, indent=2, default=str) + "\n")
    print(s["check"], "pub:", s["pass_pub_moe"], "combined:", s["pass_combined_moe"])


if __name__ == "__main__":
    import sys as _sys
    if _sys.argv[1:] == ["hh"]:
        hh_only()
    else:
        main()
