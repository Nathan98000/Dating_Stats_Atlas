"""City display names, slugs and the one-line description (ADR 0004).

The v3 city page opens with "Provo, Utah" and one plain line — "A college
town of about 700,000 people an hour south of Salt Lake City." Nothing
hand-written and no model call: the line is composed from data the build
already holds — population, adult population, state, student share, and
the distance/bearing to the nearest larger metro — with every template,
threshold and phrase in the feature registry. The deferred build-time
narratives replace it later.

Metro points are the mean of each metro's CENTRAL-county internal points
(Census TIGERweb, the same cached layer the climate join used). Distance
is great-circle miles spoken as drive time at ~50 mph — deliberately
coarse ("an hour south of Salt Lake City"), never printed as a number.

Display names: list rows use "Provo, UT"; the city page uses "Provo,
Utah" (first principal city + first state, per the boards). Slugs are
"provo-utah", asserted unique — routes carry them so no CBSA code ever
reaches a page.

Output: results/phase2c/city_meta.csv (cbsa, display_name,
display_name_full, slug, state_full, lat, lon, description).
"""
from __future__ import annotations

import math
import re

import pandas as pd

from atlas.pipeline.adapters.census import DelineationAdapter
from atlas.pipeline.adapters.noaa_normals import county_internal_points
from atlas.pipeline.fetch import RESULTS
from atlas.pipeline.registry.loader import load_registry

P2C = RESULTS / "phase2c"

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "the District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}
DIRECTIONS = ["north", "northeast", "east", "southeast",
              "south", "southwest", "west", "northwest"]
# a "larger" neighbour is meaningfully larger, not a peer
LARGER_FACTOR = 1.5
LARGER_MIN_POP = 400_000


def first_city(title: str) -> str:
    name = title.rpartition(", ")[0]
    city = re.split(r"[-–—]", name)[0].strip()
    # the delineation's "Urban Honolulu" is a Census legalism, not a name
    return re.sub(r"^Urban ", "", city)


def first_state(title: str) -> str:
    states = title.rpartition(", ")[2]
    return states.split("-")[0].strip()


def slugify(*parts: str) -> str:
    s = "-".join(parts).lower()
    s = re.sub(r"[''.]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing_word(lat_from, lon_from, lat_to, lon_to) -> str:
    """Compass word for the direction of (to) as seen from (from)."""
    p1, p2 = math.radians(lat_from), math.radians(lat_to)
    dl = math.radians(lon_to - lon_from)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    brg = (math.degrees(math.atan2(y, x)) + 360) % 360
    return DIRECTIONS[int(((brg + 22.5) % 360) // 45)]


def round_pop(pop: float) -> str:
    """Spoken population: 700,000 not 749,183; 1.3 million not 1,281,004."""
    if pop >= 950_000:
        m = round(pop / 1_000_000, 1)
        m_txt = f"{m:.0f}" if float(m).is_integer() else f"{m:.1f}"
        return f"{m_txt} million"
    if pop >= 95_000:
        return f"{round(pop / 50_000) * 50_000:,.0f}"
    return f"{round(pop / 10_000) * 10_000:,.0f}"


def _character(reg, pop: float, students_per_1k: float | None) -> str:
    for rule in reg.city_description["characters"]:
        kind = rule["rule"] if "rule" in rule else "default"
        if kind == "students_per_1k_at_least":
            if students_per_1k is not None and students_per_1k >= rule["value"]:
                return rule["text"]
        elif kind == "pop_at_least":
            if pop >= rule["value"]:
                return rule["text"]
        elif kind == "default":
            return rule["text"]
    return "A city"


def _drive_phrase(reg, miles: float) -> str | None:
    minutes = miles / 50.0 * 60.0
    for step in reg.city_description["drive_phrases"]:
        if minutes <= step["max_minutes"]:
            return step["text"]
    return None


def build() -> pd.DataFrame:
    P2C.mkdir(parents=True, exist_ok=True)
    reg = load_registry()
    metros = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})
    quality = pd.read_csv(RESULTS / "phase1" / "metro_quality.csv",
                          dtype={"cbsa": str})
    statics = pd.read_csv(RESULTS / "phase2" / "static_features.csv",
                          dtype={"cbsa": str})
    df = (metros[["cbsa", "cbsa_title", "states"]]
          .merge(quality[["cbsa", "pop_total"]], on="cbsa")
          .merge(statics[["cbsa", "students_per_1k_adults"]], on="cbsa",
                 how="left"))

    # metro point = mean of central-county internal points (cached TIGERweb)
    delin_ad = DelineationAdapter()
    delin = delin_ad.normalize(delin_ad.fetch())
    central = delin[delin["Central/Outlying County"] == "Central"]
    pts = county_internal_points()
    cc = central.merge(pts, left_on="county5", right_on="GEOID", how="left")
    metro_pts = cc.groupby("cbsa")[["lat", "lon"]].mean()
    df = df.merge(metro_pts, left_on="cbsa", right_index=True, how="left")
    assert df["lat"].notna().all(), (
        "a metro has no central-county internal point — the description "
        "build cannot place it")

    df["city"] = df["cbsa_title"].map(first_city)
    df["st"] = df["cbsa_title"].map(first_state)
    df["state_full"] = df["st"].map(STATE_NAMES)
    assert df["state_full"].notna().all(), (
        f"unmapped state code: {sorted(df[df['state_full'].isna()]['st'])}")
    df["display_name"] = df["city"] + ", " + df["st"]
    df["display_name_full"] = df["city"] + ", " + df["state_full"]
    df["slug"] = [slugify(c, s) for c, s in zip(df["city"], df["state_full"])]
    dupes = df[df["slug"].duplicated(keep=False)]
    assert dupes.empty, f"slug collisions: {dupes[['slug', 'cbsa']].values}"

    rows = df.reset_index(drop=True)
    lines = []
    for i, r in rows.iterrows():
        character = _character(reg, r["pop_total"],
                               r.get("students_per_1k_adults"))
        pop_txt = round_pop(float(r["pop_total"]))
        # nearest meaningfully-larger metro within spoken driving distance
        location = None
        cand = rows[(rows["pop_total"] >= max(LARGER_MIN_POP,
                                              r["pop_total"] * LARGER_FACTOR))
                    & (rows["cbsa"] != r["cbsa"])]
        if len(cand):
            d = cand.apply(lambda c: haversine_miles(
                r["lat"], r["lon"], c["lat"], c["lon"]), axis=1)
            j = d.idxmin()
            drive = _drive_phrase(reg, float(d[j]))
            if drive is not None:
                direction = bearing_word(rows.at[j, "lat"], rows.at[j, "lon"],
                                         r["lat"], r["lon"])
                location = reg.city_description["location_near"].format(
                    drive=drive, direction=direction,
                    city=rows.at[j, "city"])
        if location is None:
            location = reg.city_description["location_far"].format(
                state=r["state_full"])
        lines.append(reg.city_description["template"].format(
            character=character, pop=pop_txt, location=location))
    rows["description"] = lines

    out = rows[["cbsa", "display_name", "display_name_full", "slug",
                "state_full", "lat", "lon", "description"]]
    out.to_csv(P2C / "city_meta.csv", index=False)
    print(f"city meta -> {P2C / 'city_meta.csv'} ({len(out)} metros)")
    print("sample:", out.iloc[0]["display_name_full"], "—",
          out.iloc[0]["description"])
    return out


if __name__ == "__main__":
    build()
