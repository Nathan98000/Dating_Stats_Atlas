"""Preferences -> cube masks. Pure functions over the axis level definitions;
no I/O anywhere in this module.

A pool or rival filter becomes a flat 0/1 float32 vector over the per-metro
cell space (sex x age x marital x education x income x race_eth), so a pool
query is a single matrix-vector product per cube.
"""
from __future__ import annotations

import numpy as np

SEX_LEVELS = ["male", "female"]
MARITAL_LEVELS = ["never", "previously", "currently"]
EDU_LEVELS = ["hs_or_less", "some_college", "bachelors", "graduate"]
INC_LEVELS = ["lt25k", "25_50k", "50_75k", "75_100k", "100_150k", "150_250k", "ge250k"]
RACE_LEVELS = ["hispanic", "nh_white", "nh_black", "nh_asian", "nh_aian",
               "nh_nhpi", "nh_twoplus", "nh_other"]
INCOME_FLOORS = {25_000: 1, 50_000: 2, 75_000: 3, 100_000: 4, 150_000: 5, 250_000: 6}
MARITAL_SETS = {"never": [0], "not_married": [0, 1], "any": [0, 1, 2]}

N_FLAT = 2 * 53 * 3 * 4 * 7 * 8  # per-metro cells


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
