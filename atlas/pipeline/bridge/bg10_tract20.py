"""2010 block group -> 2020 tract -> metro crosswalk, population-weighted.

Mechanism: BG10 nests exactly in its 2010 tract (GEOID prefix). The Census
tab20 tract relationship file gives every (tract20, tract10) intersection
piece with its land area, so a BG10's population is split across 2020
tracts by its parent tract10's land-area split — a uniform-density
approximation that only acts at the minority of tract10s that were actually
split in 2020 (documented; most map whole). 2020 tracts then map to metros
by county prefix, with the same CT planning-region handling as the main
bridge (tab20 GEOIDs carry the old CT counties; the delineation carries
planning regions).

The reconciliation assertion required by the Phase 2a brief lives in
crosswalked_metro_totals(): crosswalked population per metro must
reconcile against the build's metro populations.
"""
from __future__ import annotations

import pandas as pd

from atlas.pipeline.adapters.census import ACS_DATASET, DelineationAdapter
from atlas.pipeline.fetch import api_get, fetch

T20_T10_URL = ("https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/"
               "tab20_tract20_tract10_natl.txt")


def _ct_tract20_to_target(county_to_cbsa: dict[str, str]) -> dict[str, str]:
    """TRACTCE -> CBSA/NONMETRO for CT, via the ACS planning-region universe
    (same approach as the main bridge)."""
    rows = api_get(ACS_DATASET, {"get": "B01003_001E", "for": "tract:*",
                                 "in": "state:09"})
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df[~df["tract"].duplicated(keep=False)]  # water-tract collisions out
    return {t: county_to_cbsa.get("09" + c, "NONMETRO")
            for t, c in zip(df["tract"], df["county"])}


def bg10_to_metro_weights() -> pd.DataFrame:
    """One row per (bg10, target) with the share of the BG10's population
    assigned there: columns geoid10, target, w."""
    delin = DelineationAdapter()
    dd = delin.normalize(delin.fetch())
    county_to_cbsa = dict(zip(dd["county5"], dd["cbsa"]))
    ct_map = _ct_tract20_to_target(county_to_cbsa)

    rel = pd.read_csv(fetch(T20_T10_URL), sep="|", dtype=str, encoding="utf-8-sig")
    rel.columns = [c.strip().upper() for c in rel.columns]
    t20 = "GEOID_TRACT_20"
    t10 = "GEOID_TRACT_10"
    area = "AREALAND_PART"
    assert {t20, t10, area} <= set(rel.columns), rel.columns.tolist()[:12]
    rel[area] = pd.to_numeric(rel[area])
    rel = rel[rel[t10].notna() & rel[t20].notna()]

    tot = rel.groupby(t10)[area].transform("sum")
    rel = rel[tot > 0].copy()
    rel["w"] = rel[area] / rel.groupby(t10)[area].transform("sum")

    def target_of(g20: str) -> str:
        if g20.startswith("09"):
            return ct_map.get(g20[5:], "NONMETRO")
        return county_to_cbsa.get(g20[:5], "NONMETRO")

    t20_targets = {g: target_of(g) for g in rel[t20].unique()}
    rel["target"] = rel[t20].map(t20_targets)
    out = (rel.groupby([t10, "target"], as_index=False)["w"].sum()
           .rename(columns={t10: "tract10"}))
    sums = out.groupby("tract10")["w"].sum()
    off = sums[(sums - 1.0).abs() > 1e-6]
    assert not len(off), f"tract10 split weights do not sum to 1 for {len(off)}"
    return out


def crosswalk_sld(sld: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    """Attach (target, w) to every SLD BG10 row via its parent tract10."""
    sld = sld.copy()
    sld["tract10"] = sld["GEOID10"].str[:11]
    m = sld.merge(weights, on="tract10", how="left")
    unmatched = m[m["target"].isna()]
    un_pop = float(unmatched.drop_duplicates("GEOID10")["TotPop"].fillna(0).sum())
    m.attrs["unmatched_bg10"] = int(unmatched["GEOID10"].nunique())
    m.attrs["unmatched_pop"] = un_pop
    return m[m["target"].notna()]
