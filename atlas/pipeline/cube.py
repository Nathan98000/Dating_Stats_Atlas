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
    variance.npy     float32  (n_metros, 2) per-metro [alpha, beta]
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

from fetch import DATA, RESULTS
from pool import open_pool
from score import MODEL_VERSION, SCHEMA_VERSION

P1 = RESULTS / "phase1"
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
    fit = pd.read_csv(P1 / "variance_fit.csv", dtype={"cbsa": str})
    val = json.loads((P1 / "variance_validation.json").read_text())
    geo = json.loads((RESULTS / "geography_manifest.json").read_text())
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

    feats = (quality.merge(fit, on="cbsa", how="left")
             .merge(metros[["cbsa", "states", "n_counties"]], on="cbsa"))
    feats = feats.set_index("cbsa").loc[metro_levels].reset_index()
    variance = feats[["alpha", "beta"]].to_numpy(dtype=np.float32)
    assert not np.isnan(variance).any(), "metro missing variance coefficients"

    tmp = BUILDS / f"_tmp_{int(time.time())}"
    tmp.mkdir(parents=True, exist_ok=True)
    np.save(tmp / "pool_cube.npy", pool_cube)
    np.save(tmp / "count_cube.npy", count_cube)
    np.save(tmp / "sumw2_cube.npy", sumw2_cube)
    np.save(tmp / "variance.npy", variance)
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
        "variance_model": {
            "form": "log(RSE) = alpha + beta*log(n_alloc), per metro",
            "validation_p90_rel_err": val["validation_p90_rel_err"],
            "beta_median": val["beta_median"],
            "fallback_metros": val["fallback_metros"],
        },
        "sources": {
            "delineation": geo["delineation_vintage"],
            "acs": geo["acs_dataset"],
            "dhc": geo["dhc_dataset"],
            "pums": "ACS 2020-2024 5-year PUMS person+housing files (51 states)",
            "tract_puma_relationship": geo["tract_puma_relationship"],
            "gq_allocation": geo["gq_allocation"],
            "n_source_files_fetched": len(manifest_files),
        },
        "file_sha256": hashes,
    }
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    out_dir = (out_root or BUILDS) / data_version
    if out_dir.exists():
        shutil.rmtree(tmp)
        print(f"build {data_version} already exists")
        return data_version
    tmp.rename(out_dir)
    (P1 / "build_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    size_mb = sum(f.stat().st_size for f in out_dir.iterdir()) / 1e6
    print(f"build {data_version} -> {out_dir} ({size_mb:.0f} MB)")
    return data_version


if __name__ == "__main__":
    build()
