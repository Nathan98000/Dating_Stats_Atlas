"""Census County Business Patterns 2023: establishment counts by NAICS at
metro level — the reach pillar's venue counts, cross-checked against QCEW.

Suppression handling: CBP publishes establishment counts even where
employment is suppressed, and cells with zero establishments are simply
absent from the response. An absent (metro, NAICS) row is therefore a true
zero, not a null — but a metro absent for EVERY code is a coverage problem
and is flagged, never zero-filled silently. The per-NAICS absence counts go
in the features report.
"""
from __future__ import annotations

import pandas as pd

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.fetch import api_get

DATASET = "2023/cbp"
GEO = "metropolitan statistical area/micropolitan statistical area"
# The NAICS selection lives in the registry (§7.2) — the one canonical home.
from atlas.pipeline.registry.loader import load_registry

NAICS = load_registry().naics_venues


class CbpAdapter:
    source_id = "census_cbp"
    vintage = "CBP 2023 (NAICS2017)"
    license = LICENSES["census_cbp"]
    requested_variables = ["ESTAB", "NAICS2017"]

    def fetch(self) -> RawBundle:
        frames = {}
        for code in NAICS:
            rows = api_get(DATASET, {"get": "ESTAB", "for": f"{GEO}:*",
                                     "NAICS2017": code})
            df = pd.DataFrame(rows[1:], columns=rows[0])
            frames[code] = df
        return RawBundle(self.source_id, [], {"frames": frames})

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        out = None
        geo_col = GEO
        for code, df in raw.meta["frames"].items():
            d = df.rename(columns={geo_col: "cbsa"})[["cbsa", "ESTAB"]].copy()
            d[f"estab_{code}"] = pd.to_numeric(d["ESTAB"])
            d = d[["cbsa", f"estab_{code}"]]
            out = d if out is None else out.merge(d, on="cbsa", how="outer")
        return out

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        checks, fails = [], []
        neg = (df.drop(columns="cbsa") < 0).any().any()
        if neg:
            fails.append("negative establishment counts (jam values?)")
        checks.append(f"{len(df)} CBSAs with >=1 code present")
        big = df[df["cbsa"] == "35620"]
        if len(big) and not (big["estab_722511"].iloc[0] > 5000):
            fails.append("NY full-service restaurant count implausibly low")
        checks.append("NY 722511 sanity")
        return Report(self.source_id, not fails, checks, fails)

    def provenance(self) -> Provenance:
        return Provenance("census_cbp", "County Business Patterns", "CBP 2023",
                          tuple(["ESTAB"] + [f"NAICS2017={c}" for c in sorted(NAICS)]),
                          "cbsa", "2023", "reach_venues_v1", "measured")
