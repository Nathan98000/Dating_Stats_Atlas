"""Serving-side query and scoring engine — pure numpy over a loaded build.

Shared by the FastAPI endpoint and the golden tests so a ranking can never
diverge between them. Loads a build directory (or a compressed fixture),
validates the cube schema contract at load, and answers queries as masked
matrix-vector products over the flattened cubes:

    est_m   = pool_cube[m]  @ mask        (one BLAS sgemv for all metros)
    n_m     = count_cube[m] @ mask        (allocated respondents, fractional)
    kish_m  = est_m^2 / (sumw2_cube[m] @ mask)
    n_gate  = min(n_m, kish_m)            (correction 2)
    CV_m    = exp(alpha_m) * n_m^beta_m   (correction 3 fitted model)

Suppression: n_gate < 100 or CV > 30% -> suppressed; 20% < CV <= 30% ->
shown_not_ranked; else ranked.

Scoring (Phase 1, pool + balance pillars only): per-request normalisation —
winsorize at the 1st/99th percentile across the ranked metros for this query,
log10 for the pool pillar, min-max to [0,1]; linear score with exact
attribution w_k * (z_k(c) - median(z_k)).

Rivals (correction 4, symmetric crude kernel): same sex as the seeker,
seeker's age +/-5 (clamped to 18-70), the pool's education floor, and the
pool's marital screen. No income floor on rivals (rivals compete for the pool
regardless of their own income) and no race screen (the crude kernel is
race-blind; the empirical pairing kernel is Phase 3). Both decisions are
deliberate and documented here and in PHASE1.md.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MODEL_VERSION = "m1.0.0"
SCHEMA_VERSION = "cube-v1"

SEX_LEVELS = ["male", "female"]
MARITAL_LEVELS = ["never", "previously", "currently"]
EDU_LEVELS = ["hs_or_less", "some_college", "bachelors", "graduate"]
INC_LEVELS = ["lt25k", "25_50k", "50_75k", "75_100k", "100_150k", "150_250k", "ge250k"]
RACE_LEVELS = ["hispanic", "nh_white", "nh_black", "nh_asian", "nh_aian",
               "nh_nhpi", "nh_twoplus", "nh_other"]
INCOME_FLOORS = {25_000: 1, 50_000: 2, 75_000: 3, 100_000: 4, 150_000: 5, 250_000: 6}
MARITAL_SETS = {"never": [0], "not_married": [0, 1], "any": [0, 1, 2]}

N_FLAT = 2 * 53 * 3 * 4 * 7 * 8  # per-metro cells


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


def _axis_vec(size: int, on: list[int]) -> np.ndarray:
    v = np.zeros(size, dtype=np.float32)
    v[on] = 1.0
    return v


def mask_vector(sex: str, age_min: int, age_max: int, marital: str,
                education_min: str | None, income_min: int | None,
                race: str | None) -> np.ndarray:
    assert sex in SEX_LEVELS, f"sex must be one of {SEX_LEVELS}"
    assert marital in MARITAL_SETS, f"marital must be one of {list(MARITAL_SETS)}"
    a0, a1 = max(18, int(age_min)), min(70, int(age_max))
    assert a0 <= a1, "empty age range"
    s = _axis_vec(2, [SEX_LEVELS.index(sex)])
    a = _axis_vec(53, list(range(a0 - 18, a1 - 18 + 1)))
    m = _axis_vec(3, MARITAL_SETS[marital])
    if education_min is None:
        e = np.ones(4, dtype=np.float32)
    else:
        assert education_min in EDU_LEVELS[1:], (
            f"education_min must be one of {EDU_LEVELS[1:]}")
        e = _axis_vec(4, list(range(EDU_LEVELS.index(education_min), 4)))
    if income_min is None:
        i = np.ones(7, dtype=np.float32)
    else:
        assert income_min in INCOME_FLOORS, (
            f"income_min must be a band edge: {sorted(INCOME_FLOORS)}")
        i = _axis_vec(7, list(range(INCOME_FLOORS[income_min], 7)))
    if race is None:
        r = np.ones(8, dtype=np.float32)
    else:
        assert race in RACE_LEVELS, f"race must be one of {RACE_LEVELS}"
        r = _axis_vec(8, [RACE_LEVELS.index(race)])
    return np.einsum("s,a,m,e,i,r->samier", s, a, m, e, i, r).ravel()


def _winsor_minmax(x: np.ndarray, log: bool) -> np.ndarray:
    lo, hi = np.percentile(x, [1, 99])
    x = np.clip(x, lo, hi)
    if log:
        x = np.log10(np.maximum(x, 1.0))
    span = x.max() - x.min()
    if span <= 0:
        return np.full_like(x, 0.5)
    return (x - x.min()) / span


def rank(build: Build, seeker_sex: str, seeker_age: int, pool: dict,
         weights: dict | None = None) -> dict:
    """The /v1/rank computation. `pool` keys: sex (optional; default opposite
    of seeker), age_min, age_max, marital, education_min, income_min, race."""
    pool_sex = pool.get("sex") or SEX_LEVELS[1 - SEX_LEVELS.index(seeker_sex)]
    mask_p = mask_vector(pool_sex, pool["age_min"], pool["age_max"],
                         pool["marital"], pool.get("education_min"),
                         pool.get("income_min"), pool.get("race"))
    mask_r = mask_vector(seeker_sex, seeker_age - 5, seeker_age + 5,
                         pool["marital"], pool.get("education_min"), None, None)

    est = build.pool_flat @ mask_p
    n_alloc = build.count_flat @ mask_p
    sumw2 = build.sumw2_flat @ mask_p
    rivals = build.pool_flat @ mask_r

    with np.errstate(divide="ignore", invalid="ignore"):
        kish = np.where(sumw2 > 0, est.astype(np.float64) ** 2 / sumw2, 0.0)
        rse = np.where(n_alloc > 0, np.exp(build.alpha) * n_alloc ** build.beta, np.inf)
    n_gate = np.minimum(n_alloc, kish)
    cv_pct = rse * 100.0
    moe = 1.645 * rse * est

    universe = build.ranked_set
    suppressed = universe & ((n_gate < 100) | (cv_pct > 30) | (est <= 0) | (rivals <= 0))
    middle = universe & ~suppressed & (cv_pct > 20)
    ranked = universe & ~suppressed & ~middle

    w = weights or {}
    wp, wb = float(w.get("pool", 0.5)), float(w.get("balance", 0.5))
    tot = wp + wb
    assert tot > 0, "weights must not both be zero"
    wp, wb = wp / tot, wb / tot

    out = {"counts": {"universe": int(universe.sum()), "ranked": int(ranked.sum()),
                      "shown_unranked": int(middle.sum()),
                      "suppressed": int(suppressed.sum())},
           "weights": {"pool": wp, "balance": wb},
           "ranked": [], "shown_unranked": [], "suppressed": []}

    ridx = np.where(ranked)[0]
    if len(ridx):
        ratio = est[ridx] / rivals[ridx]
        z_pool = _winsor_minmax(est[ridx].astype(np.float64), log=True)
        z_bal = _winsor_minmax(ratio.astype(np.float64), log=False)
        score = wp * z_pool + wb * z_bal
        med_p, med_b = float(np.median(z_pool)), float(np.median(z_bal))
        order = np.argsort(-score, kind="stable")
        for k in order:
            i = ridx[k]
            out["ranked"].append({
                "cbsa": build.metro_levels[i], "title": build.titles[build.metro_levels[i]],
                "pool": round(float(est[i])), "pool_moe": round(float(moe[i])),
                "cv_pct": round(float(cv_pct[i]), 1),
                "n_alloc": round(float(n_alloc[i]), 1),
                "rivals": round(float(rivals[i])),
                "ratio": round(float(ratio[k]), 4),
                "score": round(float(score[k]), 6),
                "attribution": {
                    "pool": round(float(wp * (z_pool[k] - med_p)), 6),
                    "balance": round(float(wb * (z_bal[k] - med_b)), 6),
                },
            })
    for i in np.where(middle)[0]:
        out["shown_unranked"].append({
            "cbsa": build.metro_levels[i], "title": build.titles[build.metro_levels[i]],
            "pool": round(float(est[i])), "pool_moe": round(float(moe[i])),
            "cv_pct": round(float(cv_pct[i]), 1),
            "n_alloc": round(float(n_alloc[i]), 1),
            "rivals": round(float(rivals[i])),
            "ratio": round(float(est[i] / rivals[i]), 4) if rivals[i] > 0 else None,
        })
    for i in np.where(suppressed)[0]:
        reason = ("n_gate<100" if n_gate[i] < 100 else
                  "cv>30" if cv_pct[i] > 30 else
                  "empty_pool" if est[i] <= 0 else "no_rivals")
        out["suppressed"].append({
            "cbsa": build.metro_levels[i],
            "title": build.titles[build.metro_levels[i]], "reason": reason})
    return out
