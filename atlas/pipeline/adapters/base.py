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
# Phase 4 (ADR 0012, Nathan's decisions): every source also carries its
# exact citation string(s), the notice its terms put beside them, and the
# conditions the build commits to. build.cube refuses a served feature
# that traces to a source that is not shippable or has no citation, and
# the "Sources and credits" section renders these strings as they are.

CENSUS_API_NOTICE = ("This product uses the Census Bureau Data API but is not "
                     "endorsed or certified by the Census Bureau.")
_CENSUS_TERMS = "https://www.census.gov/data/developers/about/terms-of-service.html"
_CENSUS_CONDITIONS = (
    "cite with the Census Bureau Data API notice (the census adapter calls the API)",
    "a figure the site computes is an estimate by Dating Stats Atlas, never "
    "\"Census data\"",
    "no Census Bureau logo or seal, and nothing implying endorsement",
)
_FEDERAL_CONDITIONS = ("no agency logo or seal, and nothing implying endorsement",)


def _census(*products: str) -> tuple[str, ...]:
    return tuple(f"Source: U.S. Census Bureau, {p}; estimates by Dating Stats Atlas."
                 for p in products)


CENSUS_ACS = LicenseTerms(
    name="US public domain (17 USC 105); Census API terms",
    url=_CENSUS_TERMS,
    shippable=True,
    attribution="Source: U.S. Census Bureau",
    citations=_census(
        "American Community Survey 2020–2024 5-year Public Use Microdata Sample",
        "American Community Survey 2020–2024 5-year detailed tables"),
    notice=CENSUS_API_NOTICE,
    conditions=_CENSUS_CONDITIONS,
)
CENSUS_DHC = LicenseTerms(
    name="US public domain (17 USC 105); Census API terms",
    url=_CENSUS_TERMS,
    shippable=True,
    attribution="Source: U.S. Census Bureau",
    citations=_census("2020 Census Demographic and Housing Characteristics File"),
    notice=CENSUS_API_NOTICE,
    conditions=_CENSUS_CONDITIONS,
)
CENSUS_GEO = LicenseTerms(
    name="US public domain (17 USC 105); Census API terms",
    url=_CENSUS_TERMS,
    shippable=True,
    attribution="Source: U.S. Census Bureau",
    citations=_census(
        "2020 Census tract relationship files",
        "TIGERweb and the 2023 cartographic boundary files"),
    notice=CENSUS_API_NOTICE,
    conditions=_CENSUS_CONDITIONS,
)
CENSUS_CBP = LicenseTerms(
    name="US public domain (17 USC 105); Census API terms",
    url=_CENSUS_TERMS,
    shippable=True,
    attribution="Source: U.S. Census Bureau",
    citations=_census("County Business Patterns 2023"),
    notice=CENSUS_API_NOTICE,
    conditions=_CENSUS_CONDITIONS,
)
OMB_DELINEATION = LicenseTerms(
    name="US public domain (17 USC 105); OMB",
    url="https://www.whitehouse.gov/wp-content/uploads/2023/07/OMB-Bulletin-23-01.pdf",
    shippable=True,
    citations=("Metropolitan areas as delineated in U.S. Office of Management and "
               "Budget Bulletin No. 23-01 (July 21, 2023).",),
    notes="Read through the census_geo adapter (the Census Bureau publishes the "
          "delineation file); credited as OMB's.",
    conditions=_FEDERAL_CONDITIONS,
)
PUBLIC_DOMAIN_BLS = LicenseTerms(
    name="US public domain (17 USC 105); BLS copyright statement",
    url="https://www.bls.gov/opub/copyright-information.htm",
    shippable=True,
    attribution="Source: U.S. Bureau of Labor Statistics",
    citations=("Source: U.S. Bureau of Labor Statistics, Quarterly Census of "
               "Employment and Wages, 2023.",),
    notes="A check only (beside County Business Patterns); no served figure "
          "traces to it, so the site does not show this citation.",
    conditions=_FEDERAL_CONDITIONS,
)
PUBLIC_DOMAIN_BEA = LicenseTerms(
    name="US public domain (17 USC 105); BEA terms",
    url="https://www.bea.gov/",
    shippable=True,
    attribution="Source: U.S. Bureau of Economic Analysis",
    citations=("Source: U.S. Bureau of Economic Analysis, Regional Price Parities "
               "by Metropolitan Area, 2024.",),
    conditions=_FEDERAL_CONDITIONS,
)
EPA_SLD_CC0 = LicenseTerms(
    name="CC0 / US public domain (EPA Smart Location Database)",
    url="https://www.epa.gov/smartgrowth/smart-location-mapping",
    shippable=True,
    attribution="Source: U.S. EPA Smart Location Database v3.0",
    notes="Street-network measures only; transit measures excluded (§12.1: "
          "GTFS snapshot from the deepest pandemic service cuts).",
    citations=("Source: U.S. Environmental Protection Agency, Smart Location "
               "Database v3.0 (June 2021).",),
    conditions=_FEDERAL_CONDITIONS,
)
PUBLIC_DOMAIN_NOAA = LicenseTerms(
    name="US public domain (17 USC 105); NOAA/NCEI open data",
    url="https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals",
    shippable=True,
    attribution="Source: NOAA NCEI U.S. Climate Normals 1991-2020",
    citations=("Source: NOAA National Centers for Environmental Information, U.S. "
               "Climate Normals 1991–2020.",),
    notes="Superseded by GHCN-Daily (Phase 2d); no served figure traces to it.",
    conditions=_FEDERAL_CONDITIONS,
)
PUBLIC_DOMAIN_GHCN = LicenseTerms(
    name="US public domain (17 USC 105); NOAA/NCEI open data",
    url="https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily",
    shippable=True,
    attribution="Source: NOAA GHCN-Daily, 1991–2020 observations",
    citations=("Source: NOAA National Centers for Environmental Information, Global "
               "Historical Climatology Network – Daily (GHCN-Daily), 1991–2020.",),
    conditions=_FEDERAL_CONDITIONS + (
        "US weather stations only: the adapter keeps US stations alone "
        "(ghcn_daily.US_STATION_PREFIX), and a test holds every served metro's "
        "station to it",),
)
PUBLIC_DOMAIN_IPEDS = LicenseTerms(
    name="US public domain (17 USC 105); NCES IPEDS",
    url="https://nces.ed.gov/ipeds/",
    shippable=True,
    attribution="Source: NCES IPEDS",
    citations=("Source: U.S. Department of Education, National Center for Education "
               "Statistics, Integrated Postsecondary Education Data System (IPEDS), "
               "2023–24.",),
    conditions=_FEDERAL_CONDITIONS,
)
PUBLIC_DOMAIN_HUD = LicenseTerms(
    name="US public domain (17 USC 105); HUD open data",
    url="https://www.huduser.gov/portal/datasets/50per.html",
    shippable=True,
    attribution="Source: U.S. Department of Housing and Urban Development",
    citations=("Source: U.S. Department of Housing and Urban Development, FY2027 "
               "50th Percentile Rent Estimates.",),
    conditions=_FEDERAL_CONDITIONS + (
        "read from HUD's bulk files, not an API: cite HUD only",),
)
FBI_CDE_CONTEXT_ONLY = LicenseTerms(
    name="US public domain; FBI Crime Data Explorer",
    url="https://cde.ucr.cjis.gov",
    shippable=True,
    notes="Never scored (D01): metro-page context only, with the FBI's own "
          "Caution Against Ranking attached. default_weight is pinned to 0.",
    citations=("Source: Federal Bureau of Investigation, Crime Data Explorer, 2025.",),
    conditions=_FEDERAL_CONDITIONS + (
        "context only, never scored",
        "the crime caveat stays with the figures: a note on the data's quality, "
        "not an attribution",),
)

