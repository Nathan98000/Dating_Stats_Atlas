"""BLS QCEW annual averages by industry — the cross-check for CBP
establishment counts (§6: "calibration truth for POI density"; here it
guards the venue counts themselves).

Suppression handling: QCEW marks suppressed cells with disclosure_code "N";
establishment counts remain published (only employment/wages are withheld),
so the cross-check uses annual_avg_estabs and reports the count of
N-flagged cells per NAICS rather than treating them as nulls.
"""
from __future__ import annotations

import io

import pandas as pd
import requests

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.adapters.cbp import NAICS

YEAR = "2024"
URL_TMPL = "https://data.bls.gov/cew/data/api/{year}/a/industry/{code}.csv"
UA = {"User-Agent": "DatingStatsAtlas-phase2/0.1 (research pipeline)"}


class QcewAdapter:
    source_id = "bls_qcew"
    vintage = f"QCEW {YEAR} annual averages"
    license = LICENSES["bls_qcew"]

    def fetch(self) -> RawBundle:
        frames = {}
        for code in NAICS:
            r = requests.get(URL_TMPL.format(year=YEAR, code=code),
                             headers=UA, timeout=120)
            r.raise_for_status()
            frames[code] = pd.read_csv(io.StringIO(r.text), dtype=str)
        return RawBundle(self.source_id, [], {"frames": frames})

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        out, flags = None, {}
        for code, df in raw.meta["frames"].items():
            m = df[df["area_fips"].str.startswith("C")
                   & (df["own_code"] == "5")].copy()          # private ownership
            m["cbsa"] = m["area_fips"].str[1:] + "0"
            m[f"qcew_estab_{code}"] = pd.to_numeric(m["annual_avg_estabs"])
            flags[code] = int((m["disclosure_code"] == "N").sum())
            m = m[["cbsa", f"qcew_estab_{code}"]]
            out = m if out is None else out.merge(m, on="cbsa", how="outer")
        out.attrs["suppressed_cells_by_naics"] = flags
        return out

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        checks, fails = [], []
        checks.append(f"{len(df)} MSA rows; suppressed(N) cells by NAICS: "
                      f"{df.attrs['suppressed_cells_by_naics']}")
        if len(df) < 300:
            fails.append(f"too few MSA rows: {len(df)}")
        return Report(self.source_id, not fails, checks, fails)

    def provenance(self) -> Provenance:
        return Provenance("bls_qcew", "QCEW open data (annual by industry)",
                          f"{YEAR} a/industry", tuple(sorted(NAICS)),
                          "cbsa (area_fips C-codes)", YEAR,
                          "reach_venues_xcheck_v1", "measured")
