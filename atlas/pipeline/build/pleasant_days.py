"""Recompute pleasant days from GHCN-Daily observations (Phase 2d item 11)
into results/phase2d/pleasant_days_ghcn.csv. Standalone so the long fetch
can run once and be diffed against the Normals values before the feature
matrix is rebuilt; build.features consumes the CSV.
"""
from __future__ import annotations

import json

import pandas as pd

from atlas.pipeline.adapters.ghcn_daily import GhcnDailyAdapter
from atlas.pipeline.fetch import RESULTS
from atlas.pipeline.registry.loader import load_registry

P2D = RESULTS / "phase2d"


def build() -> None:
    P2D.mkdir(parents=True, exist_ok=True)
    ad = GhcnDailyAdapter()
    rep = ad.validate(ad.fetch())
    assert rep.passed, rep.failures
    nd = ad.metro_pleasant_days()
    nd.to_csv(P2D / "pleasant_days_ghcn.csv", index=False)

    old = pd.read_csv(RESULTS / "phase2" / "static_features.csv",
                      dtype={"cbsa": str})[["cbsa", "pleasant_days"]]
    cmp = nd.merge(old.rename(columns={"pleasant_days": "normals_value"}),
                   on="cbsa")
    summary = {
        "metros": len(nd),
        "metros_without_station": sorted(nd[nd["pleasant_days"].isna()]["cbsa"]),
        "median_station_km": float(nd["station_km"].median()),
        "p95_station_km": float(nd["station_km"].quantile(0.95)),
        "fallback_rank_gt0": int((nd["station_rank"].fillna(0) > 0).sum()),
        "max": float(nd["pleasant_days"].max()),
        "min": float(nd["pleasant_days"].min()),
        "median": float(nd["pleasant_days"].median()),
        "median_abs_change_vs_normals": float(
            (cmp["pleasant_days"] - cmp["normals_value"]).abs().median()),
        "at_365_normals": int((cmp["normals_value"] >= 364.5).sum()),
        "at_365_ghcn": int((cmp["pleasant_days"] >= 364.5).sum()),
        # Phase 4e (the snow terms): over the metros' chosen stations and
        # their qualifying years, how many counted days had a snow reading,
        # and how many days the two snow terms excluded (days passing every
        # other criterion); a missing SNOW/SNWD reading counts as snow-free
        "definition": load_registry().pleasant_day,
        "snow": {
            "days_counted": int(nd["days_counted"].sum()),
            "days_counted_with_snow_data": int(nd["days_counted_with_snow_data"].sum()),
            "days_excluded_by_snow": int(nd["days_excluded_by_snow"].sum()),
            "valid_days": int(nd["valid_days"].sum()),
            "valid_days_with_snow_data": int(nd["valid_days_with_snow_data"].sum()),
            "snow_readings_implausible": int(nd["snow_readings_implausible"].sum()),
            "stations_with_no_snow_data": int((nd["station"].notna()
                                               & (nd["valid_days_with_snow_data"] == 0)).sum()),
            "metros_losing_a_day_or_more_to_snow": int(
                ((nd["pleasant_days_no_snow_rule"] - nd["pleasant_days"]) >= 1).sum()),
            "max_days_a_year_removed_by_snow": [
                nd.loc[(nd["pleasant_days_no_snow_rule"] - nd["pleasant_days"]).idxmax(), "cbsa"],
                round(float((nd["pleasant_days_no_snow_rule"] - nd["pleasant_days"]).max()), 2)],
        },
    }
    (P2D / "pleasant_days_report.json").write_text(
        json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"-> {P2D / 'pleasant_days_ghcn.csv'}")


if __name__ == "__main__":
    build()
