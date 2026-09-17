"""Principal-city internal points for every metro (Phase 2d).

Why: the Phase 2a-2c anchor — the mean of a metro's CENTRAL-county
internal points — is fine for compact Eastern counties and wrong by up to
130 km in the huge Western ones (Washoe County's point sits in the desert
an hour north of Reno). That mis-anchored the weather-station matching
(Reno's nearest qualifying station "for the metro" was 118 km away), the
locator-map dots and the drive-time phrases in the city descriptions.

Source: TIGERweb Places (Incorporated Places + Census Designated Places),
matched by the CBSA title's principal-city name within the metro's first
state. A metro whose title doesn't resolve to a place (consolidated
governments like Louisville/Jefferson County, hyphen-named cities the
split misses) falls back to the county anchor — those are compact-county
metros where the old anchor was already fine.

One guard the first run earned: a place's own internal point can be
degenerate — San Francisco's includes the Farallon Islands, which drag
the point 50 km into the Pacific. A place point with no weather station
within GUARD_KM (stations sit where people live; open water and empty
range have none) is rejected in favour of the county anchor, and the
anchor column says which one each metro got. Output is cached at
results/phase2d/city_points.csv.
"""
from __future__ import annotations

import time

import pandas as pd
import requests

from atlas.pipeline.adapters.noaa_normals import UA, county_internal_points
from atlas.pipeline.fetch import RESULTS

TIGERWEB_PLACES = ("https://tigerweb.geo.census.gov/arcgis/rest/services/"
                   "TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer")
OUT = RESULTS / "phase2d" / "city_points.csv"
GUARD_KM = 20.0
SANITY_KM = 150.0   # Reno's genuine place-to-county gap is 133 km

ABBR_TO_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56"}


def _place_layers() -> list[int]:
    r = requests.get(f"{TIGERWEB_PLACES}?f=pjson", headers=UA, timeout=60)
    layers = r.json().get("layers", [])
    ids = [lyr["id"] for lyr in layers
           if lyr["name"] in ("Incorporated Places",
                              "Census Designated Places")]
    assert ids, f"no place layers found among {[l['name'] for l in layers]}"
    return ids


def _lookup(layers: list[int], name: str, state_fips: str) -> tuple | None:
    esc = name.replace("'", "''")
    for lyr in layers:
        r = requests.get(
            f"{TIGERWEB_PLACES}/{lyr}/query", headers=UA, timeout=60,
            params={"where": f"BASENAME='{esc}' AND STATE='{state_fips}'",
                    "outFields": "BASENAME,STATE,INTPTLAT,INTPTLON",
                    "returnGeometry": "false", "f": "json"})
        feats = r.json().get("features", [])
        if feats:
            a = feats[0]["attributes"]
            return float(a["INTPTLAT"]), float(a["INTPTLON"])
    return None


def principal_city_points(force: bool = False) -> pd.DataFrame:
    """cbsa, lat, lon, anchor ('place' | 'county'); cached to CSV."""
    if OUT.exists() and not force:
        return pd.read_csv(OUT, dtype={"cbsa": str})
    metros = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})
    from atlas.pipeline.adapters.census import DelineationAdapter
    delin = DelineationAdapter().normalize(DelineationAdapter().fetch())
    central = delin[(delin["Central/Outlying County"] == "Central")
                    & delin["cbsa"].isin(set(metros["cbsa"]))]
    pts = county_internal_points()
    cc = central.merge(pts, left_on="county5", right_on="GEOID")
    county_anchor = cc.groupby("cbsa")[["lat", "lon"]].mean()

    # the degenerate-point guard's "is anything here" proxy: the GHCN
    # station inventory (lazy import — the weather adapter imports this
    # module at function level, so there is no cycle at module load)
    from atlas.pipeline.adapters.ghcn_daily import GhcnDailyAdapter
    from atlas.pipeline.adapters.noaa_normals import _haversine_km
    inv = GhcnDailyAdapter().stations(GhcnDailyAdapter().fetch())
    inv_lat, inv_lon = inv["lat"].to_numpy(), inv["lon"].to_numpy()

    layers = _place_layers()
    rows = []
    for _, m in metros.iterrows():
        title = m["cbsa_title"]
        city_part, state_part = title.rsplit(",", 1)
        state = state_part.strip().split("-")[0]
        fips = ABBR_TO_FIPS[state]
        # Candidate order (Phase 2e finding): the natural short name
        # first — "Lexington" before the consolidated government's legal
        # "Lexington-Fayette" — then the whole first segment, which is
        # what saves a hyphenated real city name ("Winston-Salem") whose
        # short split ("Winston") is no place at all. Double hyphens are
        # the delineation's own separator; "/" carries consolidations.
        # Every candidate must sit within SANITY_KM of the metro's own
        # county anchor, so a same-named town elsewhere in the state can
        # never hijack the metro.
        seg = city_part.split(",")[0].strip()
        candidates = [seg.split("-")[0].strip(),
                      seg.split("--")[0].strip(),
                      seg.split("/")[0].strip(),
                      seg]
        ca = county_anchor.loc[m["cbsa"]]
        got, matched = None, None
        for cand in dict.fromkeys(candidates):
            pt = _lookup(layers, cand, fips)
            if pt:
                far = float(_haversine_km(pt[0], pt[1],
                                          float(ca["lat"]), float(ca["lon"])))
                near_station = float(_haversine_km(
                    pt[0], pt[1], inv_lat, inv_lon).min())
                if far <= SANITY_KM and near_station <= GUARD_KM:
                    got, matched = pt, cand
                    break
            time.sleep(0.05)
        if got:
            rows.append({"cbsa": m["cbsa"], "lat": got[0], "lon": got[1],
                         "anchor": "place", "place_name": matched})
        else:
            rows.append({"cbsa": m["cbsa"], "lat": float(ca["lat"]),
                         "lon": float(ca["lon"]), "anchor": "county",
                         "place_name": None})
    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    n_place = int((df["anchor"] == "place").sum())
    print(f"city points: {n_place}/{len(df)} metros anchored at their "
          f"principal city; the rest keep the county anchor")
    return df


if __name__ == "__main__":
    principal_city_points(force=True)
