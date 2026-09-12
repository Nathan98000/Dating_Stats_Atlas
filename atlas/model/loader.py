"""Build artifact -> in-memory arrays, with the schema contract enforced.

This is the one sanctioned I/O module inside model/ (documented deviation
from the strict no-I/O rule in §13.1): the API, the golden tests and the
validation suite all load builds through exactly this code path, so the
axis contract has one enforcement point. scoring/suppression/explain import
nothing from it beyond the Build dataclass.

m1.1.0 artifact changes: variance.npy (the Phase 1 diagnostic power law) is
retired; the interval mechanism lives in manifest["interval_model"] plus a
per-metro offset column in features.parquet, and features.parquet carries
the static context features, purity, pool population and missing-feature
flags. Pillar weights and slider constants arrive through
manifest["model_defaults"], whose source of truth is the feature registry.
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
from atlas.model.versions import SCHEMA_VERSION

STATIC_FEATURES = ["median_gross_rent", "rpp_goods", "rpp_services_other",
                   "venues_per_100k", "resident_walkability_index",
                   "pleasant_days", "students_per_1k_adults"]


@dataclass
class Build:
    path: Path
    manifest: dict
    metro_levels: list[str]
    titles: dict[str, str]
    ranked_set: np.ndarray          # bool (n_metros,)
    pool_flat: np.ndarray           # (n_metros, N_FLAT) float32
    count_flat: np.ndarray
    sumw2_flat: np.ndarray
    pool_pop: np.ndarray            # 18-70 noninst population per metro
    purity: np.ndarray
    static: dict = field(default_factory=dict)            # feature -> array
    static_direction: dict = field(default_factory=dict)  # feature -> +-1
    static_weight: dict = field(default_factory=dict)     # feature -> w in pillar
    feature_flags: list = field(default_factory=list)     # per metro, str
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


def load_build(path: str | Path, verify_hashes: bool = True) -> Build:
    path = Path(path)
    manifest = json.loads((path / "manifest.json").read_text())
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

    feats = pd.read_parquet(path / "features.parquet")
    feats["cbsa"] = feats["cbsa"].astype(str)
    feats = feats.set_index("cbsa").loc[metro_levels]
    fb = manifest["features_block"]
    static = {f: feats[f].to_numpy(dtype=np.float64) for f in STATIC_FEATURES}
    for f in STATIC_FEATURES:
        assert f in fb, f"feature {f} missing from manifest features_block"

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

    return Build(
        path=path, manifest=manifest, metro_levels=metro_levels, titles=titles,
        ranked_set=ranked,
        pool_flat=np.ascontiguousarray(pool.reshape(n, N_FLAT)),
        count_flat=np.ascontiguousarray(count.reshape(n, N_FLAT)),
        sumw2_flat=np.ascontiguousarray(sumw2.reshape(n, N_FLAT)),
        pool_pop=feats["pop_pool_18_70"].to_numpy(dtype=np.float64),
        purity=feats["purity_pums"].to_numpy(dtype=np.float64),
        static=static,
        static_direction={f: int(fb[f]["direction"]) for f in STATIC_FEATURES},
        static_weight={f: float(fb[f]["weight_in_pillar"]) for f in STATIC_FEATURES},
        feature_flags=feats["feature_flags"].fillna("").tolist(),
        intervals=intervals,
    )