# Phase 4d (Nathan's decision): each metro's 2024 presidential vote, shown
# as context — never scored, never a filter, never a weight, never asked of
# the visitor. Licence read from the dataset page on 30 September 2026:
# CC0 1.0, whose Terms tab asks for "the data citation shown on the dataset
# page"; the citation below is that string as the page shows it, with the
# house full stop at the end. The file sits behind the dataset's guestbook,
# so it is pinned by hand (adapters/medsl_president.py), never fetched.
MEDSL_PRESIDENT_CC0 = LicenseTerms(
    name="CC0 1.0 (Harvard Dataverse, doi:10.7910/DVN/VOQCHQ)",
    url="https://doi.org/10.7910/DVN/VOQCHQ",
    shippable=True,
    attribution="MIT Election Data and Science Lab",
    citations=('MIT Election Data and Science Lab, 2018, "County Presidential Election '
               'Returns 2000-2024", https://doi.org/10.7910/DVN/VOQCHQ, Harvard Dataverse, '
               'V20, UNF:6:xvsJJxrfXMIvzAuDYlfvVw== [fileUNF].',),
    notes="countypres_2000-2024.csv (V20, released 2026-02-25), downloaded by hand "
          "through the dataset's guestbook (name, email, institution, position) "
          "on 2026-09-30 and pinned by its sha256.",
    conditions=(
        "cite with the data citation shown on the dataset page (the Dataverse "
        "community norms the Terms tab names)",
        "context only: never scored, never a filter, never a weight or importance "
        "control, never feeding the compatibility figure, never asked of the visitor",
        "no MIT or lab logo, and nothing implying endorsement",
        "obtained through the dataset's guestbook by hand, never by the pipeline",),
)
# The lab's state-level returns: a check only (each state's summed county
# totals against the lab's own state totals). No served figure traces to
# it, so the site does not show its citation (the QCEW precedent).
MEDSL_PRESIDENT_STATE_CC0 = LicenseTerms(
    name="CC0 1.0 (Harvard Dataverse, doi:10.7910/DVN/42MVDX)",
    url="https://doi.org/10.7910/DVN/42MVDX",
    shippable=True,
    attribution="MIT Election Data and Science Lab",
    citations=('MIT Election Data and Science Lab, 2017, "U.S. President 1976–2024", '
               'https://doi.org/10.7910/DVN/42MVDX, Harvard Dataverse, V10, '
               'UNF:6:xpBppxfswpr+u9xZe7/u7w== [fileUNF].',),
    notes="A check only (the state totals beside the county file); no served figure "
          "traces to it, so the site does not show this citation.",
    conditions=("a check only, never served",),
)

