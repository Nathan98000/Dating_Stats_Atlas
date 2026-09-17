"""Preferences -> cube masks and canonical request handling. Pure; no I/O.

Speaks the contract's vocabulary (self/seeking, spec race names like
"black_nh", marital as a list of levels) and turns it into flat 0/1 mask
vectors over the per-metro cell space.

m2.0.0 (ADR 0004):
  - balance_masks() replaces the symmetric-rivals apparatus: dating pool
    balance is the plain sex ratio of single adults in the SEEKING age
    range — sought sex over seeker sex, same ages, same marital selection,
    never filtered by race, education or income. seeking.age is used for
    both sexes: the simple, explainable choice (a union with the seeker's
    own ±5 window was considered and rejected — it would make the figure
    move when the seeker's age moves, which is exactly the instability the
    redefinition removes).
  - The API accepts only never_married and previously_married; the cube
    keeps its third (currently-married) level untouched.

m2.2.0 (ADR 0006, reversing ADR 0004's always-counted rule): race and
ethnicity are EIGHT equal checkboxes. A selection filters the pool to
exactly the ticked groups and adds nothing — a control whose arithmetic
the visitor can check beats one that quietly counts people they did not
tick. Zero ticked or all eight ticked means no filter at all (the same
universe either way). Race enters the pool and nothing else:
balance_masks stays race-blind on purpose.

D05 slider semantics survive as pool_vs_balance: one scalar dividing the
people-mass between pool (0 = size) and balance (1 = balance); the
three-step importance controls scale the context pillars through registry
constants, and everything renormalizes to sum to 1.
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

# spec vocabulary <-> cube levels
SPEC_RACE = {"hispanic": "hispanic", "white_nh": "nh_white",
             "black_nh": "nh_black", "asian_nh": "nh_asian",
             "aian_nh": "nh_aian", "nhpi_nh": "nh_nhpi",
             "two_or_more_nh": "nh_twoplus", "other_nh": "nh_other"}
# m2.2.0: all eight groups are ordinary checkboxes — one rule, no
# special casing (ADR 0006 reversed ADR 0004's two always-counted groups)
SELECTABLE_RACES = ("hispanic", "white_nh", "black_nh", "asian_nh",
                    "aian_nh", "nhpi_nh", "two_or_more_nh", "other_nh")
SPEC_MARITAL = {"never_married": 0, "previously_married": 1,
                "currently_married": 2}
# m2.0.0: the site offers exactly two meanings of single (ADR 0004)
ALLOWED_MARITAL = ("never_married", "previously_married")
# m2.1.0 (Phase 2d item 4): lifestyle split into weather and students so
# each carries its own importance control — six pillars, four controls.
PILLARS = ["pool", "balance", "reach", "cost", "weather", "students"]
IMPORTANCE_PILLARS = ("cost", "reach", "students", "weather")
# the old bundled control, accepted as a deprecated alias for exactly one
# version: its level applies to BOTH split pillars, which reproduces the
# m2.0.0 behaviour it named
DEPRECATED_IMPORTANCE_ALIAS = {"lifestyle": ("weather", "students")}

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


def balance_masks(req: Request) -> tuple[np.ndarray, np.ndarray]:
    """(sought mask, seeker mask) for dating pool balance (ADR 0004): the
    plain sex ratio of single adults in the SEEKING age range. Both masks
    carry only sex, seeking.age and the marital selection — race, education
    and income never touch balance, deliberately, so the figure means what
    its name says and stays put as filters move."""
    seek = req.seeking
    sought = mask_vector(seek.sex, seek.age_min, seek.age_max,
                         seek.marital_levels, None, None, None)
    seeker = mask_vector(req.self_sex, seek.age_min, seek.age_max,
                         seek.marital_levels, None, None, None)
    return sought, seeker


def resolve_race_levels(selected: list[str] | None) -> tuple[str, ...] | None:
    """m2.2.0 (ADR 0006): the selection IS the filter — exactly the
    ticked groups, nothing added. Zero ticked or all eight ticked means
    no filter at all (the identical universe, spelled two ways)."""
    if not selected:
        return None
    for r in selected:
        assert r in SPEC_RACE, f"unknown race {r!r}"
    if set(selected) >= set(SELECTABLE_RACES):
        return None
    return tuple(dict.fromkeys(SPEC_RACE[r] for r in selected))


def parse_request(body: dict) -> Request:
    """Contract request body -> typed Request. Raises ValueError on bad
    input."""
    self_ = body["self"]
    seeking = body["seeking"]
    sex = seeking.get("sex") or SEX_LEVELS[1 - SEX_LEVELS.index(self_["sex"])]
    age = seeking["age"]
    marital = seeking.get("marital")
    if not marital:
        raise ValueError("seeking.marital must list at least one status")
    for m in marital:
        if m not in ALLOWED_MARITAL:
            raise ValueError(
                "marital status must be never_married or previously_married "
                "— the site counts single people only (ADR 0004)")
    levels = frozenset(SPEC_MARITAL[m] for m in marital)
    race_levels = resolve_race_levels(seeking.get("race_ethnicity"))
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
    """One scalar dividing the people-mass: s=0 puts it on pool (size),
    s=1 on balance."""
    assert 0.0 <= s <= 1.0, "pool_vs_balance must be in [0,1]"
    w = {k: v for k, v in defaults.items() if k not in ("pool", "balance")}
    w["pool"] = mass * (1.0 - s)
    w["balance"] = mass * s
    return w


def resolve_importance_levels(importance: dict[str, str]) -> dict[str, str]:
    """The four named controls, with the m2.0.0 'lifestyle' control
    accepted as a deprecated alias for exactly one version: its level
    applies to both split pillars (reproducing what it used to mean).
    Naming lifestyle AND either of its halves is a contradiction and
    raises."""
    out = {k: v for k, v in importance.items() if k in IMPORTANCE_PILLARS}
    unknown = [k for k in importance
               if k not in IMPORTANCE_PILLARS
               and k not in DEPRECATED_IMPORTANCE_ALIAS]
    if unknown:
        raise ValueError(
            f"unknown importance controls {sorted(unknown)}; "
            f"the controls are {sorted(IMPORTANCE_PILLARS)}")
    for alias, targets in DEPRECATED_IMPORTANCE_ALIAS.items():
        if alias in importance:
            clash = [t for t in targets if t in importance]
            if clash:
                raise ValueError(
                    f"importance.{alias} is the deprecated name for "
                    f"{' and '.join(targets)}; send one or the other, "
                    f"not both")
            for t in targets:
                out[t] = importance[alias]
    return out


def importance_weights(s: float, importance: dict[str, str],
                       manifest_defaults: dict) -> dict[str, float]:
    """The v3 home-page controls -> a full weight vector, entirely from
    registry constants (the frontend sends choices, never weights): the
    context pillars scale by the level multiplier, the people-mass splits
    by the slider, and the result renormalizes to sum to 1. 'Not much' is
    a small floor rather than zero — nothing showed zeroing a pillar
    leaves the ranking sane, and the floor keeps every stat's contribution
    explainable."""
    defaults = dict(manifest_defaults["pillar_weights"])
    mass = float(manifest_defaults["size_vs_odds"]["pool_plus_balance_mass"])
    mult = manifest_defaults["importance_levels"]
    levels = resolve_importance_levels(importance)
    w = slider_weights(s, defaults, mass)
    for p in IMPORTANCE_PILLARS:
        level = levels.get(p, "some")
        if level not in mult:
            raise ValueError(f"importance.{p} must be one of {sorted(mult)}")
        w[p] = defaults[p] * float(mult[level])
    return w


def resolve_weights(req: Request, manifest_defaults: dict) -> dict[str, float]:
    """Explicit weights win; else the v3 controls (pool_vs_balance +
    importance); else defaults. Normalized to sum to 1. The size_vs_odds
    alias was accepted-but-deprecated for exactly m2.0.0 (ADR 0004) and is
    gone in m2.1.0 — the transport rejects it before this runs."""
    defaults = dict(manifest_defaults["pillar_weights"])
    svo = manifest_defaults["size_vs_odds"]
    raw = req.raw
    knobs = [k for k in ("weights", "pool_vs_balance")
             if k in raw and raw[k] is not None]
    if "weights" in knobs and (len(knobs) > 1 or "importance" in raw):
        raise ValueError("pass either weights or the named controls, not both")
    if "size_vs_odds" in raw and raw["size_vs_odds"] is not None:
        raise ValueError(
            "size_vs_odds left the contract in m2.1.0; send pool_vs_balance")
    if "pool_vs_balance" in knobs or "importance" in raw:
        s = float(raw.get("pool_vs_balance", svo["default_s"]))
        if not 0.0 <= s <= 1.0:
            raise ValueError("pool_vs_balance must be in [0,1]")
        w = importance_weights(s, dict(raw.get("importance") or {}),
                               manifest_defaults)
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
    the canonical preference vector, base64url-encoded. No permalink
    renders in the UI (ADR 0004), but the property stays load-bearing:
    every ranking the API ever serves remains reproducible."""
    import base64
    import json
    core = {k: body[k] for k in ("self", "seeking", "weights",
                                 "pool_vs_balance", "importance")
            if k in body}
    blob = json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    tok = base64.urlsafe_b64encode(blob).decode().rstrip("=")
    return f"/r/{data_version}/{model_version}/{tok}"
