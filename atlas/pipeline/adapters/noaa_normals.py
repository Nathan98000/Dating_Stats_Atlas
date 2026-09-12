"""NOAA NCEI U.S. Climate Normals 1991-2020, daily files — pleasant-day
counts per metro.

Deviation from the §6 source list, recorded: the proposal named GHCN-Daily;
this uses the 1991-2020 *Normals* daily product instead (documented in the
registry), which is the same station network already reduced to 30-year
daily normals — materially lighter than processing raw GHCN-Daily and the
right object for a climatological pleasant-day count.

Station -> metro: nearest station (haversine) to any of the metro's
CENTRAL-county internal points, requiring >=350 days of non-missing
TMAX/TMIN normals; up to 8 candidates tried per metro. County internal
points come from Census TIGERweb (the Gazetteer's yearly files are no
longer published on www2 — TIGERweb is the Census-operated equivalent and
carries the CT planning regions this build's delineation needs).

Pleasant day (registry-owned definition): TMAX normal in [55, 85] F and
TMIN normal >= 40 F.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import requests

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.fetch import fetch

INV_URL = "https://www.ncei.noaa.gov/data/normals-daily/1991-2020/doc/inventory_30yr.txt"
DAILY_URL = "https://www.ncei.noaa.gov/data/normals-daily/1991-2020/access/{sid}.csv"
TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer")
UA = {"User-Agent": "DatingStatsAtlas-phase2/0.1 (research pipeline)"}

PLEASANT_TMAX = (55.0, 85.0)
PLEASANT_TMIN_FLOOR = 40.0
MIN_DAYS = 350
MAX_CANDIDATES = 8


def county_internal_points() -> pd.DataFrame:
    """GEOID, lat, lon for every county-equivalent, from the TIGERweb layer
    that includes CT planning regions (asserted)."""
    layers = requests.get(f"{TIGERWEB}?f=pjson", headers=UA, timeout=60).json()
    for lyr in layers.get("layers", []):
        rows, offset = [], 0
        while True:
            r = requests.get(f"{TIGERWEB}/{lyr['id']}/query", headers=UA,
                             timeout=120,
                             params={"where": "1=1",
                                     "outFields": "GEOID,INTPTLAT,INTPTLON",
                                     "returnGeometry": "false", "f": "json",
                                     "orderByFields": "GEOID",
                                     "resultOffset": offset,
                                     "resultRecordCount": 2000})
            d = r.json()
            if "error" in d or not d.get("features"):
                break
            rows.extend(f["attributes"] for f in d["features"])
            if not d.get("exceededTransferLimit") and len(d["features"]) < 2000:
                break
            offset += len(d["features"])
        if not rows:
            continue
        df = pd.DataFrame(rows)
        geoids = set(df["GEOID"])
        if "09110" in geoids and len(df) > 3000:   # CT planning regions present
            df["lat"] = pd.to_numeric(df["INTPTLAT"])
            df["lon"] = pd.to_numeric(df["INTPTLON"])
            return df[["GEOID", "lat", "lon"]]
    raise RuntimeError("no TIGERweb county layer with CT planning regions found")


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


class NoaaNormalsAdapter:
    source_id = "noaa_normals"
    vintage = "U.S. Climate Normals 1991-2020 (daily)"
    license = LICENSES["noaa_normals"]
    requested_variables = ["DLY-TMAX-NORMAL", "DLY-TMIN-NORMAL"]

    def fetch(self) -> RawBundle:
        return RawBundle(self.source_id, [fetch(INV_URL)])

    def stations(self, raw: RawBundle) -> pd.DataFrame:
        rows = []
        for line in raw.paths[0].read_text().splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                rows.append({"sid": parts[0], "lat": float(parts[1]),
                             "lon": float(parts[2])})
            except ValueError:
                continue
        return pd.DataFrame(rows)

    def pleasant_days(self, sid: str) -> tuple[float | None, int]:
        """(pleasant-day count scaled to 365, non-missing days) or (None, n)."""
        try:
            path = fetch(DAILY_URL.format(sid=sid))
        except Exception:
            return None, 0
        df = pd.read_csv(path, low_memory=False)
        if not {"DLY-TMAX-NORMAL", "DLY-TMIN-NORMAL"} <= set(df.columns):
            return None, 0
        tmax = pd.to_numeric(df["DLY-TMAX-NORMAL"], errors="coerce")
        tmin = pd.to_numeric(df["DLY-TMIN-NORMAL"], errors="coerce")
        ok = tmax.notna() & tmin.notna() & tmax.between(-40, 135) & tmin.between(-60, 110)
        n = int(ok.sum())
        if n < MIN_DAYS:
            return None, n
        pleasant = (tmax.between(*PLEASANT_TMAX) & (tmin >= PLEASANT_TMIN_FLOOR) & ok)
        return float(pleasant.sum()) * 365.0 / n, n

    def metro_pleasant_days(self, central_counties: pd.DataFrame) -> pd.DataFrame:
        """central_counties: columns cbsa, county5. Returns cbsa, pleasant_days,
        station id, distance km, and the fallback rank used."""
        pts = county_internal_points()
        cc = central_counties.merge(pts, left_on="county5", right_on="GEOID")
        assert len(cc) > 0.95 * len(central_counties), (
            "county internal points missing for too many central counties")
        inv = self.stations(self.fetch())
        out, cache = [], {}
        for cbsa, grp in cc.groupby("cbsa"):
            d = None
            for _, county in grp.iterrows():
                dist = _haversine_km(county["lat"], county["lon"],
                                     inv["lat"].to_numpy(), inv["lon"].to_numpy())
                order = np.argsort(dist)[:MAX_CANDIDATES]
                for rank, j in enumerate(order):
                    sid = inv.iloc[int(j)]["sid"]
                    if sid not in cache:
                        cache[sid] = self.pleasant_days(sid)
                    val, n = cache[sid]
                    if val is not None:
                        cand = {"cbsa": cbsa, "pleasant_days": val,
                                "station": sid, "station_km": float(dist[j]),
                                "station_rank": rank, "station_days": n}
                        if d is None or cand["station_km"] < d["station_km"]:
                            d = cand
                        break
            out.append(d or {"cbsa": cbsa, "pleasant_days": None, "station": None,
                             "station_km": None, "station_rank": None,
                             "station_days": 0})
        return pd.DataFrame(out)

    def validate(self, raw: RawBundle) -> Report:
        inv = self.stations(raw)
        checks, fails = [f"{len(inv):,} stations in 1991-2020 daily inventory"], []
        if not (10_000 < len(inv) < 30_000):
            fails.append(f"unexpected inventory size {len(inv):,}")
        return Report(self.source_id, not fails, checks, fails)

    def provenance(self) -> Provenance:
        return Provenance("noaa_normals", "NCEI U.S. Climate Normals 1991-2020",
                          "normals-daily access CSVs",
                          tuple(self.requested_variables),
                          "station -> cbsa (nearest central-county internal point)",
                          "1991-2020", "lifestyle_pleasant_days_v1", "measured")
