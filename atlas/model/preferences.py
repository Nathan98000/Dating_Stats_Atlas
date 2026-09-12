"""Preferences -> cube masks and canonical request handling. Pure; no I/O.

Speaks the §8.2 contract's vocabulary (self/seeking, spec race names like
"black_nh", marital as a list of levels) and turns it into flat 0/1 mask
vectors over the per-metro cell space, plus the derived symmetric rival
window (Phase 1 correction 4: rivals carry the pool's marital screen and
education floor; no income floor, no race screen — the pairing kernel is
Phase 3).

D05 slider: slider_weights(s, defaults) reallocates the pool+balance mass
between pool (s=0, most options) and balance (s=1, best odds); context
pillar weights are untouched. The mass and default weights come from the
build manifest, whose source of truth is the feature registry.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

SEX_LEVELS = ["male", "female"]
MARITAL_LEVELS = ["never", "previously", "currently"]
EDU_LEVELS = ["hs_or_less", "some_college", "bachelors", "graduate"]
INC_LEVELS = ["lt25k", "25_50k", "50_75k", "75_100k", "100_150k", "150_250k", "ge250k"]
RACE_LEVELS = ["hispanic", "nh_white", "nh_black", "nh_asian", "nh_aian",
               "nh_nhpi", "nh_twoplus", "nh_other"]
INCOME_FLOORS = {25_000: 1, 50_000: 2, 75_000: 3, 100_000: 4, 150_000: 5, 250_000: 6}

# §8.2 vocabulary <-> cube levels
SPEC_RACE = {"hispanic": "hispanic", "white_nh": "nh_white",
             "black_nh": "nh_black", "asian_nh": "nh_asian",
             "aian_nh": "nh_aian", "nhpi_nh": "nh_nhpi",
             "two_or_more_nh": "nh_twoplus", "other_nh": "nh_other"}
SPEC_MARITAL = {"never_married": 0, "previously_married": 1,
                "currently_married": 2}
PILLARS = ["pool", "balance", "reach", "cost", "lifestyle"]

N_FLAT = 2 * 53 * 3 * 4 * 7 * 8  # per-metro cells


@dataclass(frozen=True)
class PoolSpec:
    sex: str
    age_min: int
    age_max: int
    marital_levels: frozenset[int]
    education_min: str | None = None
    income_min: int | None = None
    race_cube_levels: tuple[str, ...] | None = None   # cube names


@dataclass(frozen=True)
class Request:
    self_sex: str
    self_age: int
    seeking: PoolSpec
    weights: dict[str, float]
    pinned_data_version: str | None = None
    pinned_model_version: str | None = None
    raw: dict = field(default_factory=dict, compare=False)


def _axis_vec(size: int, on: list[int]) -> np.ndarray:
    v = np.zeros(size, dtype=np.float32)
    v[on] = 1.0
    return v


def mask_vector(sex: str, age_min: int, age_max: int,
                marital_levels: frozenset[int],
                education_min: str | None, income_min: int | None,
                race_cube_levels: tuple[str, ...] | None) -> np.ndarray:
    assert sex in SEX_LEVELS, f"sex must be one of {SEX_LEVELS}"
    assert marital_levels and marital_levels <= {0, 1, 2}, "empty marital set"
    a0, a1 = max(18, int(age_min)), min(70, int(age_max))
    assert a0 <= a1, "empty age range"
    s = _axis_vec(2, [SEX_LEVELS.index(sex)])
    a = _axis_vec(53, list(range(a0 - 18, a1 - 18 + 1)))
    m = _axis_vec(3, sorted(marital_levels))
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
    if race_cube_levels is None:
        r = np.ones(8, dtype=np.float32)
    else:
        assert race_cube_levels, "empty race filter"
        idx = []
        for rl in race_cube_levels:
            assert rl in RACE_LEVELS, f"unknown race level {rl!r}"
            idx.append(RACE_LEVELS.index(rl))
        r = _axis_vec(8, idx)
    # Output order MUST be the cube's axis order (sex, age, marital,
    # education, income, race). Phase 1 shipped "samier" here — income and
    # education transposed in the flattened mask — which silently scrambled
    # every cube query with a partial education or income filter while
    # leaving unfiltered axes intact. test_mask_axis_semantics pins this.
    return np.einsum("s,a,m,e,i,r->sameir", s, a, m, e, i, r).ravel()


def pool_mask(spec: PoolSpec) -> np.ndarray:
    return mask_vector(spec.sex, spec.age_min, spec.age_max, spec.marital_levels,
                       spec.education_min, spec.income_min, spec.race_cube_levels)


def rival_spec(req: Request) -> PoolSpec:
    """Symmetric crude rivals (Phase 1 correction 4)."""
    return PoolSpec(sex=req.self_sex,
                    age_min=max(18, req.self_age - 5),
                    age_max=min(70, req.self_age + 5),
                    marital_levels=req.seeking.marital_levels,
                    education_min=req.seeking.education_min,
                    income_min=None, race_cube_levels=None)


def parse_request(body: dict) -> Request:
    """§8.2 request body -> typed Request. Raises ValueError on bad input."""
    self_ = body["self"]
    seeking = body["seeking"]
    sex = seeking.get("sex") or SEX_LEVELS[1 - SEX_LEVELS.index(self_["sex"])]
    age = seeking["age"]
    marital = seeking.get("marital")
    if not marital:
        raise ValueError("seeking.marital must list at least one status")
    levels = frozenset(SPEC_MARITAL[m] for m in marital)
    race = seeking.get("race_ethnicity")
    race_levels = tuple(SPEC_RACE[r] for r in race) if race else None
    if seeking.get("religion") is not None:
        raise ValueError("religion is the modelled tier and ships in Phase 4")
    spec = PoolSpec(sex=sex, age_min=int(age[0]), age_max=int(age[1]),
                    marital_levels=levels,
                    education_min=seeking.get("education_min"),
                    income_min=seeking.get("income_min"),
                    race_cube_levels=race_levels)
    return Request(self_sex=self_["sex"], self_age=int(self_["age"]),
                   seeking=spec, weights=dict(body.get("weights") or {}),
                   pinned_data_version=body.get("data_version"),
                   pinned_model_version=body.get("model_version"), raw=body)


def slider_weights(s: float, defaults: dict[str, float],
                   mass: float) -> dict[str, float]:
    """D05: one scalar -> a full weight vector. s=0 puts the pool+balance
    mass on pool (most options); s=1 puts it on balance (best odds)."""
    assert 0.0 <= s <= 1.0, "size_vs_odds must be in [0,1]"
    w = {k: v for k, v in defaults.items() if k not in ("pool", "balance")}
    w["pool"] = mass * (1.0 - s)
    w["balance"] = mass * s
    return w


def resolve_weights(req: Request, manifest_defaults: dict) -> dict[str, float]:
    """Explicit weights win; else the size_vs_odds slider; else defaults.
    Weights are normalized to sum to 1 over the five pillars."""
    defaults = dict(manifest_defaults["pillar_weights"])
    svo = manifest_defaults["size_vs_odds"]
    if req.weights and "size_vs_odds" in req.raw:
        raise ValueError("pass either weights or size_vs_odds, not both")
    if "size_vs_odds" in req.raw:
        w = slider_weights(float(req.raw["size_vs_odds"]), defaults,
                           float(svo["pool_plus_balance_mass"]))
    elif req.weights:
        w = {p: float(req.weights.get(p, 0.0)) for p in PILLARS}
    else:
        w = defaults
    tot = sum(w.values())
    if tot <= 0:
        raise ValueError("weights must not all be zero")
    return {p: w.get(p, 0.0) / tot for p in PILLARS}


def permalink(data_version: str, model_version: str, body: dict) -> str:
    """Deterministic, reproducible permalink (§5.4): both version pins plus
    the canonical preference vector, base64url-encoded."""
    import base64
    import json
    core = {k: body[k] for k in ("self", "seeking", "weights", "size_vs_odds")
            if k in body}
    blob = json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    tok = base64.urlsafe_b64encode(blob).decode().rstrip("=")
    return f"/r/{data_version}/{model_version}/{tok}"
