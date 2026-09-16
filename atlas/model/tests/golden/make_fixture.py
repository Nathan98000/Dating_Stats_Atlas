"""Build the pinned 12-metro test fixture and regenerate goldens (m1.2.0).

Run AFTER a full cube build:

    python atlas/model/tests/golden/make_fixture.py <build_dir>

Slices the Phase 0 ten plus the lowest-purity ranked metro and the smallest
metro out of the real build, then evaluates the 12 golden request vectors
(§8.2 request shape; four race-filtered, one deliberately below the
suppression bar, one same-sex pool, one at the odds end of the D05 slider)
and writes goldens.json. Goldens are pinned to MODEL_VERSION: a model
change that moves a ranking fails CI until the version is bumped and this
script is re-run, with a note in the commit.
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
     "self": {"sex": "female", "age": 32, "education": "bachelors"},
     "seeking": {"age": [30, 40],
                 "marital": ["never_married", "previously_married"],
                 "education_min": "bachelors", "income_min": 75000}},
    {"name": "B_man28_women_never",
     "self": {"sex": "male", "age": 28},
     "seeking": {"age": [25, 33], "marital": ["never_married"]}},
    {"name": "C_woman38_grad_men_100k",
     "self": {"sex": "female", "age": 38},
     "seeking": {"age": [35, 48],
                 "marital": ["never_married", "previously_married"],
                 "education_min": "bachelors", "income_min": 100000}},
    {"name": "D_man41_women_50k",
     "self": {"sex": "male", "age": 41},
     "seeking": {"age": [32, 45],
                 "marital": ["never_married", "previously_married"],
                 "income_min": 50000}},
    {"name": "E_black_woman29_stress",
     "self": {"sex": "female", "age": 29, "race_ethnicity": "black_nh"},
     "seeking": {"age": [28, 38],
                 "marital": ["never_married", "previously_married"],
                 "education_min": "bachelors", "income_min": 75000,
                 "race_ethnicity": ["black_nh"]}},
    {"name": "race_asian_nh_men",
     "self": {"sex": "female", "age": 30},
     "seeking": {"age": [27, 38],
                 "marital": ["never_married", "previously_married"],
                 "education_min": "bachelors", "race_ethnicity": ["asian_nh"]}},
    {"name": "race_hispanic_women",
     "self": {"sex": "male", "age": 33},
     "seeking": {"age": [26, 38], "marital": ["never_married"],
                 "race_ethnicity": ["hispanic"]}},
    {"name": "race_white_nh_grad_multi",
     "self": {"sex": "female", "age": 45},
     "seeking": {"age": [40, 55],
                 "marital": ["never_married", "previously_married"],
                 "education_min": "graduate",
                 "race_ethnicity": ["white_nh", "two_or_more_nh"]}},
    {"name": "below_bar_nhpi_250k",
     "self": {"sex": "female", "age": 30},
     "seeking": {"age": [25, 35], "marital": ["never_married"],
                 "education_min": "graduate", "income_min": 250000,
                 "race_ethnicity": ["nhpi_nh"]}},
    {"name": "broad_any",
     "self": {"sex": "male", "age": 35},
     "seeking": {"age": [25, 50],
                 "marital": ["never_married", "previously_married",
                              "currently_married"]}},
    {"name": "slider_best_odds",
     "self": {"sex": "female", "age": 29},
     "seeking": {"age": [27, 36],
                 "marital": ["never_married", "previously_married"]},
     "size_vs_odds": 1.0},
    {"name": "same_sex_pool",
     "self": {"sex": "male", "age": 31},
     "seeking": {"sex": "male", "age": [27, 38], "marital": ["never_married"],
                 "education_min": "bachelors"}},
]


def make_fixture(build_dir: Path) -> None:
    build = engine.load_build(build_dir)
    feats = pd.read_parquet(build_dir / "features.parquet")
    feats["cbsa"] = feats["cbsa"].astype(str)
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
        sumw2_cube=build.sumw2_flat[idx].reshape(shape))
    (FIXTURE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    feats.set_index("cbsa").loc[chosen].reset_index().to_parquet(
        FIXTURE / "features.parquet", index=False)
    cells = pd.read_parquet(Path(build_dir) / "pairing_cells.parquet")
    cells[cells["cbsa"].astype(str).isin(set(chosen))].to_parquet(
        FIXTURE / "pairing_cells.parquet", index=False)
    metros_meta = [{"cbsa": c, "title": build.titles[c],
                    "ranked_set": bool(build.ranked_set[build.metro_levels.index(c)])}
                   for c in chosen]
    (FIXTURE / "metros.json").write_text(json.dumps(metros_meta, indent=1) + "\n")

    fx = engine.load_build(FIXTURE)
    vectors = []
    for v in GOLDEN_VECTORS:
        body = {k: v[k] for k in ("self", "seeking", "weights", "size_vs_odds")
                if k in v}
        res = engine.rank(fx, engine.parse_request(body))
        expect = {
            "ranked_cbsas": [r["cbsa"] for r in res["ranked"]],
            "scores": {r["cbsa"]: r["score"] for r in res["ranked"]},
            "pools": {r["cbsa"]: r["pool"] for r in res["ranked"]},
            "pool_moes": {r["cbsa"]: r["pool_moe"] for r in res["ranked"]},
            "shown_unranked_cbsas": sorted(r["cbsa"] for r in res["shown_unranked"]),
            "suppressed": {r["cbsa"]: r["reason"] for r in res["suppressed"]},
            "counts": res["counts"],
        }
        if v["seeking"].get("race_ethnicity"):
            # Pin the §10.4 counterweight: rate, replicate-measured margin
            # and gate for the top ranked metros of every race-filtered
            # vector (None where the pairing cell sits below the gate).
            expect["cross_group"] = {
                r["cbsa"]: ([r["cross_group_pairing_rate"],
                             r.get("cross_group_pairing_moe"),
                             r.get("cross_group_pairing_n")]
                            if r["cross_group_pairing_rate"] is not None
                            else None)
                for r in res["ranked"][:3]}
        vectors.append({"name": v["name"], "request": body, "expect": expect})
    n_race = sum(1 for v in GOLDEN_VECTORS
                 if v["seeking"].get("race_ethnicity"))
    assert n_race >= 3
    assert any(len(v["expect"]["suppressed"]) >= 6 for v in vectors), (
        "no vector sits meaningfully below the suppression bar")
    (HERE / "goldens.json").write_text(json.dumps({
        "model_version": engine.MODEL_VERSION,
        "fixture_of": manifest["fixture_of"],
        "vectors": vectors}, indent=1) + "\n")
    print(f"fixture: {n} metros -> {FIXTURE}")
    print(f"goldens: {len(vectors)} vectors -> goldens.json "
          f"(model_version {engine.MODEL_VERSION})")


if __name__ == "__main__":
    make_fixture(Path(sys.argv[1]))
