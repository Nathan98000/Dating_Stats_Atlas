"""Build the static context-feature matrix for the place pillars (cost,
reach, weather, students since m2.1.0) across all 387 metros, with the four
traps from the Phase 2a brief handled explicitly:

  - CBP/QCEW suppression: disclosure flags and absent cells are not nulls;
    absence counts per NAICS go in the report, and the two sources are
    cross-checked (correlation per NAICS + worst discrepancies).
  - EPA SLD is 2010 block groups: crosswalked through
    bridge/bg10_tract20.py, with metro-total reconciliation asserted.
  - "% of the pool in walkable tracts" is not computable from the cube:
    the feature is resident_walkability_index (SLD population-weighted),
    named so the distinction survives into the copy; the §5.3 mock's
    wording is flagged in the report.
  - Missing features stay NaN with a per-metro flag list; the scoring-time
    policy (registry `missing_data_policy`) renormalizes weights, never
    zero-fills.

Output: results/phase2/static_features.csv (committed) +
results/phase2/features_report.json. The cube build folds these into the
artifact's features.parquet.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from atlas.pipeline.adapters.bea_rpp import BeaRppAdapter
from atlas.pipeline.adapters.cbp import CbpAdapter
from atlas.pipeline.adapters.census import (ACS_DATASET, AcsSummaryAdapter,
                                            DelineationAdapter)
from atlas.pipeline.adapters.epa_sld import EpaSldAdapter
from atlas.pipeline.adapters.hud_fmr50 import HudFmr50Adapter
from atlas.pipeline.adapters.ipeds import IpedsAdapter
from atlas.pipeline.adapters.qcew import QcewAdapter
from atlas.pipeline.bridge.bg10_tract20 import bg10_to_metro_weights, crosswalk_sld
from atlas.pipeline.fetch import RESULTS, api_get
from atlas.pipeline.registry.loader import load_registry

P2 = RESULTS / "phase2"
STATIC_FEATURES = ["rent_1br", "rpp_goods", "rpp_services_other",
                   "venues_per_100k", "resident_walkability_index",
                   "pleasant_days", "students_per_1k_adults"]
NE_STATE_FIPS = {"CT": "09", "MA": "25", "ME": "23",
                 "NH": "33", "RI": "44", "VT": "50"}


def _num(x):
    if x is None or x in ("", "null"):
        return np.nan
    v = float(x)
    return np.nan if v <= -111111111 else v


def build() -> None:
    P2.mkdir(parents=True, exist_ok=True)
    reg = load_registry()
    metros = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})
    quality = pd.read_csv(RESULTS / "phase1" / "metro_quality.csv",
                          dtype={"cbsa": str})
    out = metros[["cbsa", "cbsa_title"]].merge(
        quality[["cbsa", "pop_pool_18_70"]], on="cbsa")
    report: dict = {"metros": len(out)}

    # ---- cost: HUD FY2027 50th-percentile 1-BR rent + BEA RPP --------------
    # m2.4.0 (ADR 0008): rent comes from HUD's 50th Percentile Rent
    # Estimates — gross rent (shelter + tenant-paid utilities) on HUD's
    # adjusted-standard-quality ACS 2020-2024 base, trended into the
    # fiscal year. HUD publishes per FMR AREA; the county file joins to
    # the site's metros through the same OMB 23-01 delineation the build
    # already holds. One rule everywhere: a metro's rent is the mean of
    # its counties' one-bedroom medians WEIGHTED BY RENTER-OCCUPIED
    # HOUSEHOLDS (B25003_003E) — renters, not population, because this
    # is an average of rents and should be weighted by the households
    # actually paying one. In the six New England states HUD publishes
    # town (county-subdivision) rows instead of county rows, so the same
    # weight applies one level down. A weighted mean of medians is NOT
    # the metro's median (the ADR owns that); the check that keeps it
    # honest: wherever a metro is a single FMR area, the weights cannot
    # move the mean, and the figure must equal HUD's published area
    # figure exactly.
    hud = HudFmr50Adapter()
    hraw = hud.fetch()
    hrep = hud.validate(hraw)
    assert hrep.passed, hrep.failures
    hrows = hud.normalize(hraw)
    delin = DelineationAdapter()
    dd = delin.normalize(delin.fetch())
    county_to_cbsa = dict(zip(dd["county5"], dd["cbsa"]))
    site_cbsas = set(out["cbsa"])
    site_counties = set(dd.loc[dd["cbsa"].isin(site_cbsas), "county5"])
    missing_counties = site_counties - set(hrows["county5"])
    assert not missing_counties, (
        f"{len(missing_counties)} delineation counties absent from the "
        f"HUD county file: {sorted(missing_counties)[:8]}")
    hrows = hrows[hrows["county5"].isin(site_counties)].copy()
    hrows["cbsa"] = hrows["county5"].map(county_to_cbsa)

    # renter-occupied households: county level everywhere, county
    # subdivision in New England (HUD's town rows carry sub codes).
    # HUD's subdivision codes lag FIPS revisions — Massachusetts "Town
    # cities" (Watertown, Methuen, Amesbury, Easthampton) and two tiny
    # Maine townships carry pre-revision codes against ACS 2024's
    # current ones — so unmatched rows fall back to a NAME join within
    # the county (refused on a within-county name collision), and only
    # a row under 1,000 people may end at weight zero. Every fallback
    # and every zero-weight row is named in the report.
    r_rows = AcsSummaryAdapter("B25003", "county").fetch().meta["rows"]
    rframe = pd.DataFrame(r_rows[1:], columns=r_rows[0])
    rframe["county5"] = rframe["state"] + rframe["county"]
    county_renters = dict(zip(rframe["county5"],
                              pd.to_numeric(rframe["B25003_003E"])))

    def _town_key(name: str) -> str:
        drop = {"town", "city", "plantation", "township", "gore", "grant",
                "location", "purchase", "ut"}
        toks = [t for t in str(name).lower().replace(",", " ").split()
                if t not in drop]
        return " ".join(toks)

    cousub_renters: dict[tuple[str, str], float] = {}
    cousub_by_name: dict[tuple[str, str], float | None] = {}
    for st in sorted(NE_STATE_FIPS.values()):
        rows_st = api_get(ACS_DATASET,
                          {"get": "NAME,B25003_003E",
                           "for": "county subdivision:*",
                           "in": f"state:{st}"})
        f = pd.DataFrame(rows_st[1:], columns=rows_st[0])
        for _, r in f.iterrows():
            c5 = r["state"] + r["county"]
            w = float(r["B25003_003E"])
            cousub_renters[(c5, r["county subdivision"])] = w
            key = (c5, _town_key(r["NAME"].split(",")[0]))
            # a within-county name collision poisons the fallback for
            # that name rather than guessing between towns
            cousub_by_name[key] = None if key in cousub_by_name else w

    is_town = hrows["county_sub_code"] != "99999"
    hrows["w"] = np.where(
        is_town,
        [cousub_renters.get((c, s), np.nan) for c, s in
         zip(hrows["county5"], hrows["county_sub_code"])],
        hrows["county5"].map(county_renters))
    name_fallback_rows = []
    zero_weight_rows = []
    for i in hrows.index[is_town & hrows["w"].isna()]:
        row = hrows.loc[i]
        by_name = cousub_by_name.get(
            (row["county5"], _town_key(row["town_name"])))
        if by_name is not None:
            hrows.loc[i, "w"] = by_name
            name_fallback_rows.append(
                f"{row['town_name']} ({row['county5']}/"
                f"{row['county_sub_code']})")
        else:
            assert float(row["pop2023"]) < 1000, (
                f"HUD town row {row['town_name']} ({row['county5']}/"
                f"{row['county_sub_code']}, pop {row['pop2023']:.0f}) has "
                f"no renter-household weight by code or name — investigate "
                f"before shipping")
            zero_weight_rows.append(
                f"{row['town_name']} ({row['county5']}/"
                f"{row['county_sub_code']}, pop {row['pop2023']:.0f})")
    hrows["w"] = hrows["w"].fillna(0.0)

    def _metro_rent(g: pd.DataFrame) -> float:
        wsum = float(g["w"].sum())
        assert wsum > 0, f"metro {g['cbsa'].iloc[0]}: zero renter weight"
        return float((g["rent_1br"] * g["w"]).sum() / wsum)

    metro_rent = hrows.groupby("cbsa").apply(_metro_rent, include_groups=False)
    out["rent_1br"] = out["cbsa"].map(metro_rent)
    assert out["rent_1br"].notna().all() and len(out) == 387, (
        f"HUD rent must cover every metro: "
        f"{int(out['rent_1br'].isna().sum())} missing of {len(out)}")
    ranked_flags = quality.set_index("cbsa")["ranked_set"]
    ranked_cbsas = set(ranked_flags[ranked_flags].index)
    assert out.loc[out["cbsa"].isin(ranked_cbsas), "rent_1br"].notna().all() \
        and len(ranked_cbsas) == 193, "all 193 ranked metros need a figure"

    # the exactness check: single-FMR-area metros must equal HUD's own
    # published area figure to the cent; multi-area metros report the
    # spread a single number is papering over
    areas = hud.areas(hraw).set_index("hud_area_code")
    n_area = hrows.groupby("cbsa")["hud_area_code"].nunique()
    single = sorted(n_area[n_area == 1].index)
    exact = 0
    for c in single:
        code = hrows.loc[hrows["cbsa"] == c, "hud_area_code"].iloc[0]
        assert abs(float(metro_rent[c]) - float(areas.loc[code, "rent_1br"])) \
            < 1e-9, (c, code, metro_rent[c], areas.loc[code, "rent_1br"])
        exact += 1
    spreads = (hrows.groupby("cbsa")["rent_1br"]
               .agg(lambda v: float(v.max() - v.min())))
    multi = sorted(n_area[n_area > 1].index)
    widest = spreads.loc[multi].sort_values(ascending=False).head(10)
    titles = dict(zip(out["cbsa"], out["cbsa_title"]))
    report["rent"] = {
        "source": "HUD FY2027 50th Percentile Rent Estimates, county file "
                  "(rent_50_1), renter-household-weighted (B25003_003E)",
        "county_rows_used": int(len(hrows)),
        "ne_town_rows": int(is_town.sum()),
        "ne_code_revision_name_fallbacks": name_fallback_rows,
        "ne_zero_weight_rows_under_1000_pop": zero_weight_rows,
        "metros_covered": int(out["rent_1br"].notna().sum()),
        "single_fmr_area_metros_exact_vs_area_file": exact,
        "multi_fmr_area_metros": len(multi),
        "widest_within_metro_spreads": [
            {"cbsa": c, "title": titles.get(c, c),
             "spread": round(float(s), 0)} for c, s in widest.items()],
    }

    bea = BeaRppAdapter()
    braw = bea.fetch()
    brep = bea.validate(braw)
    assert brep.passed, brep.failures
    rpp = bea.normalize(braw)
    out = out.merge(rpp[["cbsa", "rpp_goods", "rpp_services_other"]],
                    on="cbsa", how="left")
    report["rpp_missing_metros"] = sorted(
        out[out["rpp_goods"].isna()]["cbsa"].tolist())

    # ---- reach: CBP venues (+ QCEW cross-check) + SLD walkability ----------
    cbp = CbpAdapter()
    craw = cbp.fetch()
    crep = cbp.validate(craw)
    assert crep.passed, crep.failures
    cd = cbp.normalize(craw)
    cd = out[["cbsa"]].merge(cd, on="cbsa", how="left")
    estab_cols = [c for c in cd.columns if c.startswith("estab_")]
    report["cbp_absent_cells_by_naics"] = {
        c.replace("estab_", ""): int(cd[c].isna().sum()) for c in estab_cols}
    no_rows = cd[cd[estab_cols].isna().all(axis=1)]["cbsa"].tolist()
    report["cbp_metros_with_no_rows"] = no_rows
    qc = QcewAdapter()
    qd = qc.normalize(qc.fetch())
    report["qcew_suppressed_cells_by_naics"] = qd.attrs["suppressed_cells_by_naics"]
    xr0 = cd.merge(qd, on="cbsa", how="left")
    # An absent CBP cell is USUALLY a published zero, but QCEW shows some
    # small-NAICS absences are nonzero — quantify instead of asserting
    # "true zero", and zero-fill only for the venue SUM the feature uses
    # (the error there is a handful of establishments).
    report["cbp_absent_but_qcew_positive"] = {
        code: int((xr0[f"estab_{code}"].isna()
                   & (xr0[f"qcew_estab_{code}"].fillna(0) > 0)).sum())
        for code in report["cbp_absent_cells_by_naics"]}
    cd.loc[~cd[estab_cols].isna().all(axis=1), estab_cols] = (
        cd.loc[~cd[estab_cols].isna().all(axis=1), estab_cols].fillna(0))
    total_venues = cd[estab_cols].sum(axis=1, min_count=1)
    out["venues_per_100k"] = (total_venues / out["pop_pool_18_70"] * 100_000)

    xr = cd.merge(qd, on="cbsa", how="inner")
    xcheck = {}
    for code in report["cbp_absent_cells_by_naics"]:
        a, b = xr[f"estab_{code}"], xr[f"qcew_estab_{code}"]
        m = a.notna() & b.notna() & (a + b > 0)
        r = float(np.corrcoef(np.log1p(a[m]), np.log1p(b[m]))[0, 1])
        med_ratio = float((a[m] / b[m].replace(0, np.nan)).median())
        xcheck[code] = {"n": int(m.sum()), "log_corr": round(r, 4),
                        "median_cbp_over_qcew": round(med_ratio, 3)}
    qcew_cols = [f"qcew_estab_{c}" for c in report["cbp_absent_cells_by_naics"]]
    sum_a = xr[estab_cols].sum(axis=1, min_count=1)
    sum_b = xr[qcew_cols].sum(axis=1, min_count=1)
    m = sum_a.notna() & sum_b.notna() & (sum_a + sum_b > 0)
    sum_corr = float(np.corrcoef(np.log1p(sum_a[m]), np.log1p(sum_b[m]))[0, 1])
    xcheck["venue_sum"] = {"n": int(m.sum()), "log_corr": round(sum_corr, 4),
                           "median_cbp_over_qcew": round(
                               float((sum_a[m] / sum_b[m]).median()), 3)}
    report["cbp_vs_qcew"] = xcheck
    # The gate guards the quantity the feature consumes: the 6-code sum.
    # Per-code correlations (incl. the weaker museum/theater cells) are
    # reported as measured, not gated.
    assert sum_corr > 0.95, f"CBP/QCEW venue-sum cross-check failed: {xcheck}"

    sld_ad = EpaSldAdapter()
    sraw = sld_ad.fetch()
    srep = sld_ad.validate(sraw)
    assert srep.passed, srep.failures
    sld = sld_ad.normalize(sraw)
    weights = bg10_to_metro_weights()
    xw = crosswalk_sld(sld, weights)
    report["sld_unmatched_bg10"] = xw.attrs["unmatched_bg10"]
    report["sld_unmatched_pop"] = xw.attrs["unmatched_pop"]
    xw["wpop"] = xw["TotPop"].fillna(0) * xw["w"]
    grp = xw[xw["target"].isin(set(out["cbsa"]))].groupby("target")
    walk = grp.apply(lambda g: np.average(
        g["NatWalkInd"].fillna(g["NatWalkInd"].median()),
        weights=np.maximum(g["wpop"], 1e-9)), include_groups=False)
    sld_pop = grp["wpop"].sum()
    out["resident_walkability_index"] = out["cbsa"].map(walk)
    # reconciliation: crosswalked SLD population vs the build's metro pop.
    rec = out[["cbsa"]].copy()
    rec["sld_pop"] = rec["cbsa"].map(sld_pop)
    rec = rec.merge(quality[["cbsa", "pop_total"]], on="cbsa")
    rec["log_ratio"] = np.log(rec["sld_pop"] / rec["pop_total"])
    report["sld_reconciliation"] = {
        "corr_log_pop": float(np.corrcoef(np.log(rec["sld_pop"].clip(1)),
                                          np.log(rec["pop_total"]))[0, 1]),
        "median_log_ratio": float(rec["log_ratio"].median()),
        "max_abs_log_ratio": float(rec["log_ratio"].abs().max()),
        "worst": rec.reindex(rec["log_ratio"].abs().sort_values(ascending=False)
                             .index).head(5)[["cbsa", "sld_pop", "pop_total"]]
                 .to_dict("records"),
        "note": "SLD TotPop is ~2018 vintage at 2010 BGs vs 2020-2024 metro "
                "population; the assertion is structural (coverage), not "
                "vintage equality."}
    assert report["sld_reconciliation"]["corr_log_pop"] > 0.99, "SLD crosswalk broken"
    assert report["sld_reconciliation"]["max_abs_log_ratio"] < 0.35, (
        f"SLD metro totals fail reconciliation: {report['sld_reconciliation']}")

    # ---- weather: GHCN-Daily pleasant days (m2.1.0, item 11) ---------------
    # Computed on actual observations by build.pleasant_days (the long
    # fetch runs once, standalone); the Normals-based count is retired —
    # averaging destroyed the day-to-day variation the statistic exists to
    # count, which is how San Francisco served 365.
    ghcn_csv = RESULTS / "phase2d" / "pleasant_days_ghcn.csv"
    assert ghcn_csv.exists(), "run build.pleasant_days before build.features"
    nd = pd.read_csv(ghcn_csv, dtype={"cbsa": str})
    out = out.merge(nd[["cbsa", "pleasant_days"]], on="cbsa", how="left")
    report["ghcn_pleasant_days"] = {
        "metros_without_station": sorted(nd[nd["pleasant_days"].isna()]["cbsa"]),
        "median_station_km": float(nd["station_km"].median()),
        "p95_station_km": float(nd["station_km"].quantile(0.95)),
        "fallback_rank_gt0": int((nd["station_rank"].fillna(0) > 0).sum()),
        "definition": dict(reg.pleasant_day)}

    # ---- students: IPEDS ---------------------------------------------------
    delin_ad = DelineationAdapter()
    delin = delin_ad.normalize(delin_ad.fetch())

    ip = IpedsAdapter()
    iraw = ip.fetch()
    irep = ip.validate(iraw)
    assert irep.passed, irep.failures
    inst = ip.normalize(iraw)
    known = set(out["cbsa"])
    inst["cbsa_hd"] = inst["CBSA"].astype(str).str.zfill(5)
    inst["cbsa_cty"] = inst["COUNTYCD"].astype(str).str.zfill(5).map(
        dict(zip(delin["county5"], delin["cbsa"])))
    inst["metro"] = np.where(inst["cbsa_hd"].isin(known), inst["cbsa_hd"],
                             inst["cbsa_cty"])
    report["ipeds"] = {
        "institutions": int(len(inst)),
        "hd_cbsa_used": int(inst["cbsa_hd"].isin(known).sum()),
        "county_fallback_used": int((~inst["cbsa_hd"].isin(known)
                                     & inst["cbsa_cty"].notna()).sum()),
        "unassigned": int(inst["metro"].isna().sum()),
        "negative_net_clipped": int((inst["net"] < 0).sum())}
    students = inst[inst["metro"].isin(known)].groupby("metro")["net"].sum()
    out["students_per_1k_adults"] = (out["cbsa"].map(students).fillna(0)
                                     / out["pop_pool_18_70"] * 1_000)

    # ---- missing-data flags (policy applied at scoring time) ---------------
    out["feature_flags"] = out[STATIC_FEATURES].isna().apply(
        lambda row: ";".join(sorted(row.index[row])), axis=1)
    report["missing_by_feature"] = {
        f: int(out[f].isna().sum()) for f in STATIC_FEATURES}
    report["metros_with_any_missing"] = int((out["feature_flags"] != "").sum())
    report["spec_wording_flag"] = (
        "§5.3 mock says '% of the pool in walkable tracts'; the pool exists "
        "only at metro level after PUMA allocation, so the shipped feature is "
        "resident_walkability_index (SLD population-weighted walkability of "
        "the metro's residents). Frontend copy must say residents, not pool.")

    out.to_csv(P2 / "static_features.csv", index=False)
    (P2 / "features_report.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: report[k] for k in
                      ["cbp_vs_qcew", "sld_reconciliation", "missing_by_feature",
                       "metros_with_any_missing"]}, indent=2, default=str))
    print(f"static features -> {P2 / 'static_features.csv'} ({len(out)} metros)")


if __name__ == "__main__":
    build()
