"""BEA Regional Price Parities, metro (MARPP), OMB 23-01 delineation.

Composition decision (recorded in the registry): the cost pillar uses
B25064 median gross rent plus RPP *Goods* and RPP *Services: Other* — the
all-items RPP is deliberately excluded because rent is measured directly at
metro level and all-items would double-count housing (its rents component).
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.fetch import fetch

URL = "https://apps.bea.gov/regional/zip/MARPP.zip"
MEMBER = "MARPP_MSA_2008_2024.csv"
YEAR = "2024"
SERIES = {"RPPs: Goods": "rpp_goods", "RPPs: Services: Other": "rpp_services_other",
          "RPPs: All items": "rpp_all_items"}  # all_items kept for reporting only


class BeaRppAdapter:
    source_id = "bea_rpp"
    vintage = f"MARPP {YEAR} (released 2026-02, OMB 23-01 delineation)"
    license = LICENSES["bea_rpp"]

    def fetch(self) -> RawBundle:
        return RawBundle(self.source_id, [fetch(URL)])

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        with zipfile.ZipFile(raw.paths[0]) as z:
            df = pd.read_csv(io.TextIOWrapper(z.open(MEMBER), "latin1"), dtype=str)
        df.columns = [c.strip() for c in df.columns]
        df["GeoFIPS"] = df["GeoFIPS"].str.strip().str.strip('"')
        df["Description"] = df["Description"].str.strip()
        df = df[df["GeoFIPS"].str.fullmatch(r"\d{5}") & (df["GeoFIPS"] != "00000")
                & (df["GeoFIPS"] != "00999") & df["Description"].isin(SERIES)]
        out = df.pivot_table(index="GeoFIPS", columns="Description", values=YEAR,
                             aggfunc="first")
        out = out.rename(columns=SERIES)
        for c in out.columns:
            out[c] = pd.to_numeric(out[c].replace("(NA)", None), errors="coerce")
        out.index.name = "cbsa"
        return out.reset_index()

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        checks, fails = [], []
        checks.append(f"{len(df)} metro rows")
        if not (300 < len(df) < 500):
            fails.append(f"unexpected metro count {len(df)}")
        med = df["rpp_all_items"].median()
        checks.append(f"median all-items RPP {med:.1f}")
        if not (90 < med < 105):
            fails.append(f"implausible RPP median {med}")
        # the file's own footnote pins the delineation; assert the marker text
        with zipfile.ZipFile(raw.paths[0]) as z:
            foot = z.read("MARPP__Footnotes.html").decode("latin1")
        if "23-01" not in foot:
            fails.append("delineation footnote does not name OMB 23-01")
        checks.append("footnote pins OMB 23-01")
        return Report(self.source_id, not fails, checks, fails)

    def provenance(self) -> Provenance:
        return Provenance("bea_rpp", "BEA Regional Price Parities (MARPP)",
                          MEMBER, ("RPPs: Goods", "RPPs: Services: Other"),
                          "cbsa", YEAR, "cost_rpp_v1", "measured")
