"""Census adapters: OMB delineation, tract-PUMA relationship, ACS summary
tables, ACS PUMS archives, and 2020 DHC tract group quarters.

These wrap the fetch/validate/provenance responsibilities that Phase 0/1
carried as ad-hoc functions. The DHC adapter is the poster child for why:
its requested variable list is the *single source* for both the query and
the manifest provenance record, so the Phase 1 bug — manifest saying "P5"
while the code queried P18 — cannot recur by construction.
"""
from __future__ import annotations

import pandas as pd
import requests as _rq

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.fetch import api_get, fetch

ACS_DATASET = "2024/acs/acs5"   # ACS 2020-2024 5-year
DHC_DATASET = "2020/dec/dhc"

DELINEATION_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/"
    "reference-files/2023/delineation-files/list1_2023.xlsx")
REL2020_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/"
    "2020_Census_Tract_to_2020_PUMA.txt")


class DelineationAdapter:
    source_id = "census_geo"
    vintage = "OMB Bulletin No. 23-01 (July 21, 2023)"
    license = LICENSES["census_geo"]

    def fetch(self) -> RawBundle:
        return RawBundle(self.source_id, [fetch(DELINEATION_URL)])

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        ok = df["cbsa"].str.fullmatch(r"\d{5}").all() and len(df) > 1000
        return Report(self.source_id, bool(ok), ["cbsa codes 5-digit", ">1000 county rows"])

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        df = pd.read_excel(raw.paths[0], header=2, dtype=str)
        df = df[df["CBSA Code"].str.fullmatch(r"\d{5}", na=False)].copy()
        df["county5"] = (df["FIPS State Code"].str.zfill(2)
                         + df["FIPS County Code"].str.zfill(3))
        df["is_metro"] = df["Metropolitan/Micropolitan Statistical Area"].eq(
            "Metropolitan Statistical Area")
        return df.rename(columns={"CBSA Code": "cbsa", "CBSA Title": "cbsa_title"})

    def provenance(self) -> Provenance:
        return Provenance("census_geo", "OMB CBSA delineation", "list1_2023.xlsx",
                          ("CBSA Code", "CBSA Title", "FIPS State Code",
                           "FIPS County Code"),
                          "county -> CBSA", "2023-07", "delineation_v1", "measured")


class TractPumaRelAdapter:
    source_id = "census_geo"
    vintage = "2020 Census tracts -> 2020 PUMAs"
    license = LICENSES["census_geo"]

    def fetch(self) -> RawBundle:
        return RawBundle(self.source_id, [fetch(REL2020_URL)])

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        ok = {"STATEFP", "COUNTYFP", "TRACTCE", "PUMA5CE"} <= set(df.columns)
        return Report(self.source_id, bool(ok), ["required columns present"])

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        df = pd.read_csv(raw.paths[0], dtype=str, encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        return df

    def provenance(self) -> Provenance:
        return Provenance("census_geo", "2020 tract to 2020 PUMA relationship",
                          "2020_Census_Tract_to_2020_PUMA.txt",
                          ("STATEFP", "COUNTYFP", "TRACTCE", "PUMA5CE"),
                          "tract", "2020", "bridge_v2", "measured")


class AcsSummaryAdapter:
    """Published ACS 2020-2024 5-year tables via the API (group() calls)."""
    source_id = "census_acs"
    vintage = "2020-2024 (ACS 5-year)"
    license = LICENSES["census_acs"]

    def __init__(self, table: str, geography: str):
        self.table = table
        self.geography = geography

    def fetch(self) -> RawBundle:
        rows = api_get(ACS_DATASET, {"get": f"group({self.table})",
                                     "for": f"{self.geography}:*"})
        return RawBundle(self.source_id, [], {"rows": rows})

    def group_labels(self) -> dict[str, str]:
        r = _rq.get(f"https://api.census.gov/data/{ACS_DATASET}/groups/"
                    f"{self.table}.json", timeout=60)
        r.raise_for_status()
        return {k: v["label"] for k, v in r.json()["variables"].items()
                if k.endswith("E")}

    def validate(self, raw: RawBundle) -> Report:
        ok = len(raw.meta["rows"]) > 1
        return Report(self.source_id, ok, [f"{self.table}: >0 rows"])

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        rows = raw.meta["rows"]
        return pd.DataFrame(rows[1:], columns=rows[0]).set_index(rows[0][-1])

    def provenance(self) -> Provenance:
        return Provenance("census_acs", f"acs/acs5 {self.vintage}", self.table,
                          (f"group({self.table})",), self.geography,
                          "2020-2024", f"summary_{self.table.lower()}", "measured")


class DhcTractGqAdapter:
    """2020 DHC tract-level total population and GQ by major type.

    GQ comes from table P18 (GROUP QUARTERS POPULATION BY SEX BY AGE BY
    MAJOR GROUP QUARTERS TYPE); the institutionalized / noninstitutionalized
    subtotals are selected from the group metadata by label. The DHC's P5 is
    a Hispanic-by-race table — Phase 1 caught that trap at query time and
    then mis-recorded it in the manifest; this adapter's requested_variables
    is now the single source for both the query and the manifest record.
    """
    source_id = "census_dhc"
    vintage = "2020 Census DHC"
    license = LICENSES["census_dhc"]
    TABLE = "P18"

    def __init__(self):
        meta = _rq.get(f"https://api.census.gov/data/{DHC_DATASET}/groups/"
                       f"{self.TABLE}.json", timeout=60).json()["variables"]
        self.inst_vars = sorted(
            v for v, d in meta.items() if v.endswith("N")
            and "!!Institutionalized population" in d["label"]
            and d["label"].count("!!") == 4)
        self.noninst_vars = sorted(
            v for v, d in meta.items() if v.endswith("N")
            and "!!Noninstitutionalized population" in d["label"]
            and d["label"].count("!!") == 4)
        assert len(self.inst_vars) == 6 and len(self.noninst_vars) == 6, (
            self.inst_vars, self.noninst_vars)
        self.requested_variables = sorted(
            ["P1_001N", "P18_001N"] + self.inst_vars + self.noninst_vars)

    def fetch_state(self, st: str) -> pd.DataFrame:
        get = ",".join(self.requested_variables)
        rows = api_get(DHC_DATASET, {"get": get, "for": "tract:*",
                                     "in": f"state:{st}"})
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df["geoid"] = df["state"] + df["county"] + df["tract"]
        num = df[self.requested_variables].apply(pd.to_numeric)
        df["pop2020"] = num["P1_001N"]
        df["gq_total"] = num["P18_001N"]
        df["gq_inst"] = num[self.inst_vars].sum(axis=1)
        df["gq_noninst"] = num[self.noninst_vars].sum(axis=1)
        return df[["geoid", "pop2020", "gq_total", "gq_inst", "gq_noninst"]]

    def fetch(self) -> RawBundle:  # per-state pulls happen via fetch_state
        return RawBundle(self.source_id)

    def validate(self, raw: RawBundle) -> Report:
        return Report(self.source_id, True,
                      ["per-tract identity gq_inst+gq_noninst==gq_total "
                       "asserted at use site"])

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        raise NotImplementedError("use fetch_state(st)")

    def provenance(self) -> Provenance:
        return Provenance("census_dhc", "2020 Census DHC (dec/dhc)",
                          "P18 (+P1_001N)", tuple(self.requested_variables),
                          "tract", "2020", "gq_alloc_v2", "measured")
