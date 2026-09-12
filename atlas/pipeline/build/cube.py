"""Build the serving artifact: dense cubes over
[metro, sex, age, marital, education, income, race_eth], plus per-metro
variance coefficients, features and a manifest that pins everything.

The axis ordering and level coding are a versioned contract (SCHEMA below);
the API refuses to load a build whose manifest disagrees with the schema it
was compiled against, and validates cube shapes against the manifest.

Universe: ages 18-70, institutional GQ excluded (the pool universe).
Cubes:
    pool_cube.npy    float32  sum of PWGTP * a_eff        (weighted persons)
    count_cube.npy   float32  sum of a_eff                (allocated respondents
                              — fractional, so uint16 per the spec sketch would
                              truncate exactly the quantity the conservative
                              n-gate depends on; float32 is the same 110 MB as
                              the pool cube and is documented in PHASE1.md)
    sumw2_cube.npy   float32  sum of (PWGTP * a_eff)^2    (Kish effective
                              sample size at serve time, correction 2)
m1.1.0: variance.npy (the Phase 1 diagnostic power law) is retired; the
Gate 0 interval model ships in manifest["interval_model"] with per-metro
offsets in features.parquet, which also carries the static context features
and missing-feature flags. Pillar weights and slider constants flow
registry -> manifest["model_defaults"] -> model, so the registry stays the
single home for both.
The build directory is immutable and content-addressed: data_version is a
hash over the file hashes; manifest.json carries both plus every source
vintage.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time

import numpy as np
import pandas as pd

from atlas.model.versions import MODEL_VERSION, SCHEMA_VERSION
from atlas.pipeline.adapters.census import DhcTractGqAdapter
from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.contracts.provenance import (assert_all_shippable,
                                                 assert_manifest_matches_requests)
from atlas.pipeline.adapters.base import LICENSES
from atlas.pipeline.contracts.provenance import Provenance
from atlas.pipeline.fetch import DATA, RESULTS
from atlas.pipeline.registry.loader import load_registry

P1 = RESULTS / "phase1"
P2 = RESULTS / "phase2"
BUILDS = DATA / "builds"

SEX_LEVELS = ["male", "female"]
AGE_LEVELS = [str(a) for a in range(18, 71)]
MARITAL_LEVELS = ["never", "previously", "currently"]
EDU_LEVELS = ["hs_or_less", "some_college", "bachelors", "graduate"]
INC_LEVELS = ["lt25k", "25_50k", "50_75k", "75_100k", "100_150k", "150_250k", "ge250k"]
RACE_LEVELS = ["hispanic", "nh_white", "nh_black", "nh_asian", "nh_aian",
               "nh_nhpi", "nh_twoplus", "nh_other"]

MARITAL_FROM_PARQUET = {"never": 0, "formerly": 1, "married": 2}
EDU_IDX = {l: i for i, l in enumerate(EDU_LEVELS)}
RACE_IDX = {l: i for i, l in enumerate(RACE_LEVELS)}


def axes_schema(metro_levels: list[str]) -> list[dict]:
    return [
        {"name": "metro", "levels": metro_levels},
        {"name": "sex", "levels": SEX_LEVELS},
        {"name": "age", "levels": AGE_LEVELS},
        {"name": "marital", "levels": MARITAL_LEVELS},
        {"name": "education", "levels": EDU_LEVELS},
        {"name": "income", "levels": INC_LEVELS},
        {"name": "race_eth", "levels": RACE_LEVELS},
    ]


def build(out_root=None) -> str:
    con = open_pool()
    quality = pd.read_csv(P1 / "metro_quality.csv", dtype={"cbsa": str})
    metros = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})
    reg = load_registry()
    statics = pd.read_csv(P2 / "static_features.csv", dtype={"cbsa": str})
    iv = json.loads((P2 / "interval_validation.json").read_text())
    ioff = pd.read_csv(P2 / "interval_metro_offsets.csv", dtype={"cbsa": str})
    geo = json.loads((RESULTS / "geography_manifest.json").read_text())
    assert iv["option2_one_sided"]["pass"], "Gate 0 interval bound not passing"
    manifest_files = json.loads((RESULTS / "fetch_manifest.json").read_text())["files"]

    metro_levels = sorted(metros["cbsa"])
    shape = (len(metro_levels), 2, 53, 3, 4, 7, 8)
    n_cells = int(np.prod(shape))
    midx = {c: i for i, c in enumerate(metro_levels)}

    rows = con.execute("""
        SELECT cbsa, sex, agep, marital3, edu4, incband7, race8,
               sum(pwgtp * a_eff) AS w,
               sum(a_eff) AS n_alloc,
               sum(pwgtp * pwgtp * a_eff * a_eff) AS w2
        FROM contrib
        WHERE agep BETWEEN 18 AND 70 AND gq <> 2
        GROUP BY 1,2,3,4,5,6,7
    """).df()
    for c in ["sex", "agep", "marital3", "edu4", "incband7", "race8"]:
        assert rows[c].notna().all(), f"NULL {c} in cube rows"

    idx = (
        rows["cbsa"].map(midx).to_numpy(),
        (rows["sex"].astype(int) - 1).to_numpy(),
        (rows["agep"].astype(int) - 18).to_numpy(),
        rows["marital3"].map(MARITAL_FROM_PARQUET).to_numpy(),
        rows["edu4"].map(EDU_IDX).to_numpy(),
        (rows["incband7"].astype(int) - 1).to_numpy(),
        rows["race8"].map(RACE_IDX).to_numpy(),
    )
    pool_cube = np.zeros(shape, dtype=np.float32)
    count_cube = np.zeros(shape, dtype=np.float32)
    sumw2_cube = np.zeros(shape, dtype=np.float32)
    pool_cube[idx] = rows["w"].to_numpy(dtype=np.float32)
    count_cube[idx] = rows["n_alloc"].to_numpy(dtype=np.float32)
    sumw2_cube[idx] = rows["w2"].to_numpy(dtype=np.float32)

    tot_sql = con.execute("""
        SELECT sum(pwgtp * a_eff), sum(a_eff) FROM contrib
        WHERE agep BETWEEN 18 AND 70 AND gq <> 2""").fetchone()
    assert abs(pool_cube.sum(dtype=np.float64) - tot_sql[0]) / tot_sql[0] < 1e-6
    assert abs(count_cube.sum(dtype=np.float64) - tot_sql[1]) / tot_sql[1] < 1e-6
    max_count = float(count_cube.max())
    print(f"cube: {n_cells:,} cells, {len(rows):,} nonzero; max count cell "
          f"{max_count:,.1f} (uint16 would hold the magnitude but not the fraction)")

    static_cols = ["median_gross_rent", "rpp_goods", "rpp_services_other",
                   "venues_per_100k", "resident_walkability_index",
                   "pleasant_days", "students_per_1k_adults", "feature_flags"]
    feats = (quality.merge(metros[["cbsa", "states", "n_counties"]], on="cbsa")
             .merge(statics[["cbsa"] + static_cols], on="cbsa", how="left")
             .merge(ioff.rename(columns={"offset": "interval_offset"}),
                    on="cbsa", how="left"))
    feats = feats.set_index("cbsa").loc[metro_levels].reset_index()
    assert feats["interval_offset"].notna().all(), "metro missing interval offset"
    feats["feature_flags"] = feats["feature_flags"].fillna("")

    tmp = BUILDS / f"_tmp_{int(time.time())}"
    tmp.mkdir(parents=True, exist_ok=True)
    np.save(tmp / "pool_cube.npy", pool_cube)
    np.save(tmp / "count_cube.npy", count_cube)
    np.save(tmp / "sumw2_cube.npy", sumw2_cube)
    feats.to_parquet(tmp / "features.parquet", index=False)
    (tmp / "metros.json").write_text(json.dumps(
        [{"cbsa": r["cbsa"], "title": r["cbsa_title"],
          "ranked_set": bool(r["ranked_set"])} for _, r in feats.iterrows()],
        indent=1) + "\n")

    hashes = {}
    for f in sorted(tmp.iterdir()):
        hashes[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    data_version = hashlib.sha256(
        json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]

    manifest = {
        "data_version": data_version,
        "model_version": MODEL_VERSION,
        "schema_version": SCHEMA_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "axes": axes_schema(metro_levels),
        "cube_shape": list(shape),
        "cube_cells": n_cells,
        "universe": "ages 18-70, institutional group quarters excluded",
        "cube_dtypes": {"pool_cube": "float32 sum PWGTP*a_eff",
                        "count_cube": "float32 sum a_eff (fractional allocated respondents)",
                        "sumw2_cube": "float32 sum (PWGTP*a_eff)^2"},
        "interval_model": {
            "mechanism": "one_sided_calibrated_bound (Gate 0 Option 2)",
            "form": "served_RSE = exp(X.beta + metro_offset) * inflation[race]",
            "feature_names": iv["features"],
            "coefficients": [iv["coefficients"][n] for n in iv["features"]],
            "race_levels": RACE_LEVELS,
            "inflation_by_race": iv["option2_one_sided"]["inflation_by_race"],
            "validation": {
                "coverage": iv["option2_one_sided"]["coverage"],
                "median_overstatement": iv["option2_one_sided"]["median_overstatement"],
                "p90_overstatement": iv["option2_one_sided"]["p90_overstatement"],
                "option1_two_sided_p90_rel_err": iv["option1_two_sided"]["p90_rel_err"],
                "gates": iv["option2_one_sided"]["gates"],
            },
            "copy_rule": "margins read 'at least this wide', never plus-or-minus",
            "used_by_api": True,
        },
        "variance_model_phase1": {
            "note": "the Phase 1 per-metro power law is retired; its 44% p90 "
                    "failure and diagnostics remain in "
                    "results/phase1/variance_validation.json",
            "used_by_api": False,
        },
        "tier_policy": {
            "suppress": "min(n_alloc, kish) < 100, or served CV > 30%, or "
                        "empty pool/rivals",
            "shown_unranked": "20% < served CV <= 30% (D08, computed on the "
                              "served upper-bound CV — errs toward not ranking)",
            "ranked": "served CV <= 20% and n_gate >= 100",
        },
        "model_defaults": {
            "pillar_weights": reg.pillars,
            "size_vs_odds": reg.size_vs_odds,
        },
        "features_block": {
            f.id: {"pillar": f.pillar, "kind": f.kind, "direction": f.direction,
                   "weight_in_pillar": f.weight_in_pillar, "status": f.status,
                   "provenance": f.provenance}
            for f in reg.features.values()
        },
        "sources": {
            "delineation": geo["delineation_vintage"],
            "acs": geo["acs_dataset"],
            "dhc": geo["dhc_dataset"],
            "pums": "ACS 2020-2024 5-year PUMS person+housing files (51 states)",
            "tract_puma_relationship": geo["tract_puma_relationship"],
            "gq_allocation": geo["gq_allocation"],
            "dhc_table": geo["dhc_table"],
            "dhc_variables": sorted(geo["dhc_variables"]),
            "n_source_files_fetched": len(manifest_files),
        },
        "file_sha256": hashes,
    }
    # Provenance cannot drift from the query: the manifest's recorded DHC
    # variable list must equal what the adapter actually requests, and every
    # scored feature must trace to a shippable source.
    assert_manifest_matches_requests(
        {"dhc": manifest["sources"]["dhc_variables"]},
        {"dhc": DhcTractGqAdapter().requested_variables})
    provs = {f.id: Provenance(**{**{k: f.provenance[k] for k in
                                    ("source", "dataset", "table", "geography",
                                     "vintage", "transform_id", "tier")},
                               "variables": tuple(f.provenance["variables"])})
             for f in reg.features.values() if f.status == "active"}
    assert_all_shippable(provs, LICENSES | {"census_acs": LICENSES["census_acs"]})
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    out_dir = (out_root or BUILDS) / data_version
    if out_dir.exists():
        shutil.rmtree(tmp)
        print(f"build {data_version} already exists")
        return data_version
    tmp.rename(out_dir)
    (P2 / "build_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    size_mb = sum(f.stat().st_size for f in out_dir.iterdir()) / 1e6
    print(f"build {data_version} -> {out_dir} ({size_mb:.0f} MB)")
    return data_version


if __name__ == "__main__":
    build()
