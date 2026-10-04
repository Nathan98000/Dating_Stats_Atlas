"""GHCN-Daily 1991-2020 — pleasant-day counts per metro from ACTUAL daily
observations, replacing the Normals-based count (Phase 2d item 11).

Why the switch back: §6 specified GHCN-Daily; Phase 2a substituted the
30-year daily *Normals* (recorded deviation) — and Normals average away the
day-to-day variation the statistic exists to count. Any city whose AVERAGE
day sits inside the thresholds scores every day of the year: San
Francisco's normal highs sit in the high-50s-to-60s band all year, so it
served 365. Computed on real days, a cold snap, a heat wave or a rainy day
fails the test on the day it happens.

Definition (registry-owned, every threshold; Phase 4e, Nathan's rule,
m4.2.0): a nice day meets ALL of — the day's average temperature, taken as
(TMAX + TMIN) / 2 because GHCN's TAVG is often missing, between
tavg_f[0] and tavg_f[1] inclusive; TMAX below tmax_below_f; TMIN above
tmin_above_f; PRCP at most prcp_max_in (no more than a light shower); SNOW
at most snow_max_in (none measurable); SNWD below snwd_max_in (no deep
snow cover). Many stations do not report snow: a day with no SNOW or SNWD
value counts as snow-free (with the low above 45°F, snow is effectively
impossible), and which days had snow data is counted, not assumed. Station
eligibility and the completeness policy are unchanged — a valid day needs
TMAX, TMIN and PRCP. (m2.1.0-m4.1.1: TMAX in [55, 85], TMIN >= 40, PRCP
<= 0.1.) Per station: count pleasant
days per calendar year over 1991-2020, scale each year by 365/valid-days
(a missing reading is unknown, not un-nice), require MIN_DAYS_PER_YEAR
valid days for a year to count and MIN_YEARS qualifying years for the
station to count, then average across qualifying years.

Station -> metro: nearest qualifying station (haversine) to any of the
metro's central-county internal points, up to MAX_CANDIDATES tried — the
same matching the Normals adapter used, with a larger candidate list
because daily completeness is a harder test than a published normal.

Also computed per metro, for the validation suite's sanity assertions
(never served): mean annual precipitation and mean winter (Dec-Feb) TMIN.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.adapters.noaa_normals import _haversine_km
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.fetch import fetch
from atlas.pipeline.registry.loader import load_registry

INV_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt"
DAILY_URL = ("https://www.ncei.noaa.gov/access/services/data/v1"
             "?dataset=daily-summaries&stations={sid}"
             "&startDate=1991-01-01&endDate=2020-12-31"
             "&dataTypes=TMAX,TMIN,PRCP,SNOW,SNWD&format=csv&units=standard")

YEARS = (1991, 2020)
MIN_DAYS_PER_YEAR = 330      # a year with fewer valid days is not counted
MIN_YEARS = 25               # a station with fewer qualifying years fails
MAX_CANDIDATES = 24
# GHCN network code (3rd character of a US station id) — SNOTEL ('S')
# stations are mountain snow-monitoring sites, systematically colder and
# wetter than the metro whose county they sit in: the first run matched
# nine metros to SNOTEL (Boulder to a ridge site that scored 39 nice
# days). COOP ('C'), WBAN/airport ('W') and CRN ('R') stations measure
# where people live.
ALLOWED_NETWORKS = ("C", "W", "R")
# Phase 4 (ADR 0012, Nathan's decision): US weather stations only. A GHCN
# id's first two characters are its country code; the filter above only
# ever looked at US ids, so a station across a border could win — the
# first audit found Detroit matched to Windsor, Ontario (CA006139520).
US_STATION_PREFIX = "US"


# plausible ranges for the snow fields (inches): a reading outside them is
# a data error and is treated as no reading (snow-free), and counted
SNOW_RANGE = (0.0, 100.0)
SNWD_RANGE = (0.0, 500.0)


def nice_day_parts(tmax: pd.Series, tmin: pd.Series, prcp: pd.Series,
                   snow: pd.Series, snwd: pd.Series, rule: dict) -> dict[str, pd.Series]:
    """The nice-day rule, criterion by criterion, on daily values in GHCN's
    standard units (°F, inches). Each part is True where the day passes it;
    `nice` is all of them. Missing SNOW or SNWD passes its part (snow-free);
    a missing temperature or rain reading fails (the day is then not valid,
    which the caller decides). The average is (TMAX + TMIN) / 2."""
    lo, hi = rule["tavg_f"]
    tavg = (tmax + tmin) / 2.0
    parts = {
        "tavg": tavg.between(lo, hi),                       # inclusive
        "tmax": tmax < rule["tmax_below_f"],
        "tmin": tmin > rule["tmin_above_f"],
        "prcp": prcp <= rule["prcp_max_in"],
        "snow": snow.isna() | (snow <= rule["snow_max_in"]),
        "snwd": snwd.isna() | (snwd < rule["snwd_max_in"]),
    }
    parts["temp"] = parts["tavg"] & parts["tmax"] & parts["tmin"]
    parts["snow_free"] = parts["snow"] & parts["snwd"]
    parts["nice"] = parts["temp"] & parts["prcp"] & parts["snow_free"]
    return parts


class GhcnDailyAdapter:
    source_id = "ghcn_daily"
    vintage = "GHCN-Daily, observations 1991-2020"
    license = LICENSES["ghcn_daily"]
    requested_variables = ["TMAX", "TMIN", "PRCP", "SNOW", "SNWD"]

    def __init__(self) -> None:
        self.rule = dict(load_registry().pleasant_day)
        self.prcp_max = self.rule["prcp_max_in"]

    def fetch(self) -> RawBundle:
        return RawBundle(self.source_id, [fetch(INV_URL)])

    def stations(self, raw: RawBundle) -> pd.DataFrame:
        """Stations whose TMAX, TMIN and PRCP inventories each span the
        normals period (coarse pre-filter; true completeness is measured
        from the data)."""
        rows = []
        for line in raw.paths[0].read_text().splitlines():
            parts = line.split()
            if len(parts) != 6 or parts[3] not in ("TMAX", "TMIN", "PRCP"):
                continue
            sid = parts[0]
            if not sid.startswith(US_STATION_PREFIX) or sid[2] not in ALLOWED_NETWORKS:
                continue
            rows.append({"sid": sid, "lat": float(parts[1]),
                         "lon": float(parts[2]), "elem": parts[3],
                         "first": int(parts[4]), "last": int(parts[5])})
        df = pd.DataFrame(rows)
        ok = df[(df["first"] <= YEARS[0] + 2) & (df["last"] >= YEARS[1] - 1)]
        counts = ok.groupby("sid")["elem"].nunique()
        full = set(counts[counts == 3].index)
        out = ok[ok["sid"].isin(full)].drop_duplicates("sid")
        return out[["sid", "lat", "lon"]].reset_index(drop=True)

    def station_pleasant(self, sid: str) -> dict | None:
        """Pleasant-day average for one station, or None if it fails the
        completeness bars. Also returns the sanity quantities."""
        try:
            path = fetch(DAILY_URL.format(sid=sid))
            df = pd.read_csv(path, low_memory=False)
        except Exception:
            return None
        if not {"DATE", "TMAX", "TMIN", "PRCP"} <= set(df.columns):
            return None
        d = pd.to_datetime(df["DATE"], errors="coerce")
        tmax = pd.to_numeric(df["TMAX"], errors="coerce")
        tmin = pd.to_numeric(df["TMIN"], errors="coerce")
        prcp = pd.to_numeric(df["PRCP"], errors="coerce")
        # the snow fields: absent columns (a station that never reports
        # snow) and blank cells are no reading; so is an implausible one
        snow_raw = pd.to_numeric(df.get("SNOW", pd.Series(index=df.index, dtype=float)),
                                 errors="coerce")
        snwd_raw = pd.to_numeric(df.get("SNWD", pd.Series(index=df.index, dtype=float)),
                                 errors="coerce")
        snow = snow_raw.where(snow_raw.between(*SNOW_RANGE))
        snwd = snwd_raw.where(snwd_raw.between(*SNWD_RANGE))
        valid = (d.notna() & tmax.notna() & tmin.notna() & prcp.notna()
                 & tmax.between(-40, 135) & tmin.between(-60, 110)
                 & (tmin <= tmax) & prcp.between(0, 30))
        year = d.dt.year
        parts = nice_day_parts(tmax, tmin, prcp, snow, snwd, self.rule)
        pleasant = valid & parts["nice"]
        # counterfactuals for the validation suite and the report: the rule
        # without its rain term, and without its two snow terms
        mild = valid & parts["temp"] & parts["snow_free"]
        no_snow_rule = valid & parts["temp"] & parts["prcp"]
        has_snow_data = snow.notna() | snwd.notna()
        per_year = pd.DataFrame({
            "year": year, "valid": valid, "mild": mild, "pleasant": pleasant,
            "no_snow_rule": no_snow_rule,
            "counted_with_snow_data": pleasant & has_snow_data,
            "excluded_by_snow": no_snow_rule & ~parts["snow_free"],
            "snow_data": valid & has_snow_data,
            "snow_implausible": valid & ((snow_raw.notna() & snow.isna())
                                         | (snwd_raw.notna() & snwd.isna())),
        }).groupby("year").sum()
        per_year = per_year[(per_year.index >= YEARS[0])
                            & (per_year.index <= YEARS[1])]
        qual = per_year[per_year["valid"] >= MIN_DAYS_PER_YEAR]
        if len(qual) < MIN_YEARS:
            return None
        rate = (qual["pleasant"] / qual["valid"] * 365.0).mean()
        # the rain-free counterfactual: the validation suite asserts
        # the rain term only ever REMOVES days, and removes most where wet
        # days are mild ones — that mechanism check replaced a "wettest
        # metro near the bottom" guess the data disproved (drizzle-belt
        # wet days are mostly cold days already excluded by temperature)
        rate_no_rain = (qual["mild"] / qual["valid"] * 365.0).mean()
        rate_no_snow_rule = (qual["no_snow_rule"] / qual["valid"] * 365.0).mean()
        # sanity quantities over the same qualifying years. Both wetness
        # measures ship because they disagree in an instructive way: the
        # most INCHES fall on the warm Gulf coast in bursts that leave
        # plenty of mild dry days; the most RAIN-DAYS is the drizzle belt,
        # which is what actually suppresses nice days — the validation
        # anchor uses rain-days for exactly that reason.
        qy = set(qual.index)
        vy = valid & year.isin(qy)
        precip_annual = float(prcp[vy].groupby(year[vy]).sum().mean())
        wet = vy & (prcp > self.prcp_max)
        rainy = pd.DataFrame({"y": year[vy], "wet": wet[vy],
                              "v": valid[vy]}).groupby("y").sum()
        rainy_days = float((rainy["wet"] / rainy["v"] * 365.0).mean())
        winter = vy & d.dt.month.isin((12, 1, 2))
        winter_tmin = float(tmin[winter].mean()) if winter.any() else np.nan
        return {"pleasant_days": float(rate),
                "pleasant_days_no_rain": float(rate_no_rain),
                "pleasant_days_no_snow_rule": float(rate_no_snow_rule),
                # raw day counts over the qualifying years (the report's
                # snow-data figures; never served)
                "valid_days": int(qual["valid"].sum()),
                "days_counted": int(qual["pleasant"].sum()),
                "days_counted_with_snow_data": int(qual["counted_with_snow_data"].sum()),
                "days_excluded_by_snow": int(qual["excluded_by_snow"].sum()),
                "valid_days_with_snow_data": int(qual["snow_data"].sum()),
                "snow_readings_implausible": int(qual["snow_implausible"].sum()),
                "years_used": int(len(qual)),
                "annual_precip_in": precip_annual,
                "rainy_days": rainy_days,
                "winter_tmin_f": winter_tmin}

    def metro_pleasant_days(self) -> pd.DataFrame:
        """Nearest qualifying station per metro, anchored at the metro's
        PRINCIPAL-CITY internal point (Phase 2d: the old central-county
        anchor sat up to 130 km from the city in the huge Western
        counties, which is exactly where the station match went wrong).
        Candidates in distance order; the first that clears the
        completeness bars wins."""
        from atlas.pipeline.bridge.city_points import principal_city_points
        anchors = principal_city_points()
        inv = self.stations(self.fetch())
        print(f"ghcn: {len(inv):,} stations pass the inventory pre-filter")
        out, cache = [], {}
        for _, a in anchors.iterrows():
            d = None
            dist = _haversine_km(a["lat"], a["lon"],
                                 inv["lat"].to_numpy(), inv["lon"].to_numpy())
            order = np.argsort(dist)[:MAX_CANDIDATES]
            for rank, j in enumerate(order):
                sid = inv.iloc[int(j)]["sid"]
                if sid not in cache:
                    cache[sid] = self.station_pleasant(sid)
                val = cache[sid]
                if val is not None:
                    d = {"cbsa": a["cbsa"], "station": sid,
                         "station_km": float(dist[j]),
                         "station_rank": rank, "anchor": a["anchor"], **val}
                    break
            out.append(d or {"cbsa": a["cbsa"], "pleasant_days": None,
                             "pleasant_days_no_rain": None,
                             "pleasant_days_no_snow_rule": None,
                             "valid_days": 0, "days_counted": 0,
                             "days_counted_with_snow_data": 0,
                             "days_excluded_by_snow": 0,
                             "valid_days_with_snow_data": 0,
                             "snow_readings_implausible": 0,
                             "station": None, "station_km": None,
                             "station_rank": None, "anchor": a["anchor"],
                             "years_used": 0, "annual_precip_in": None,
                             "rainy_days": None, "winter_tmin_f": None})
        return pd.DataFrame(out)

    def validate(self, raw: RawBundle) -> Report:
        inv = self.stations(raw)
        checks = [f"{len(inv):,} stations span 1991-2020 for TMAX+TMIN+PRCP"]
        fails = []
        if not (2_000 < len(inv) < 30_000):
            fails.append(f"unexpected qualifying-station count {len(inv):,}")
        return Report(self.source_id, not fails, checks, fails)

    def provenance(self) -> Provenance:
        return Provenance("ghcn_daily", "NOAA GHCN-Daily",
                          "daily-summaries access CSVs (TMAX, TMIN, PRCP, SNOW, SNWD)",
                          tuple(self.requested_variables),
                          "station -> cbsa (nearest central-county internal point)",
                          "1991-2020", "lifestyle_pleasant_days_v3", "measured")
