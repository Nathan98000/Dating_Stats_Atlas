"""FBI Crime Data Explorer — metro-level offence rates with reporting
coverage (Phase 2d item 5). Context only, never scored (D01).

The FBI publishes no metro-level table in the NIBRS era, so this adapter
builds the aggregation itself and keeps the two fatal traps in view:

  1. THE DENOMINATOR IS THE COVERED POPULATION. Each metro's rates divide
     summed offences by the population of the agencies that reported a
     full year — never by the metro's whole population, which would
     understate every rate by exactly the coverage gap.
  2. THE REPORTING PANEL DIFFERS BY METRO AND YEAR. Coverage — the share
     of the metro's agency-covered population living in agencies that
     reported a full year — ships beside the rates, and a metro below the
     registry floor shows the blank state instead of a figure.

Full-year test: an agency-year counts only if all 12 months carry
submitted data (a non-reporting month arrives as null) in BOTH offence
categories, AND the counts pass the transition-junk rule: during the
2021+ NIBRS cutover some large agencies' partial submissions were
accepted as tiny month totals (New York City 2021 shows twelve numeric
months summing to a violent rate under 2 per 100k). An agency-year above
the registry's population bar whose violent AND property rates both sit
below the registry's implausibility bars is excluded as not-really-
reporting, and every exclusion is named in the build report.

Geography: the roster maps each ORI to its county name; county name ->
FIPS via the pinned delineation (suffix-and-space-insensitive). Agencies
whose county is NOT SPECIFIED, unmatched, or in Connecticut (the CDE
speaks old counties; the delineation speaks planning regions) fall back
to the nearest county internal point to the agency's coordinates within
its state — counted and reported.

The API key (repo root, gitignored) is read like the Census key and never
logged: cached responses are stored under data/raw/fbi_cde keyed by the
keyless path, and the fetch log records keyless paths only.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.pipeline.adapters.base import LICENSES
from atlas.pipeline.contracts.provenance import Provenance
from atlas.pipeline.fetch import DATA, REPO

API_BASE = "https://api.usa.gov/crime/fbi/cde"
CACHE = DATA / "raw" / "fbi_cde"
KEY_FILE = REPO / "FBI Crime Data API Key.txt"

YEARS = (2021, 2025)
OFFENSES = ("violent-crime", "property-crime")
STATES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA",
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
          "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
          "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
          "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

_local = threading.local()


def cde_api_key() -> str:
    key = os.environ.get("FBI_CDE_API_KEY", "").strip()
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
    if not key:
        raise RuntimeError(
            "No FBI CDE key: set FBI_CDE_API_KEY or create "
            "'FBI Crime Data API Key.txt' at the repo root")
    return key


def _get_json(path: str, max_tries: int = 6) -> dict:
    """GET {API_BASE}/{path}, cached under data/raw/fbi_cde by the KEYLESS
    path so the key never lands on disk or in any manifest."""
    cache_file = CACHE / (hashlib.sha256(path.encode()).hexdigest()[:20] + ".json.gz")
    if cache_file.exists():
        with gzip.open(cache_file, "rt") as f:
            return json.load(f)
    sep = "&" if "?" in path else "?"
    url = f"{API_BASE}/{path}{sep}API_KEY={cde_api_key()}"
    last = None
    for attempt in range(max_tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                d = json.load(r)
            CACHE.mkdir(parents=True, exist_ok=True)
            tmp = cache_file.with_suffix(".part")
            with gzip.open(tmp, "wt") as f:
                json.dump(d, f)
            os.replace(tmp, cache_file)
            return d
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 404:
                raise
            time.sleep(min(60.0, (2.0 ** attempt) * (2 if e.code == 429 else 1)))
        except Exception as e:  # noqa: PERF203
            last = str(e)[:120]
            time.sleep(2.0 ** attempt)
    raise RuntimeError(f"CDE request failed for {path}: {last}")


def norm_county(name: str) -> str:
    """Suffix-and-space-insensitive county key: 'De Kalb County' ->
    'DEKALB', 'Richmond city' -> 'RICHMONDCITY' (the CITY suffix is
    meaningful — Virginia has both a Richmond County and a Richmond
    city)."""
    n = name.upper().replace(".", "").replace("'", "")
    n = "".join(n.split())
    for suffix in ("COUNTY", "PARISH", "BOROUGH", "CENSUSAREA",
                   "MUNICIPALITY", "MUNICIPIO", "CITYANDBOROUGH"):
        if n.endswith(suffix) and n != suffix:
            n = n[: -len(suffix)]
            break
    return n


class FbiCdeAdapter:
    source_id = "fbi_cde"
    vintage = "FBI Crime Data Explorer, summarized agency data"
    license = LICENSES["fbi_cde"]
    requested_variables = ["violent-crime", "property-crime"]

    def roster(self) -> pd.DataFrame:
        """Every agency in the 50 states + DC: ori, county name (the
        roster's own assignment), type, coordinates."""
        rows = []
        for st in STATES:
            d = _get_json(f"agency/byStateAbbr/{st}")
            for county_key, agencies in d.items():
                for a in agencies:
                    rows.append({
                        "ori": a["ori"], "state": a["state_abbr"],
                        "county_key": county_key,
                        "counties": a.get("counties") or "",
                        "agency_name": a.get("agency_name") or "",
                        "agency_type": a.get("agency_type_name") or "",
                        "lat": a.get("latitude"), "lon": a.get("longitude"),
                    })
        df = pd.DataFrame(rows)
        # an agency serving several counties appears under each county key;
        # its own `counties` field lists them with the primary first
        df["primary_county"] = np.where(
            df["counties"].str.strip().isin(("", "NOT SPECIFIED")),
            df["county_key"],
            df["counties"].str.split(",").str[0].str.strip())
        df = df.sort_values(["ori", "county_key"]).drop_duplicates("ori")
        return df.reset_index(drop=True)

    def monthly(self, ori: str, offense: str) -> dict | None:
        """One agency-offense pull for the whole YEARS span: monthly
        actuals for the agency's own series (null = not submitted) and its
        population by year. None when CDE has no series for the agency."""
        d = _get_json(f"summarized/agency/{ori}/{offense}"
                      f"?from=01-{YEARS[0]}&to=12-{YEARS[1]}")
        actuals = d.get("offenses", {}).get("actuals", {})
        series_key = next((k for k in actuals if k.endswith(" Offenses")),
                          None)
        if series_key is None:
            return None
        series = actuals[series_key]
        # the population series keyed by the AGENCY'S OWN NAME — the same
        # name its actuals series carries. The response also carries the
        # state's and the nation's series, and the state must never be
        # mistaken for the agency (the first aggregation did exactly
        # that, handing every agency its state population and flagging
        # two-thirds of all agency-years as implausible).
        agency_name = series_key[: -len(" Offenses")]
        pops = d.get("populations", {}).get("population", {})
        pop_series = pops.get(agency_name, {})
        pop_by_year: dict[str, float] = {}
        for mk, v in pop_series.items():
            y = mk.split("-")[1]
            if v is not None:
                pop_by_year[y] = max(pop_by_year.get(y, 0.0), float(v))
        months = {}
        for y in range(YEARS[0], YEARS[1] + 1):
            vals = [series.get(f"{m:02d}-{y}") for m in range(1, 13)]
            months[str(y)] = vals
        return {"months": months, "pop_by_year": pop_by_year}

    def provenance(self) -> Provenance:
        return Provenance(
            "fbi_cde", "FBI Crime Data Explorer",
            "summarized agency offences (agency -> county -> cbsa)",
            tuple(self.requested_variables),
            "agency -> cbsa via ORI county and the pinned delineation",
            f"{YEARS[0]}-{YEARS[1]}", "crime_rates_v1", "context")
