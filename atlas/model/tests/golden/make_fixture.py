"""Build the pinned 12-metro test fixture and regenerate goldens.

Run AFTER a full cube build:

    python atlas/tests/make_fixture.py <build_dir>

Slices the Phase 0 ten plus two edge metros (the lowest-purity ranked-set
metro and the smallest-population metro) out of the real build into a
compressed fixture, then evaluates the 12 golden request vectors and writes
goldens.json. Goldens are pinned to MODEL_VERSION: a model change that moves
a ranking fails CI until the version is bumped and this script is re-run,
with a note in the commit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from atlas import model as engine  # noqa: E402

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture_build"

GOLDEN_VECTORS = [
    {"name": "A_woman32_ba_men_75k",
     "seeker": {"sex": "female", "age": 32},
     "pool": {"age_min": 30, "age_max": 40, "marital": "not_married",
              "education_min": "bachelors", "income_min": 75000}},
    {"name": "B_man28_women_never",
     "seeker": {"sex": "male", "age": 28},
     "pool": {"age_min": 25, "age_max": 33, "marital": "never"}},
    {"name": "C_woman38_grad_men_100k",
     "seeker": {"sex": "female", "age": 38},
     "pool": {"age_min": 35, "age_max": 48, "marital": "not_married",
              "education_min": "bachelors", "income_min": 100000}},
    {"name": "D_man41_women_50k",
     "seeker": {"sex": "male", "age": 41},
     "pool": {"age_min": 32, "age_max": 45, "marital": "not_married",
              "income_min": 50000}},
    {"name": "E_black_woman29_stress",
     "seeker": {"sex": "female", "age": 29},
     "pool": {"age_min": 28, "age_max": 38, "marital": "not_married",
              "education_min": "bachelors", "income_min": 75000,
              "race": "nh_black"}},
    {"name": "race_nh_asian_men",
     "seeker": {"sex": "female", "age": 30},
     "pool": {"age_min": 27, "age_max": 38, "marital": "not_married",
              "education_min": "bachelors", "race": "nh_asian"}},
    {"name": "race_hispanic_women",
     "seeker": {"sex": "male", "age": 33},
     "pool": {"age_min": 26, "age_max": 38, "marital": "never",
              "race": "hispanic"}},
    {"name": "race_nh_white_men_grad",
     "seeker": {"sex": "female", "age": 45},
     "pool": {"age_min": 40, "age_max": 55, "marital": "not_married",
              "education_min": "graduate", "race": "nh_white"}},
    {"name": "below_bar_nhpi_250k",
     "seeker": {"sex": "female", "age": 30},
     "pool": {"age_min": 25, "age_max": 35, "marital": "never",
              "education_min": "graduate", "income_min": 250000,
              "race": "nh_nhpi"}},
    {"name": "broad_any",
     "seeker": {"sex": "male", "age": 35},
     "pool": {"age_min": 25, "age_max": 50, "marital": "any"}},
    {"name": "weights_pool_only",
     "seeker": {"sex": "female", "age": 29},
     "pool": {"age_min": 27, "age_max": 36, "marital": "not_married"},
     "weights": {"pool": 1.0, "balance": 0.0}},
    {"name": "same_sex_pool",
     "seeker": {"sex": "male", "age": 31},
     "pool": {"sex": "male", "age_min": 27, "age_max": 38, "marital": "never",
              "education_min": "bachelors"}},
]


def make_fixture(build_dir: Path) -> None:
    build = engine.load_build(build_dir)
    feats = pd.read_parquet(build_dir / "features.parquet")
    phase0 = json.loads(
        (HERE.parents[2] / "results" / "geography_manifest.json").read_text()
    )["phase0_metros"]
    ranked = feats[feats["ranked_set"]]
    lowest_purity = ranked.nsmallest(1, "purity_pums")["cbsa"].iloc[0]
    smallest = feats.nsmallest(1, "pop_total")["cbsa"].iloc[0]
    chosen = sorted(set(phase0.values()) | {lowest_purity, smallest})
    assert len(chosen) == 12, chosen
    idx = [build.metro_levels.index(c) for c in chosen]

    n = len(chosen)
    manifest = dict(build.manifest)
    manifest["axes"] = [{"name": "metro", "levels": chosen}] + build.manifest["axes"][1:]
    manifest["cube_shape"] = [n] + build.manifest["cube_shape"][1:]
    manifest["cube_cells"] = int(np.prod(manifest["cube_shape"]))
    manifest["fixture_of"] = build.manifest["data_version"]
    manifest["data_version"] = "fixture-" + build.manifest["data_version"]
    manifest.pop("file_sha256")

    FIXTURE.mkdir(exist_ok=True)
    shape = tuple(manifest["cube_shape"])
    np.savez_compressed(
        FIXTURE / "fixture.npz",
        pool_cube=build.pool_flat[idx].reshape(shape),
        count_cube=build.count_flat[idx].reshape(shape),
        sumw2_cube=build.sumw2_flat[idx].reshape(shape),
        variance=np.stack([build.alpha[idx], build.beta[idx]], axis=1).astype(np.float32),
    )
    (FIXTURE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    metros_meta = [{"cbsa": c, "title": build.titles[c],
                    "ranked_set": bool(build.ranked_set[build.metro_levels.index(c)])}
                   for c in chosen]
    (FIXTURE / "metros.json").write_text(json.dumps(metros_meta, indent=1) + "\n")

    fx = engine.load_build(FIXTURE)
    vectors = []
    for v in GOLDEN_VECTORS:
        res = engine.rank(fx, v["seeker"]["sex"], v["seeker"]["age"], v["pool"],
                          v.get("weights"))
        vectors.append({
            "name": v["name"], "request": v,
            "expect": {
                "ranked_cbsas": [r["cbsa"] for r in res["ranked"]],
                "scores": {r["cbsa"]: r["score"] for r in res["ranked"]},
                "shown_unranked_cbsas": sorted(r["cbsa"] for r in res["shown_unranked"]),
                "suppressed": {r["cbsa"]: r["reason"] for r in res["suppressed"]},
                "counts": res["counts"],
            }})
    n_suppressed_somewhere = sum(1 for v in vectors if v["expect"]["suppressed"])
    assert any(len(v["expect"]["suppressed"]) >= 6 for v in vectors), (
        "no vector is meaningfully below the suppression bar")
    (HERE / "goldens.json").write_text(json.dumps({
        "model_version": engine.MODEL_VERSION,
        "fixture_of": manifest["fixture_of"],
        "vectors": vectors}, indent=1) + "\n")
    print(f"fixture: {n} metros -> {FIXTURE}")
    print(f"goldens: {len(vectors)} vectors, "
          f"{n_suppressed_somewhere} with suppressions -> goldens.json")


if __name__ == "__main__":
    make_fixture(Path(sys.argv[1]))
