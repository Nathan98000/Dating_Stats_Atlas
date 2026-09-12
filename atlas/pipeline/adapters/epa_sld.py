"""EPA Smart Location Database v3.0 — street-network walkability at 2010
block groups, pulled from EPA's ArcGIS REST service with field selection
(no 1.1 GB geodatabase, no GDAL dependency).

Only street-network-derived measures are taken (NatWalkInd, D3B intersection
density); SLD transit measures are excluded per §12.1 (its GTFS snapshot
dates from the deepest pandemic service cuts). SLD is 2010 block-group
geography; the crosswalk to 2020 tracts and metros lives in
pipeline/bridge/bg10_tract20.py, not here.
"""
from __future__ import annotations

import json
import time

import pandas as pd
import requests

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.fetch import DATA

BASE = ("https://geodata.epa.gov/arcgis/rest/services/OA/"
        "SmartLocationDatabase/MapServer")
FIELDS = ["GEOID10", "GEOID20", "NatWalkInd", "D3B", "TotPop"]
CACHE = DATA / "adapters" / "epa_sld_bg10.parquet"
UA = {"User-Agent": "DatingStatsAtlas-phase2/0.1 (research pipeline)"}


class EpaSldAdapter:
    source_id = "epa_sld"
    vintage = "SLD v3.0 (June 2021), 2010 block groups"
    license = LICENSES["epa_sld"]
    requested_variables = FIELDS

    def _layer(self) -> int:
        info = requests.get(f"{BASE}?f=pjson", headers=UA, timeout=60).json()
        for lyr in info.get("layers", [{"id": 0}]):
            meta = requests.get(f"{BASE}/{lyr['id']}?f=pjson", headers=UA,
                                timeout=60).json()
            names = {f["name"] for f in (meta.get("fields") or [])}
            if meta.get("type") == "Feature Layer" and set(FIELDS) <= names:
                self._max_rec = int(meta.get("maxRecordCount", 1000))
                print(f"  SLD: using layer {lyr['id']} ({meta.get('name')}), "
                      f"maxRecordCount {self._max_rec}", flush=True)
                return lyr["id"]
        raise RuntimeError(f"no SLD feature layer carries {FIELDS}")

    def fetch(self) -> RawBundle:
        """State-partitioned queries: this server's deep-offset pagination
        degrades ~40x (measured 1.7s at offset 0 vs ~76s past offset 40k),
        so each state is pulled from offset 0 instead of paging nationally."""
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        if CACHE.exists():
            return RawBundle(self.source_id, [CACHE])
        from atlas.pipeline.bridge.tract_puma_cbsa import STATE_FIPS_TO_POSTAL
        layer = self._layer()
        page = min(self._max_rec, 5000)
        rows = []
        for st in sorted(STATE_FIPS_TO_POSTAL):
            offset = 0
            while True:
                r = requests.get(f"{BASE}/{layer}/query", headers=UA, timeout=180,
                                 params={"where": f"STATEFP='{st}'",
                                         "outFields": ",".join(FIELDS),
                                         "returnGeometry": "false", "f": "json",
                                         "orderByFields": "OBJECTID",
                                         "resultOffset": offset,
                                         "resultRecordCount": page})
                r.raise_for_status()
                d = r.json()
                if "error" in d:
                    raise RuntimeError(f"SLD {st} offset {offset}: {d['error']}")
                feats = d.get("features", [])
                if not feats and d.get("exceededTransferLimit"):
                    time.sleep(5)   # transient empty page: retry same offset
                    continue
                rows.extend(f["attributes"] for f in feats)
                offset += len(feats)
                if not d.get("exceededTransferLimit") and len(feats) < page:
                    break
                time.sleep(0.1)
            print(f"  SLD {st}: cumulative {len(rows):,}", flush=True)
        df = pd.DataFrame(rows)
        assert len(df) == 217_182, (
            f"SLD v3 has 217,182 BG10 rows in the 50 states + DC (220,134 "
            f"national minus 2,952 in AS/GU/MP/PR/VI); got {len(df):,} — a "
            "state was silently truncated (verify with returnCountOnly)")
        assert df["GEOID10"].nunique() == len(df), "duplicate BG10 rows"
        df.to_parquet(CACHE, index=False)
        (CACHE.with_suffix(".json")).write_text(json.dumps(
            {"source": f"{BASE}/{layer}/query", "fields": FIELDS,
             "rows": len(df), "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
            indent=2) + "\n")
        return RawBundle(self.source_id, [CACHE])

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        df = pd.read_parquet(raw.paths[0])
        df["GEOID10"] = df["GEOID10"].astype(str).str.zfill(12)
        for c in ["NatWalkInd", "D3B", "TotPop"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        checks, fails = [], []
        checks.append(f"{len(df):,} 2010 block groups")
        if len(df) != 217_182:
            fails.append(f"BG count {len(df):,} != 217,182 (51-state SLD v3)")
        w = df["NatWalkInd"].dropna()
        checks.append(f"NatWalkInd range {w.min():.1f}-{w.max():.1f}")
        if not (w.between(1, 20).mean() > 0.99):
            fails.append("NatWalkInd outside its documented 1-20 range")
        if (df["TotPop"].fillna(0) < 0).any():
            fails.append("negative TotPop")
        return Report(self.source_id, not fails, checks, fails)

    def provenance(self) -> Provenance:
        return Provenance("epa_sld", "EPA Smart Location Database v3.0",
                          "SmartLocationDatabase MapServer", tuple(FIELDS),
                          "block group (2010)", "2021-06 (SLD v3.0)",
                          "reach_walkability_v1", "measured")
