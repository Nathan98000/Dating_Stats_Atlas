"""Build artifact -> in-memory arrays, with the schema contract enforced.

This is the one sanctioned I/O module inside model/ (a documented deviation
from the strict no-I/O rule in §13.1): it lives beside the schema it
validates because the API, the golden tests and the validation suite all
load builds through exactly this code path, and a second loader would be a
second place for the axis contract to drift. scoring/suppression/explain
import nothing from it beyond the Build dataclass.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from atlas.model.preferences import (EDU_LEVELS, INC_LEVELS, MARITAL_LEVELS,
                                     N_FLAT, RACE_LEVELS, SEX_LEVELS)
from atlas.model.versions import SCHEMA_VERSION


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
    alpha: np.ndarray
    beta: np.ndarray
    features: dict = field(default_factory=dict)


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
        pool, count, sumw2, variance = (z["pool_cube"], z["count_cube"],
                                        z["sumw2_cube"], z["variance"])
    else:
        if verify_hashes:
            for fname, want in manifest["file_sha256"].items():
                got = hashlib.sha256((path / fname).read_bytes()).hexdigest()
                assert got == want, f"hash mismatch for {fname}"
        pool = np.load(path / "pool_cube.npy")
        count = np.load(path / "count_cube.npy")
        sumw2 = np.load(path / "sumw2_cube.npy")
        variance = np.load(path / "variance.npy")

    shape = tuple(manifest["cube_shape"])
    for name, arr in [("pool", pool), ("count", count), ("sumw2", sumw2)]:
        assert arr.shape == shape, f"{name} cube shape {arr.shape} != manifest {shape}"
    assert variance.shape == (n, 2)
    assert shape[0] == n and int(np.prod(shape[1:])) == N_FLAT

    metros_meta = json.loads((path / "metros.json").read_text())
    assert [m["cbsa"] for m in metros_meta] == metro_levels
    ranked = np.array([m["ranked_set"] for m in metros_meta], dtype=bool)
    titles = {m["cbsa"]: m["title"] for m in metros_meta}

    return Build(
        path=path, manifest=manifest, metro_levels=metro_levels, titles=titles,
        ranked_set=ranked,
        pool_flat=np.ascontiguousarray(pool.reshape(n, N_FLAT)),
        count_flat=np.ascontiguousarray(count.reshape(n, N_FLAT)),
        sumw2_flat=np.ascontiguousarray(sumw2.reshape(n, N_FLAT)),
        alpha=variance[:, 0].astype(np.float64),
        beta=variance[:, 1].astype(np.float64),
    )
