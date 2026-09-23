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

m3.0.0 artifact changes (ADR 0009): the build ships kernel.json +
kernel.npz (the assortative kernel with its per-metro dials and
normalisers), loaded into Build.kernel; and the loader precomputes the
REDUCED cubes the weighted path sums over — pool and sumw2 collapsed to
(metro, sex, age, education, race) for each of the 3 marital selections
x 7 income floors, so a request's kernel-weighted sum is an einsum over
1,696 cells per metro instead of a 28,448-cell masked pass. The reduced
sums with unit weights must equal pool_flat @ mask (asserted in tests:
the weighted path's mask-axis sibling).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.model.intervals import IntervalModel
from atlas.model.preferences import (EDU_LEVELS, INC_LEVELS, KERNEL_COMPONENTS,
                                     MARITAL_LEVELS, N_FLAT, RACE_LEVELS,
                                     SEX_LEVELS, Kernel)
from atlas.model.versions import MODEL_VERSION, SCHEMA_VERSION

STATIC_FEATURES = ["rent_1br", "rpp_goods", "rpp_services_other",
                   "venues_per_100k", "resident_walkability_index",
                   "pleasant_days", "students_per_1k_adults"]
# display-only stats the v3 city cards read (never scored); their values
# and national standings ship in features.parquet
CARD_ONLY_FEATURES = {"everyday_prices": "everyday_prices",
                      "who_lives_here": "pop_total"}
# crime context (Phase 2d item 5; D01): values for the registry-chosen
# year, NaN where coverage failed or nothing reported — never scored,
# asserted at registry load and again in the engine tests
CRIME_FEATURES = ("violent_crime_rate", "property_crime_rate",
                  "crime_coverage")
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
    crime: dict = field(default_factory=dict)             # crime feature -> array
    standing_all: dict = field(default_factory=dict)      # feature -> pct/387
    static_direction: dict = field(default_factory=dict)  # feature -> +-1
    static_weight: dict = field(default_factory=dict)     # feature -> w in pillar
    feature_flags: list = field(default_factory=list)     # per metro, str
    legend: dict = field(default_factory=dict)            # feature -> display/meta
    pillars: dict = field(default_factory=dict)           # pillar -> display/weight
    pairing_metro: dict = field(default_factory=dict)     # rate/moe/n arrays
    pairing: PairingCells | None = None
    intervals: IntervalModel | None = None
    # m3.0.0: the kernel and the reduced cubes the weighted path reads
    kernel: Kernel | None = None
    reduced_pool: np.ndarray | None = None    # (3 marital sets, 7 floors, n, 2, 53, 4, 8) float32
    reduced_sumw2: np.ndarray | None = None


# marital selections the reduced cubes are keyed on, in the order the
# cube's marital axis reads (never=0, previously=1); income floors are
# the seven band indices (0 = no floor)
REDUCED_MARITAL_SETS = ((0,), (1,), (0, 1))


def reduced_key(marital_levels: frozenset[int], income_floor_idx: int) -> tuple[int, int]:
    sel = tuple(sorted(marital_levels))
    assert sel in REDUCED_MARITAL_SETS, f"marital selection {sel} not reducible"
    return REDUCED_MARITAL_SETS.index(sel), int(income_floor_idx)


def reduce_cube(cube: np.ndarray) -> np.ndarray:
    """(n, 2, 53, 3, 4, 7, 8) -> (3, 7, n, 2, 53, 4, 8): summed over the
    marital selection and over income bands at or above each floor."""
    n = cube.shape[0]
    out = np.empty((len(REDUCED_MARITAL_SETS), 7, n, 2, 53, 4, 8), dtype=np.float32)
    c64 = cube.astype(np.float64, copy=False)
    for mi, msel in enumerate(REDUCED_MARITAL_SETS):
        base = c64[:, :, :, list(msel), :, :, :].sum(axis=3)          # (n, 2, 53, 4, 7, 8)
        cum = np.flip(np.cumsum(np.flip(base, axis=4), axis=4), axis=4)
        for f in range(7):
            out[mi, f] = cum[:, :, :, :, f, :]
    return out


def _load_kernel(path: Path, metro_levels: list[str]) -> Kernel:
    meta = json.loads((path / "kernel.json").read_text())
    z = np.load(path / "kernel.npz", allow_pickle=False)
    assert meta["version"] == "kernel_v1", meta["version"]
    assert list(z["metro_levels"]) == metro_levels, (
        "kernel.npz metro order disagrees with the build's metros")
    assert meta["sex_levels"] == SEX_LEVELS and meta["edu_levels"] == EDU_LEVELS \
        and meta["race_levels"] == RACE_LEVELS, "kernel level coding drifted"
    f_age = np.asarray(z["f_age"], dtype=np.float64)
    f_edu = np.asarray(z["f_edu"], dtype=np.float64)
    f_race = np.asarray(z["f_race"], dtype=np.float64)
    dials = np.asarray(z["dials"], dtype=np.float64)
    log_norm = np.asarray(z["log_norm"], dtype=np.float32)
    avail = np.asarray(z["avail_national"], dtype=np.float64)
    n = len(metro_levels)
    if log_norm.shape == (n, 2 * 53 * 4 * 8):
        # the writer stores the per-seeker normalisers flat in seeker-type
        # order (sex, age, edu, race), which is exactly this reshape
        log_norm = log_norm.reshape(n, 2, 53, 4, 8)
    assert f_age.shape == (2, 105) and f_edu.shape == (4, 4) and f_race.shape == (2, 8, 8)
    assert dials.shape == (n, 3) and log_norm.shape == (n, 2, 53, 4, 8)
    assert avail.shape == (2, 53, 4, 8) and (avail >= 0).all()
    assert np.isfinite(f_age).all() and np.isfinite(f_edu).all() and np.isfinite(f_race).all()
    assert np.isfinite(dials).all() and (dials >= 0).all()
    comps = tuple(meta.get("dial_components", []))
    for j, c in enumerate(KERNEL_COMPONENTS):
        if c not in comps:
            assert np.allclose(dials[:, j], 1.0), (
                f"component {c} earned no dial but carries non-unit dials")
    return Kernel(f_age=f_age, f_edu=f_edu, f_race=f_race, dials=dials,
                  log_norm=log_norm, avail=avail, gap_offset=int(meta["gap_offset"]),
                  dial_components=comps,
                  meta={k: meta.get(k) for k in ("version", "fitting_sample",
                                                  "fitting_sample_spec", "bandwidth_years",
                                                  "dials_tau", "generated_at", "gauge",
                                                  "form")})


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
    if (allow_model_mismatch and "rent_1br" not in feats.columns
            and "median_gross_rent" in feats.columns):
        # pre-m2.4.0 artifact under deliberate cross-version work: rent
        # was renamed in Phase 2g (ADR 0008); the old column IS the old
        # rent, so the comparison instruments can read both builds
        _ren = lambda k: "rent_1br" if k == "median_gross_rent" else k  # noqa: E731
        feats = feats.rename(columns={
            "median_gross_rent": "rent_1br",
            "standing_all_median_gross_rent": "standing_all_rent_1br"})
        fb = {_ren(k): v for k, v in fb.items()}
        manifest = dict(manifest)
        manifest["city_cards"] = [_ren(c) for c in manifest["city_cards"]]
        manifest["stat_pages"] = [_ren(c) for c in manifest["stat_pages"]]
    static = {f: feats[f].to_numpy(dtype=np.float64) for f in STATIC_FEATURES}
    for fid, col in CARD_ONLY_FEATURES.items():
        static[fid] = feats[col].to_numpy(dtype=np.float64)
    # m2.1.0 artifact requirements — strict for the build being served,
    # relaxed only under allow_model_mismatch (deliberate cross-version
    # work on an older artifact, e.g. the split-equivalence gate)
    old_artifact = allow_model_mismatch and not all(
        fid in feats.columns for fid in CRIME_FEATURES)
    crime = {}
    for fid in CRIME_FEATURES:
        if old_artifact:
            crime[fid] = np.full(len(feats), np.nan)
            continue
        assert fid in feats.columns, f"features.parquet missing {fid} (m2.1.0)"
        crime[fid] = feats[fid].to_numpy(dtype=np.float64)
    standing_all = {}
    banded = list(manifest["city_cards"]) + (
        [] if old_artifact else ["violent_crime_rate", "property_crime_rate"])
    for fid in banded:
        col = f"standing_all_{fid}"
        assert col in feats.columns, f"features.parquet missing {col}"
        standing_all[fid] = feats[col].to_numpy(dtype=np.float64)
    if not old_artifact:
        bands = manifest["standing_bands"]
        assert (len(bands.get("edges", [])) == len(bands.get("keys", [])) - 1
                and len(bands.get("keys", [])) == 5), (
            "manifest must carry the five-band standing thresholds (m2.1.0)")
        assert "strings" in manifest and "crime" in manifest, (
            "manifest must carry the registry strings and crime block (m2.1.0)")
        assert {"year", "coverage_floor"} <= set(manifest["crime"])
        from atlas.model.preferences import SELECTABLE_RACES
        assert [g["id"] for g in manifest.get("race_groups", [])] == \
            list(SELECTABLE_RACES), (
            "manifest race_groups must name the eight selectable groups in "
            "panel order (m2.2.0/ADR 0006)")
    for f in STATIC_FEATURES + ["pool_balance", "match_propensity"]:
        assert f in fb, f"feature {f} missing from manifest features_block"
    assert fb["pool_balance"].get("status") == "context_only" and \
        float(fb["pool_balance"]["weight_in_pillar"]) == 0.0, (
        "pool_balance is displayed, never scored (ADR 0009)")
    assert fb["match_propensity"]["pillar"] == "match", "match_propensity carries the match pillar"
    if not old_artifact:
        for f in CRIME_FEATURES:
            assert f in fb, f"feature {f} missing from manifest features_block"
    for fid, entry in fb.items():
        missing = [k for k in LEGEND_DISPLAY_KEYS if not entry.get(k)]
        assert not missing, (
            f"manifest features_block[{fid}] missing display fields {missing} "
            f"(ADR 0003: no user-facing label lives in code)")
    for fid in manifest["city_cards"]:
        labels = fb[fid].get("band_labels")
        tones = fb[fid].get("band_tones")
        assert labels and tones and (old_artifact or len(labels) == 5
                                     and len(tones) == 5), (
            f"city card {fid} needs five band_labels and five derived "
            f"band_tones in the manifest (m2.1.0)")
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

    # m3.0.0: the kernel is part of the served artifact; a build without
    # it cannot serve chances of matching
    assert (path / "kernel.json").exists() and (path / "kernel.npz").exists(), (
        "build is missing kernel.json / kernel.npz (m3.0.0); run "
        "build.kernel before build.cube")
    kernel = _load_kernel(path, metro_levels)
    reduced_pool = reduce_cube(pool)
    reduced_sumw2 = reduce_cube(sumw2)

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
        crime=crime,
        standing_all=standing_all,
        static_direction={f: int(fb[f]["direction"]) for f in STATIC_FEATURES},
        static_weight={f: float(fb[f]["weight_in_pillar"]) for f in STATIC_FEATURES},
        feature_flags=feats["feature_flags"].fillna("").tolist(),
        legend=fb,
        pillars=manifest["pillars"],
        pairing_metro=pairing_metro,
        pairing=_load_pairing(path, metro_levels),
        intervals=intervals,
        kernel=kernel,
        reduced_pool=reduced_pool,
        reduced_sumw2=reduced_sumw2,
    )
