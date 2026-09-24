"""Adapter contract (§6.1): one typed adapter per source, provenance and
license attached at the source rather than sprinkled through the pipeline.

Adapters wrap the content-addressed cache in pipeline/fetch.py, so every
fetch is idempotent and lands in the fetch manifest with URL, SHA-256, byte
size and timestamp.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import pandas as pd

from atlas.pipeline.contracts.provenance import LicenseTerms, Provenance, Report


@dataclass
class RawBundle:
    source_id: str
    paths: list[Path] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


@runtime_checkable
class Adapter(Protocol):
    source_id: str
    vintage: str
    license: LicenseTerms

    def fetch(self) -> RawBundle: ...
    def validate(self, raw: RawBundle) -> Report: ...
    def normalize(self, raw: RawBundle) -> pd.DataFrame: ...
    def provenance(self) -> Provenance: ...


# ---- License registry. `shippable` is the load-bearing bit (§4.6). --------

PUBLIC_DOMAIN_CENSUS = LicenseTerms(
    name="US public domain (17 USC 105); Census API terms",
    url="https://www.census.gov/data/developers/about/terms-of-service.html",
    shippable=True,
    attribution="Source: U.S. Census Bureau",
)
PUBLIC_DOMAIN_BLS = LicenseTerms(
    name="US public domain (17 USC 105); BLS copyright statement",
    url="https://www.bls.gov/opub/copyright-information.htm",
    shippable=True,
    attribution="Source: U.S. Bureau of Labor Statistics",
)
PUBLIC_DOMAIN_BEA = LicenseTerms(
    name="US public domain (17 USC 105); BEA terms",
    url="https://www.bea.gov/",
    shippable=True,
    attribution="Source: U.S. Bureau of Economic Analysis",
)
EPA_SLD_CC0 = LicenseTerms(
    name="CC0 / US public domain (EPA Smart Location Database)",
    url="https://www.epa.gov/smartgrowth/smart-location-mapping",
    shippable=True,
    attribution="Source: U.S. EPA Smart Location Database v3.0",
    notes="Street-network measures only; transit measures excluded (§12.1: "
          "GTFS snapshot from the deepest pandemic service cuts).",
)
PUBLIC_DOMAIN_NOAA = LicenseTerms(
    name="US public domain (17 USC 105); NOAA/NCEI open data",
    url="https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals",
    shippable=True,
    attribution="Source: NOAA NCEI U.S. Climate Normals 1991-2020",
)
PUBLIC_DOMAIN_GHCN = LicenseTerms(
    name="US public domain (17 USC 105); NOAA/NCEI open data",
    url="https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily",
    shippable=True,
    attribution="Source: NOAA GHCN-Daily, 1991–2020 observations",
)
PUBLIC_DOMAIN_IPEDS = LicenseTerms(
    name="US public domain (17 USC 105); NCES IPEDS",
    url="https://nces.ed.gov/ipeds/",
    shippable=True,
    attribution="Source: NCES IPEDS",
)
PUBLIC_DOMAIN_HUD = LicenseTerms(
    name="US public domain (17 USC 105); HUD open data",
    url="https://www.huduser.gov/portal/datasets/50per.html",
    shippable=True,
    attribution="Source: U.S. Department of Housing and Urban Development",
)
FBI_CDE_CONTEXT_ONLY = LicenseTerms(
    name="US public domain; FBI Crime Data Explorer",
    url="https://cde.ucr.cjis.gov",
    shippable=True,
    notes="Never scored (D01): metro-page context only, with the FBI's own "
          "Caution Against Ranking attached. default_weight is pinned to 0.",
)

# Phase 3c (A3): the one non-federal, non-Commons source the build reads.
# A validation reference only, read OUTSIDE any adapter by build.kernel,
# build.kernel_refine and build.validate; marked non-shippable so that
# assert_all_shippable refuses any published field that ever traces to it,
# and guarded directly by build.validate's hard "pew never shipped" check,
# because the provenance assertion cannot see a file no adapter feeds.
PEW_INTERMARRIAGE_REFERENCE = LicenseTerms(
    name="Pew Research Center, 'Intermarriage across the U.S. by metro area' "
         "(2017); Pew terms and conditions",
    url="https://www.pewresearch.org/about/terms-and-conditions/",
    shippable=False,
    attribution="Pew Research Center",
    notes="results/reference/pew_intermarriage_2015.csv, accessed 2026-09-16: "
          "the 2011-2015 newlywed intermarriage rates for 124 metros and the "
          "nation. Out-of-sample check on the chances-of-matching kernel "
          "(leave one metro out, predict its rate, compare); never chooses a "
          "kernel (ADR 0009 §2 as amended), never scored, never shipped.",
)

LICENSES: dict[str, LicenseTerms] = {
    "census_acs": PUBLIC_DOMAIN_CENSUS,
    "census_dhc": PUBLIC_DOMAIN_CENSUS,
    "census_geo": PUBLIC_DOMAIN_CENSUS,
    "census_cbp": PUBLIC_DOMAIN_CENSUS,
    "bls_qcew": PUBLIC_DOMAIN_BLS,
    "bea_rpp": PUBLIC_DOMAIN_BEA,
    "epa_sld": EPA_SLD_CC0,
    "noaa_normals": PUBLIC_DOMAIN_NOAA,
    "ghcn_daily": PUBLIC_DOMAIN_GHCN,
    "ipeds": PUBLIC_DOMAIN_IPEDS,
    "hud_fmr50": PUBLIC_DOMAIN_HUD,
    "fbi_cde": FBI_CDE_CONTEXT_ONLY,
    "pew_intermarriage": PEW_INTERMARRIAGE_REFERENCE,
}
