"""Build artifact -> in-memory arrays, with the schema contract enforced.

This is the one sanctioned I/O module inside model/ (documented deviation
from the strict no-I/O rule in §13.1): the API, the golden tests and the
validation suite all load builds through exactly this code path, so the
axis contract has one enforcement point. scoring/suppression/explain import
nothing from it beyond the Build dataclass.

m1.2.0 artifact changes: features.parquet gains the metro-level interim
cross-group pairing columns; pairing_cells.parquet ships the per
metro x sex x race pairing cells with their 80 replicate sums (the §10.4
counterweight's margins are measured directly at serve time); the manifest
features_block carries the registry display fields so no user-facing label
lives in code. The loader now also refuses a build whose model_version
disagrees with the engine's — a build produced under one model version
loaded silently into another is the same class of failure as the Phase 1
mask bug: two things that must agree, with nothing checking that they do.
Pass allow_model_mismatch=True only for deliberate cross-version work.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.model.intervals import IntervalModel
from atlas.model.preferences import (EDU_LEVELS, INC_LEVELS, MARITAL_LEVELS,
                                     N_FLAT, RACE_LEVELS, SEX_LEVELS)
from atlas.model.versions import MODEL_VERSION, SCHEMA_VERSION

STATIC_FEATURES = ["median_gross_rent", "rpp_goods", "rpp_services_other",
                   "venues_per_100k", "resident_walkability_index",
                   "pleasant_days", "students_per_1k_adults"]
# display-only stats the v3 city cards read (never scored); their values
# and national standings ship in features.parquet
CARD_ONLY_FEATURES = {"everyday_prices": "everyday_prices",
                      "who_lives_here": "pop_total"}
LEGEND_DISPLAY_KEYS = ("display_name", "unit", "definition")


@dataclass
class PairingCells:
    """Interim cross-group pairing cells (metro, sex, race), with the 80
    replicate numerator/denominator sums for direct margin measurement."""
    num: np.ndarray        # (n_metros, 2, 8) weighted out-group partnered
    den: np.ndarray        # (n_metros, 2, 8) weighted partnered
    n_alloc: np.ndarray    # (n_metros, 2, 8) allocated respondents
    sumw2: np.ndarray      # (n_metros, 2, 8) sum of squared weights
    num_r: np.ndarray      # (n_metros, 2, 8, 80)
    den_r: np.ndarray      # (n_metros, 2, 8, 80)


@dataclass
class Build:
    path: Path
    manifest: dict
    metro_levels: list[str]
    titles: dict[str, str]
    display_names: list[str]        # "Provo, UT" (v3 list rows)
    display_names_full: list[str]   # "Provo, Utah" (v3 city page)
    slugs: list[str]                # "provo-utah" (routes; no code renders)
    descriptions: list[str]         # the formulaic one-line description
    ranked_set: np.ndarray          # bool (n_metros,)
    pool_flat: np.ndarray           # (n_metros, N_FLAT) float32
    count_flat: np.ndarray
    sumw2_flat: np.ndarray
    pool_pop: np.ndarray            # 18-70 noninst population per metro
    purity: np.ndarray
    gq_flag: np.ndarray             # bool (n_metros,) — dorm/barracks share
    static: dict = field(default_factory=dict)            # feature -> array
    standing_all: dict = field(default_factory=dict)      # feature -> pct/387
    static_direction: dict = field(default_factory=dict)  # feature -> +-1
    static_weight: dict = field(default_factory=dict)     # feature -> w in pillar
    feature_flags: list = field(default_factory=list)     # per metro, str
    legend: dict = field(default_factory=dict)            # feature -> display/meta
    pillars: dict = field(default_factory=dict)           # pillar -> display/weight
    pairing_metro: dict = field(default_factory=dict)     # rate/moe/n arrays
    pairing: PairingCells | None = None
    intervals: IntervalModel | None = None


def _validate_axes(manifest: dict) -> list[str]:
    assert manifest["schema_version"] == SCHEMA_VERSION, (
        f"build schema {manifest['schema_version']!r} != engine {SCHEMA_VERSION!r}")
    axes = manifest["axes"]
    names = [a["name"] for a in axes]
    assert names == ["metro", "sex", "age", "marital", "education", "income",
                     "race_eth"], names
    assert axes[1]["levels"] == SEX_LEVELS
    assert axes[2]["levels"] == [str(a) for a in range(18, 71)]
    assert axes[3]["levels"] == MARITAL_LEVELS
    assert axes[4]["levels"] == EDU_LEVELS
    assert axes[5]["levels"] == INC_LEVELS
    assert axes[6]["levels"] == RACE_LEVELS
    return axes[0]["levels"]


def _load_pairing(path: Path, metro_levels: list[str]) -> PairingCells:
    df = pd.read_parquet(path / "pairing_cells.parquet")
    df["cbsa"] = df["cbsa"].astype(str)
    n = len(metro_levels)
    midx = {c: i for i, c in enumerate(metro_levels)}
    sidx = {s: i for i, s in enumerate(SEX_LEVELS)}
    ridx = {r: i for i, r in enumerate(RACE_LEVELS)}
    shape = (n, 2, 8)
    arrs = {k: np.zeros(shape, dtype=np.float64)
            for k in ("num", "den", "n_alloc", "sumw2")}
    num_r = np.zeros(shape + (80,), dtype=np.float32)
    den_r = np.zeros(shape + (80,), dtype=np.float32)
    ii = (df["cbsa"].map(midx).to_numpy(),
          df["sex"].map(sidx).to_numpy(),
          df["race8"].map(ridx).to_numpy())
    assert not any(np.isnan(x.astype(float)).any() for x in ii), (
        "pairing_cells carries an unknown metro/sex/race level")
    for k in arrs:
        arrs[k][ii] = df[k].to_numpy(dtype=np.float64)
    rep_num = df[[f"num_r{i}" for i in range(1, 81)]].to_numpy(dtype=np.float32)
    rep_den = df[[f"den_r{i}" for i in range(1, 81)]].to_numpy(dtype=np.float32)
    num_r[ii] = rep_num
    den_r[ii] = rep_den
    return PairingCells(num=arrs["num"], den=arrs["den"],
                        n_alloc=arrs["n_alloc"], sumw2=arrs["sumw2"],
                        num_r=num_r, den_r=den_r)


def load_build(path: str | Path, verify_hashes: bool = True,
               allow_model_mismatch: bool = False) -> Build:
    path = Path(path)
    manifest = json.loads((path / "manifest.json").read_text())
    if not allow_model_mismatch:
        assert manifest["model_version"] == MODEL_VERSION, (
            f"build model_version {manifest['model_version']!r} != engine "
            f"{MODEL_VERSION!r}; regenerate the build, or pass "
            f"allow_model_mismatch=True for deliberate cross-version work")
    metro_levels = _validate_axes(manifest)
    n = len(metro_levels)

    npz = path / "fixture.npz"
    if npz.exists():
        z = np.load(npz)
        pool, count, sumw2 = z["pool_cube"], z["count_cube"], z["sumw2_cube"]
    else:
        if verify_hashes:
            for fname, want in manifest["file_sha256"].items():
                got = hashlib.sha256((path / fname).read_bytes()).hexdigest()
                assert got == want, f"hash mismatch for {fname}"
        pool = np.load(path / "pool_cube.npy")
        count = np.load(path / "count_cube.npy")
        sumw2 = np.load(path / "sumw2_cube.npy")

    shape = tuple(manifest["cube_shape"])
    for name, arr in [("pool", pool), ("count", count), ("sumw2", sumw2)]:
        assert arr.shape == shape, f"{name} cube shape {arr.shape} != manifest {shape}"
    assert shape[0] == n and int(np.prod(shape[1:])) == N_FLAT

    metros_meta = json.loads((path / "metros.json").read_text())
    assert [m["cbsa"] for m in metros_meta] == metro_levels
    ranked = np.array([m["ranked_set"] for m in metros_meta], dtype=bool)
    titles = {m["cbsa"]: m["title"] for m in metros_meta}
    for m in metros_meta:
        for k in ("display_name", "display_name_full", "slug", "description"):
            assert m.get(k), f"metros.json entry {m['cbsa']} missing {k} (m2.0.0)"
    display_names = [m["display_name"] for m in metros_meta]
    display_names_full = [m["display_name_full"] for m in metros_meta]
    slugs = [m["slug"] for m in metros_meta]
    assert len(set(slugs)) == len(slugs), "city slugs must be unique"
    descriptions = [m["description"] for m in metros_meta]

    feats = pd.read_parquet(path / "features.parquet")
    feats["cbsa"] = feats["cbsa"].astype(str)
    feats = feats.set_index("cbsa").loc[metro_levels]
    fb = manifest["features_block"]
    static = {f: feats[f].to_numpy(dtype=np.float64) for f in STATIC_FEATURES}
    for fid, col in CARD_ONLY_FEATURES.items():
        static[fid] = feats[col].to_numpy(dtype=np.float64)
    standing_all = {}
    for fid in manifest["city_cards"]:
        col = f"standing_all_{fid}"
        assert col in feats.columns, f"features.parquet missing {col}"
        standing_all[fid] = feats[col].to_numpy(dtype=np.float64)
    assert {"low_below", "high_above"} <= set(manifest["standing_bands"]), (
        "manifest must carry the standing-band thresholds (ADR 0004)")
    for f in STATIC_FEATURES + ["pool_balance"]:
        assert f in fb, f"feature {f} missing from manifest features_block"
    for fid, entry in fb.items():
        missing = [k for k in LEGEND_DISPLAY_KEYS if not entry.get(k)]
        assert not missing, (
            f"manifest features_block[{fid}] missing display fields {missing} "
            f"(ADR 0003: no user-facing label lives in code)")
    for fid in manifest["city_cards"]:
        assert fb[fid].get("band_labels"), (
            f"city card {fid} missing band_labels in the manifest")
    assert "pillars" in manifest and all(
        p.get("display_name") for p in manifest["pillars"].values()), (
        "manifest must carry pillar display names (ADR 0003)")

    im_cfg = manifest["interval_model"]
    assert im_cfg["used_by_api"] is True, "interval model not marked servable"
    intervals = IntervalModel(
        feature_names=list(im_cfg["feature_names"]),
        coef=np.array(im_cfg["coefficients"], dtype=np.float64),
        race_levels=list(im_cfg["race_levels"]),
        offsets=feats["interval_offset"].to_numpy(dtype=np.float64),
        inflation=dict(im_cfg["inflation_by_race"]),
        meta=dict(im_cfg.get("validation", {})))
    assert intervals.race_levels == RACE_LEVELS

    pairing_metro = {
        "rate": feats["cross_group_pairing_rate"].to_numpy(dtype=np.float64),
        "moe": feats["cross_group_pairing_moe"].to_numpy(dtype=np.float64),
        "n": feats["cross_group_pairing_n"].to_numpy(dtype=np.float64),
    }

    return Build(
        path=path, manifest=manifest, metro_levels=metro_levels, titles=titles,
        display_names=display_names, display_names_full=display_names_full,
        slugs=slugs, descriptions=descriptions,
        ranked_set=ranked,
        pool_flat=np.ascontiguousarray(pool.reshape(n, N_FLAT)),
        count_flat=np.ascontiguousarray(count.reshape(n, N_FLAT)),
        sumw2_flat=np.ascontiguousarray(sumw2.reshape(n, N_FLAT)),
        pool_pop=feats["pop_pool_18_70"].to_numpy(dtype=np.float64),
        purity=feats["purity_pums"].to_numpy(dtype=np.float64),
        gq_flag=feats["gq_flag"].to_numpy(dtype=bool),
        static=static,
        standing_all=standing_all,
        static_direction={f: int(fb[f]["direction"]) for f in STATIC_FEATURES},
        static_weight={f: float(fb[f]["weight_in_pillar"]) for f in STATIC_FEATURES},
        feature_flags=feats["feature_flags"].fillna("").tolist(),
        legend=fb,
        pillars=manifest["pillars"],
        pairing_metro=pairing_metro,
        pairing=_load_pairing(path, metro_levels),
        intervals=intervals,
    )
