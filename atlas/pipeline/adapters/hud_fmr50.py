"""HUD 50th Percentile Rent Estimates, FY2027 (Phase 2g item 1).

The rent statistic's source since m2.4.0 (ADR 0008): HUD publishes
50th-percentile (median) gross rents — shelter plus tenant-paid
utilities — for every Fair Market Rent area, annually. Per HUD's FY27
methodology: the base is ACS 2024 5-year (2020–2024) "adjusted standard
quality" gross rents (cash rent, ten acres or less, full plumbing,
complete kitchen, meals not included; units under the 75th percentile
of public-housing rents removed), carried to the fiscal year by a
recent-mover adjustment, a 2024→2025 gross-rent inflation factor, and a
trend factor; published 50th-percentile rents are floored at the FMR.
FY2027 is the first year the utility component comes from composite
EIA/BLS inflation factors rather than the metro CPI utility indices BLS
discontinued in January 2025.

Geography: the COUNTY file (verified schema: sheet fy2027_fmr_50,
4,764 rows; columns state_code, county_code, county_sub_code, cntyname,
town_name, hud_areaname, fips2025, rent_50_0..rent_50_4, hud_area_code,
state_alpha, pop2023). rent_50_1 is the one-bedroom figure. Outside New
England every county is one row; in the six New England states HUD
publishes town (county-subdivision) rows instead, and 14 counties span
two HUD areas — the build collapses those with renter-household weights
at the subdivision level (features.py).

huduser.gov answers a non-browser User-Agent with an empty 202, so this
adapter fetches with a browser UA through the same content-addressed
cache and manifest as every other source.
"""
from __future__ import annotations

import pandas as pd

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.fetch import fetch

COUNTY_URL = ("https://www.huduser.gov/portal/datasets/50thper/"
              "FY2027_FMR_50_county.xlsx")
AREA_URL = ("https://www.huduser.gov/portal/datasets/50thper/"
            "FY2027_FMR_50_area.xlsx")
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
# a US monthly one-bedroom median outside this band is a parsing bug,
# not a market
PLAUSIBLE_1BR = (300.0, 6000.0)
NEW_ENGLAND = ("CT", "MA", "ME", "NH", "RI", "VT")


class HudFmr50Adapter:
    source_id = "hud_fmr50"
    vintage = "FY2027 50th Percentile Rent Estimates"
    license = LICENSES["hud_fmr50"]

    def fetch(self) -> RawBundle:
        return RawBundle(self.source_id, [
            fetch(COUNTY_URL, headers=BROWSER_UA),
            fetch(AREA_URL, headers=BROWSER_UA),
        ])

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        """County-file rows: county5, county_sub_code, town_name,
        state_alpha, hud_area_code, hud_areaname, rent_1br (float),
        pop2023 (float). town_name matters because HUD's New England
        subdivision codes lag FIPS revisions (Massachusetts "Town
        cities", two Maine townships) — the build falls back to a
        name join within the county for those rows."""
        df = pd.read_excel(raw.paths[0], dtype=str)
        df["county5"] = (df["state_code"].str.zfill(2)
                         + df["county_code"].str.zfill(3))
        df["rent_1br"] = pd.to_numeric(df["rent_50_1"])
        df["pop2023"] = pd.to_numeric(df["pop2023"])
        return df[["county5", "county_sub_code", "town_name", "state_alpha",
                   "hud_area_code", "hud_areaname", "rent_1br", "pop2023"]]

    def areas(self, raw: RawBundle) -> pd.DataFrame:
        """Area-file rows for the exactness check: hud_area_code,
        rent_1br."""
        df = pd.read_excel(raw.paths[1], dtype=str)
        df["rent_1br"] = pd.to_numeric(df["rent_50_1"])
        return df[["hud_area_code", "hud_areaname", "rent_1br"]]

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        failures = []
        if not df["county5"].str.fullmatch(r"\d{5}").all():
            failures.append("county FIPS not all five digits")
        if df["rent_1br"].isna().any():
            failures.append(f"{int(df['rent_1br'].isna().sum())} rows "
                            f"missing the one-bedroom figure")
        lo, hi = PLAUSIBLE_1BR
        bad = df[(df["rent_1br"] < lo) | (df["rent_1br"] > hi)]
        if len(bad):
            failures.append(f"{len(bad)} one-bedroom values outside "
                            f"[{lo:.0f}, {hi:.0f}]")
        outside_ne = ~df["state_alpha"].isin(NEW_ENGLAND)
        if (df.loc[outside_ne, "county_sub_code"] != "99999").any():
            failures.append("sub-county rows outside New England — the "
                            "collapse rule assumed there are none")
        return Report(self.source_id, not failures,
                      failures or ["FIPS 5-digit", "rent_50_1 populated",
                                   "values plausible",
                                   "sub-county rows NE-only"])

    def provenance(self) -> Provenance:
        return Provenance("hud_fmr50",
                          "HUD 50th Percentile Rent Estimates, FY2027",
                          "FY2027_FMR_50_county.xlsx",
                          ("rent_50_1",),
                          "county (NE: county subdivision) -> cbsa",
                          "FY2027", "cost_rent_1br_hud_v1", "measured")
