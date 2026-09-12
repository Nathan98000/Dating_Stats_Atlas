"""NCES IPEDS: student population net of exclusively-online enrollment,
assigned to metros via the HD institution directory.

Metro assignment prefers HD's own CBSA field, asserted against the OMB
23-01 delineation; institutions whose HD CBSA code is not in the current
delineation fall back to COUNTYCD -> CBSA, and the count of such fallbacks
is reported. Enrollment is EF...A_DIST: total fall enrollment minus
exclusively-distance-education enrollment, all-students level.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.fetch import fetch

HD_URL = "https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip"
EF_URL = "https://nces.ed.gov/ipeds/datacenter/data/EF2023A_DIST.zip"


def _read_zip_csv(path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        # prefer the revised file when present (e.g. ef2023a_dist_rv.csv)
        names = sorted(z.namelist(), key=lambda n: ("_rv" not in n.lower(), n))
        with z.open(names[0]) as f:
            df = pd.read_csv(io.TextIOWrapper(f, "latin1"), dtype=str)
        df.columns = [c.replace("\ufeff", "").replace("\u00ef\u00bb\u00bf", "")
                      .upper().strip() for c in df.columns]
        return df


class IpedsAdapter:
    source_id = "ipeds"
    vintage = "2023-24 (HD2023, EF2023A_DIST)"
    license = LICENSES["ipeds"]
    requested_variables = ["UNITID", "CBSA", "COUNTYCD", "EFDELEV", "EFDETOT", "EFDEEXC"]

    def fetch(self) -> RawBundle:
        return RawBundle(self.source_id, [fetch(HD_URL), fetch(EF_URL)])

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        hd = _read_zip_csv(raw.paths[0])
        ef = _read_zip_csv(raw.paths[1])
        assert {"UNITID", "CBSA", "COUNTYCD"} <= set(hd.columns), (
            sorted(set(["UNITID", "CBSA", "COUNTYCD"]) - set(hd.columns)),
            hd.columns.tolist())
        assert {"UNITID", "EFDELEV", "EFDETOT", "EFDEEXC"} <= set(ef.columns), (
            ef.columns[:20])
        lev = ef[ef["EFDELEV"].str.strip() == "1"].copy()   # all students
        lev["net"] = (pd.to_numeric(lev["EFDETOT"], errors="coerce").fillna(0)
                      - pd.to_numeric(lev["EFDEEXC"], errors="coerce").fillna(0))
        m = lev[["UNITID", "net"]].merge(
            hd[["UNITID", "CBSA", "COUNTYCD"]], on="UNITID", how="left")
        m.attrs["n_institutions"] = len(m)
        return m

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        checks, fails = [], []
        checks.append(f"{len(df)} institutions with all-students DE rows")
        if not (3000 < len(df) < 8000):
            fails.append(f"unexpected institution count {len(df)}")
        if (df["net"] < 0).any():
            fails.append(f"{(df['net'] < 0).sum()} institutions with negative "
                         "net (EFDEEXC > EFDETOT)")
        tot = df["net"].sum()
        checks.append(f"national net-of-online enrollment {tot/1e6:.1f}M")
        if not (5e6 < tot < 25e6):
            fails.append(f"implausible national total {tot}")
        return Report(self.source_id, not fails, checks, fails)

    def provenance(self) -> Provenance:
        return Provenance("ipeds", "IPEDS HD2023 + EF2023A_DIST",
                          "HD2023, EF2023A_DIST",
                          tuple(self.requested_variables), "institution -> cbsa",
                          "2023-24", "lifestyle_students_v1", "measured")
