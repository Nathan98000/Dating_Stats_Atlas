"""Calibration of the PUMS-derived, PUMA-allocated estimates against published
ACS 2020-2024 5-year tables for the same CBSAs — plus the persona pools.

A failing check is a finding, not something to tune away. Published-table
universes include institutional group quarters, so calibration queries run
with include_inst=True; persona pools exclude institutional GQ.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from fetch import RESULTS, SESSION, api_get
from pool import QUERY_LOG, open_pool, pool, pool_by, share, tier

ACS = "2024/acs/acs5"
GEO = "metropolitan statistical area/micropolitan statistical area"

AGE_BANDS = [(18, 24), (25, 29), (30, 34), (35, 39), (40, 44),
             (45, 49), (50, 54), (55, 59), (60, 64), (65, 69)]

RACE_MAP = {  # B02001 label fragment -> our RAC1P grouping (all ethnicities)
    "White alone": "rac1p = 1",
    "Black or African American alone": "rac1p = 2",
    "American Indian and Alaska Native alone": "rac1p IN (3,4,5)",
    "Asian alone": "rac1p = 6",
    "Native Hawaiian and Other Pacific Islander alone": "rac1p = 7",
    "Some other race alone": "rac1p = 8",
    "Two or more races": "rac1p = 9",
}

PERSONAS = {
    # persona: (pool where-clause, rival where-clause, description)
    "A": ("sex = 1 AND agep BETWEEN 30 AND 40 AND edu4 = 'ba_plus' "
          "AND inc_adj >= 75000 AND msp IN (3,4,5,6)",
          "sex = 2 AND agep BETWEEN 27 AND 37 AND edu4 = 'ba_plus'",
          "Woman 32 BA+ seeking men 30-40 BA+ $75k+ not married"),
    "B": ("sex = 2 AND agep BETWEEN 25 AND 33 AND msp = 6",
          "sex = 1 AND agep BETWEEN 23 AND 33",
          "Man 28 some-college seeking women 25-33 never married"),
    "C": ("sex = 1 AND agep BETWEEN 35 AND 48 AND edu4 = 'ba_plus' "
          "AND inc_adj >= 100000 AND msp IN (3,4,5,6)",
          "sex = 2 AND agep BETWEEN 33 AND 43 AND edu4 = 'ba_plus'",
          "Woman 38 grad seeking men 35-48 BA+ $100k+ not married"),
    "D": ("sex = 2 AND agep BETWEEN 32 AND 45 AND inc_adj >= 50000 "
          "AND msp IN (3,4,5,6)",
          "sex = 1 AND agep BETWEEN 36 AND 46",
          "Man 41 BA seeking women 32-45 $50k+ not married"),
    "E": ("sex = 1 AND agep BETWEEN 28 AND 38 AND edu4 = 'ba_plus' "
          "AND inc_adj >= 75000 AND race8 = 'nh_black' AND msp IN (3,4,5,6)",
          "sex = 2 AND agep BETWEEN 24 AND 34 AND edu4 = 'ba_plus'",
          "Woman 29 BA+ Black NH seeking men 28-38 BA+ $75k+ Black NH not married"),
}


def _num(x) -> float | None:
    if x is None or x == "" or x == "null":
        return None
    v = float(x)
    return None if v <= -111111111 else v


def _moe(x) -> float | None:
    if x is None or x == "" or x == "null":
        return None
    v = float(x)
    if v == -555555555:  # controlled estimate: no sampling error
        return 0.0
    return None if v <= -111111111 else v


def published(table: str, cbsas: list[str]) -> pd.DataFrame:
    rows = api_get(ACS, {"get": f"group({table})", "for": f"{GEO}:{','.join(cbsas)}"})
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df.set_index(rows[0][-1])


def group_labels(table: str) -> dict[str, str]:
    r = SESSION.get(f"https://api.census.gov/data/{ACS}/groups/{table}.json", timeout=60)
    r.raise_for_status()
    return {k: v["label"] for k, v in r.json()["variables"].items() if k.endswith("E")}


def _parse_age(text: str) -> tuple[int, int] | None:
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


# ---------------------------------------------------------------- checks ----

def check_total_pop(con, metros: pd.DataFrame) -> pd.DataFrame:
    pub = published("B01003", metros["cbsa"].tolist())
    rows = []
    for _, m in metros.iterrows():
        ours = pool(con, m["cbsa"], "TRUE", include_inst=True)
        pub_est = _num(pub.loc[m["cbsa"], "B01003_001E"])
        gap_pct = (ours["est"] - pub_est) / pub_est * 100
        rows.append({"cbsa": m["cbsa"], "metro": m["cbsa_title"],
                     "pums_est": round(ours["est"]), "published": pub_est,
                     "gap_pct": round(gap_pct, 3), "tolerance_pct": 2.0,
                     "pass": abs(gap_pct) <= 2.0})
    return pd.DataFrame(rows)


def check_sex_age(con, metros: pd.DataFrame) -> pd.DataFrame:
    labels = group_labels("B01001")
    pub = published("B01001", metros["cbsa"].tolist())
    # published var -> (sex, age range)
    cells = {}
    for var, lab in labels.items():
        parts = lab.split("!!")
        if len(parts) == 4 and parts[2].rstrip(":") in ("Male", "Female"):
            age = _parse_age(parts[3])
            if age:
                cells[var] = (parts[2].rstrip(":"), age)
    rows = []
    for _, m in metros.iterrows():
        for sex_name, sex_code in [("Male", 1), ("Female", 2)]:
            ours = pool_by(
                con, m["cbsa"],
                "CASE " + " ".join(
                    f"WHEN agep BETWEEN {lo} AND {hi} THEN '{lo}-{hi}'"
                    for lo, hi in AGE_BANDS) + " END",
                f"sex = {sex_code} AND agep BETWEEN 18 AND 69",
                include_inst=True).set_index("grp")
            for lo, hi in AGE_BANDS:
                comp = [v for v, (s, (alo, ahi)) in cells.items()
                        if s == sex_name and alo >= lo and ahi <= hi]
                inside = sum(ahi - alo + 1 for v in comp
                             for s, (alo, ahi) in [cells[v]])
                assert inside == hi - lo + 1, f"band {lo}-{hi} {sex_name}: bad coverage"
                pub_est = sum(_num(pub.loc[m["cbsa"], v]) for v in comp)
                pub_moe = math.sqrt(sum(
                    (_moe(pub.loc[m["cbsa"], v.replace("E", "M")]) or 0.0) ** 2
                    for v in comp))
                o = ours.loc[f"{lo}-{hi}"]
                gap = o["est"] - pub_est
                rows.append({
                    "cbsa": m["cbsa"], "metro": m["cbsa_title"], "sex": sex_name,
                    "band": f"{lo}-{hi}", "pums_est": round(o["est"]),
                    "published": pub_est, "gap": round(gap),
                    "pub_moe": round(pub_moe), "pums_moe": round(o["moe"]),
                    "pass_pub_moe": abs(gap) <= pub_moe,
                    "pass_combined_moe": abs(gap) <= math.sqrt(pub_moe ** 2 + o["moe"] ** 2),
                })
    return pd.DataFrame(rows)


def check_never_married(con, metros: pd.DataFrame) -> pd.DataFrame:
    lab12 = group_labels("B12002")
    nm_vars = {}
    for var, lab in lab12.items():
        parts = [p.rstrip(":") for p in lab.split("!!")]
        if parts[-1] == "30 to 34 years" and "Never married" in parts:
            sex = "Male" if "Male" in parts else "Female"
            nm_vars[sex] = var
    assert set(nm_vars) == {"Male", "Female"}, nm_vars

    lab01 = group_labels("B01001")
    den_vars = {"Male": [], "Female": []}
    for var, lab in lab01.items():
        parts = lab.split("!!")
        if len(parts) == 4 and parts[2].rstrip(":") in ("Male", "Female"):
            age = _parse_age(parts[3])
            if age == (30, 34):
                den_vars[parts[2].rstrip(":")].append(var)
    assert all(len(v) == 1 for v in den_vars.values())

    pub12 = published("B12002", metros["cbsa"].tolist())
    pub01 = published("B01001", metros["cbsa"].tolist())
    rows = []
    for _, m in metros.iterrows():
        for sex_name, sex_code in [("Male", 1), ("Female", 2)]:
            nv, dv = nm_vars[sex_name], den_vars[sex_name][0]
            num, num_moe = _num(pub12.loc[m["cbsa"], nv]), _moe(pub12.loc[m["cbsa"], nv.replace("E", "M")])
            den, den_moe = _num(pub01.loc[m["cbsa"], dv]), _moe(pub01.loc[m["cbsa"], dv.replace("E", "M")])
            r = num / den
            inner = (num_moe or 0) ** 2 - r ** 2 * (den_moe or 0) ** 2
            if inner < 0:
                inner = (num_moe or 0) ** 2 + r ** 2 * (den_moe or 0) ** 2
            pub_share_moe = math.sqrt(inner) / den
            ours = share(con, m["cbsa"],
                         f"sex = {sex_code} AND agep BETWEEN 30 AND 34 AND msp = 6",
                         f"sex = {sex_code} AND agep BETWEEN 30 AND 34",
                         include_inst=True)
            gap = ours["share"] - r
            rows.append({
                "cbsa": m["cbsa"], "metro": m["cbsa_title"], "sex": sex_name,
                "pums_share": round(ours["share"], 4), "published_share": round(r, 4),
                "gap": round(gap, 4), "pub_share_moe": round(pub_share_moe, 4),
                "pums_share_moe": round(ours["moe"], 4),
                "pass_pub_moe": abs(gap) <= pub_share_moe,
                "pass_combined_moe": abs(gap) <= math.sqrt(pub_share_moe ** 2 + ours["moe"] ** 2),
            })
    return pd.DataFrame(rows)


def check_race(con, metros: pd.DataFrame) -> pd.DataFrame:
    labels = group_labels("B02001")
    var_for = {}
    for var, lab in labels.items():
        tail = lab.split("!!")[-1].rstrip(":")
        if tail in RACE_MAP and lab.count("!!") == 2:  # top-level categories only
            var_for[tail] = var
    assert len(var_for) == 7, var_for
    pub_race = published("B02001", metros["cbsa"].tolist())
    pub_hisp = published("B03003", metros["cbsa"].tolist())

    rows = []
    for _, m in metros.iterrows():
        for cat, var in var_for.items():
            ours = pool(con, m["cbsa"], RACE_MAP[cat], include_inst=True, log=False)
            pub_est = _num(pub_race.loc[m["cbsa"], var])
            pub_moe = _moe(pub_race.loc[m["cbsa"], var.replace("E", "M")])
            gap = ours["est"] - pub_est
            rows.append({"cbsa": m["cbsa"], "metro": m["cbsa_title"], "category": cat,
                         "pums_est": round(ours["est"]), "published": pub_est,
                         "gap": round(gap), "pub_moe": pub_moe, "pums_moe": round(ours["moe"]),
                         "pass_pub_moe": abs(gap) <= pub_moe,
                         "pass_combined_moe": abs(gap) <= math.sqrt(pub_moe ** 2 + ours["moe"] ** 2)})
        ours = pool(con, m["cbsa"], "hisp >= 2", include_inst=True, log=False)
        pub_est = _num(pub_hisp.loc[m["cbsa"], "B03003_003E"])
        pub_moe = _moe(pub_hisp.loc[m["cbsa"], "B03003_003M"])
        gap = ours["est"] - pub_est
        rows.append({"cbsa": m["cbsa"], "metro": m["cbsa_title"], "category": "Hispanic (any race)",
                     "pums_est": round(ours["est"]), "published": pub_est,
                     "gap": round(gap), "pub_moe": pub_moe, "pums_moe": round(ours["moe"]),
                     "pass_pub_moe": abs(gap) <= pub_moe,
                     "pass_combined_moe": abs(gap) <= math.sqrt(pub_moe ** 2 + ours["moe"] ** 2)})
    return pd.DataFrame(rows)


def check_rent(metros: pd.DataFrame) -> pd.DataFrame:
    """Published median gross rent only — a sanity check that the resolved CBSA
    codes are the metros we think they are (PUMS person files carry no rent)."""
    pub = published("B25064", metros["cbsa"].tolist())
    rows = []
    for _, m in metros.iterrows():
        rows.append({"cbsa": m["cbsa"], "metro": m["cbsa_title"],
                     "median_gross_rent": _num(pub.loc[m["cbsa"], "B25064_001E"]),
                     "moe": _moe(pub.loc[m["cbsa"], "B25064_001M"])})
    return pd.DataFrame(rows)


# ------------------------------------------------------- quality metrics ----

def metro_quality(con, metros: pd.DataFrame) -> pd.DataFrame:
    """PUMS-weighted allocation purity + group-quarters shares per metro."""
    q = con.execute("""
        SELECT cbsa,
            sum(pwgtp * a) FILTER (WHERE a >= 0.95) / sum(pwgtp * a) AS purity_pums,
            sum(pwgtp * a) FILTER (WHERE gq = 2) / sum(pwgtp * a) AS inst_gq_share_all_ages,
            sum(pwgtp * a) FILTER (WHERE gq = 1 AND agep BETWEEN 18 AND 70)
              / sum(pwgtp * a) FILTER (WHERE gq <> 2 AND agep BETWEEN 18 AND 70)
              AS noninst_gq_share_18_70
        FROM contrib GROUP BY cbsa
    """).df()
    out = metros[["cbsa", "cbsa_title", "purity"]].rename(
        columns={"purity": "purity_tract_pop"}).merge(q, on="cbsa")
    return out.sort_values("purity_pums")


def check_gq(quality: pd.DataFrame) -> dict:
    g = quality.set_index("cbsa_title")["noninst_gq_share_18_70"]
    ann = g[[i for i in g.index if i.startswith("Ann Arbor")][0]]
    kil = g[[i for i in g.index if i.startswith("Killeen")][0]]
    pit = g[[i for i in g.index if i.startswith("Pittsburgh")][0]]
    return {"ann_arbor": round(float(ann), 4), "killeen": round(float(kil), 4),
            "pittsburgh": round(float(pit), 4),
            "pass": bool(ann > 2 * pit and kil > 2 * pit)}


def check_moe_scaling() -> dict:
    """Across logged pool queries, CV should scale roughly as n^-0.5."""
    pts = [(q["n"], q["cv_pct"]) for q in QUERY_LOG
           if q["cv_pct"] and q["n"] >= 10]
    x = np.log([p[0] for p in pts])
    y = np.log([p[1] for p in pts])
    slope, intercept = np.polyfit(x, y, 1)
    r2 = float(np.corrcoef(x, y)[0, 1] ** 2)
    return {"n_queries": len(pts), "slope": round(float(slope), 3),
            "r2": round(r2, 3), "expected": -0.5,
            "pass": bool(-0.65 <= slope <= -0.35)}


# --------------------------------------------------------------- personas ---

def personas(con, metros: pd.DataFrame, quality: pd.DataFrame) -> pd.DataFrame:
    qual = quality.set_index("cbsa")
    rows = []
    for p, (pool_where, rival_where, desc) in PERSONAS.items():
        for _, m in metros.iterrows():
            P = pool(con, m["cbsa"], pool_where)          # excludes institutional GQ
            R = pool(con, m["cbsa"], rival_where)
            rows.append({
                "cbsa": m["cbsa"], "metro_name": m["cbsa_title"], "persona": p,
                "pool": round(P["est"]), "pool_moe": round(P["moe"]),
                "cv": round(P["cv_pct"], 1) if P["cv_pct"] is not None else None,
                "n_unweighted": P["n"],
                "rivals": round(R["est"]),
                "ratio": round(P["est"] / R["est"], 3) if R["est"] > 0 else None,
                "tier": tier(P["n"], P["cv_pct"]),
                "allocation_purity": round(float(qual.loc[m["cbsa"], "purity_pums"]), 4),
                "gq_share": round(float(qual.loc[m["cbsa"], "noninst_gq_share_18_70"]), 4),
            })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------- main ---

def main() -> None:
    con = open_pool()
    metros = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})

    quality = metro_quality(con, metros)
    quality.to_csv(RESULTS / "metro_quality.csv", index=False)

    t = check_total_pop(con, metros)
    t.to_csv(RESULTS / "calibration_total_pop.csv", index=False)
    print(f"\n== Total population vs B01003 (tolerance 2%): "
          f"{t['pass'].sum()}/{len(t)} pass, worst gap {t['gap_pct'].abs().max():.2f}%")
    print(t.to_string(index=False))

    sa = check_sex_age(con, metros)
    sa.to_csv(RESULTS / "calibration_sex_age.csv", index=False)
    print(f"\n== Sex x age vs B01001: {sa['pass_pub_moe'].sum()}/{len(sa)} within published MOE, "
          f"{sa['pass_combined_moe'].sum()}/{len(sa)} within combined MOE")

    nm = check_never_married(con, metros)
    nm.to_csv(RESULTS / "calibration_never_married.csv", index=False)
    print(f"\n== Never-married share 30-34 vs B12002/B01001: "
          f"{nm['pass_pub_moe'].sum()}/{len(nm)} within published MOE, "
          f"{nm['pass_combined_moe'].sum()}/{len(nm)} within combined MOE")
    print(nm.to_string(index=False))

    rc = check_race(con, metros)
    rc.to_csv(RESULTS / "calibration_race.csv", index=False)
    print(f"\n== Race/ethnicity vs B02001+B03003: {rc['pass_pub_moe'].sum()}/{len(rc)} "
          f"within published MOE, {rc['pass_combined_moe'].sum()}/{len(rc)} within combined MOE")

    rent = check_rent(metros)
    rent.to_csv(RESULTS / "calibration_rent.csv", index=False)
    print("\n== Median gross rent (published B25064, eyeball only)")
    print(rent.to_string(index=False))

    pers = personas(con, metros, quality)
    pers.to_csv(RESULTS / "phase0_pools.csv", index=False)
    print(f"\n== Personas: tiers {pers['tier'].value_counts().to_dict()}")

    gq = check_gq(quality)
    scaling = check_moe_scaling()
    (RESULTS / "check_summary.json").write_text(json.dumps({
        "total_pop_pass": f"{int(t['pass'].sum())}/{len(t)}",
        "sex_age_within_pub_moe": f"{int(sa['pass_pub_moe'].sum())}/{len(sa)}",
        "sex_age_within_combined_moe": f"{int(sa['pass_combined_moe'].sum())}/{len(sa)}",
        "never_married_within_pub_moe": f"{int(nm['pass_pub_moe'].sum())}/{len(nm)}",
        "never_married_within_combined_moe": f"{int(nm['pass_combined_moe'].sum())}/{len(nm)}",
        "race_within_pub_moe": f"{int(rc['pass_pub_moe'].sum())}/{len(rc)}",
        "race_within_combined_moe": f"{int(rc['pass_combined_moe'].sum())}/{len(rc)}",
        "gq_contrast": gq, "moe_scaling": scaling,
        "persona_tiers": pers["tier"].value_counts().to_dict(),
    }, indent=2) + "\n")
    print("\n== GQ contrast:", gq)
    print("== MOE ~ 1/sqrt(n):", scaling)
    print("\n== Metro quality")
    print(quality.to_string(index=False))


if __name__ == "__main__":
    main()