# Phase 3c (A3): the one non-federal, non-Commons source the build reads.
# A validation reference only, read OUTSIDE any adapter by build.kernel
# and build.kernel_refine; marked non-shippable so that assert_all_shippable
# refuses any published field that ever traces to it, and guarded directly
# by build.validate's hard "pew never shipped" check, because the
# provenance assertion cannot see a file no adapter feeds. Phase 4 (ADR
# 0012, Nathan's decision): build-time only, never published and never
# compared in public; the table lives only in the gitignored private folder
# (pew_guard.PEW_TABLE), and it and every per-metro value copied from it
# left the repository and its history.
PEW_INTERMARRIAGE_REFERENCE = LicenseTerms(
    name="Pew Research Center, 'Intermarriage across the U.S. by metro area' "
         "(2017); Pew terms and conditions",
    url="https://www.pewresearch.org/about/terms-and-conditions/",
    shippable=False,
    attribution="Pew Research Center",
    conditions=("build-time only", "never published", "never compared in public",
                "replaced as the intermarriage check by the Census PUMS one (ADR 0016)"),
    notes="atlas/data/private/pew/pew_intermarriage_2015.csv (gitignored; the "
          "build machine only), accessed 2026-09-16: the 2011-2015 newlywed "
          "intermarriage rates for 124 metros and the nation. Build-time only: "
          "never published and never compared in public (ADR 0012); never "
          "chooses a kernel (ADR 0009 §2 as amended), never scored, never shipped.",
)

LICENSES: dict[str, LicenseTerms] = {
    "census_acs": CENSUS_ACS,
    "census_dhc": CENSUS_DHC,
    "census_geo": CENSUS_GEO,
    "census_cbp": CENSUS_CBP,
    "omb_delineation": OMB_DELINEATION,
    "bls_qcew": PUBLIC_DOMAIN_BLS,
    "bea_rpp": PUBLIC_DOMAIN_BEA,
    "epa_sld": EPA_SLD_CC0,
    "noaa_normals": PUBLIC_DOMAIN_NOAA,
    "ghcn_daily": PUBLIC_DOMAIN_GHCN,
    "ipeds": PUBLIC_DOMAIN_IPEDS,
    "hud_fmr50": PUBLIC_DOMAIN_HUD,
    "fbi_cde": FBI_CDE_CONTEXT_ONLY,
    "medsl_president": MEDSL_PRESIDENT_CC0,
    "medsl_president_state": MEDSL_PRESIDENT_STATE_CC0,
    "pew_intermarriage": PEW_INTERMARRIAGE_REFERENCE,
}

# Every served figure passes through the metro geography, which the build
# makes from these; they are credited beside the features' own sources
# and held to the same bar (contracts.provenance.assert_credited_shippable).
GEOGRAPHY_SOURCES = ("omb_delineation", "census_geo", "census_dhc")
