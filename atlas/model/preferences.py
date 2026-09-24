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

D05 slider semantics survive as pool_vs_match (m3.0.0, ADR 0009): one
scalar dividing the people-mass between pool (0 = size) and match (1 =
chances of matching); pool_vs_balance is accepted as a deprecated alias
for exactly this version. The three-step importance controls scale the
context pillars through registry constants, and everything renormalizes
to sum to 1.

m3.0.0 also puts the assortative kernel's seeker side here: Kernel is the
shipped artifact (kernel.json + kernel.npz, loaded by loader.py) and
seeker_weights() turns the visitor's own sex, age and OPTIONAL education
and race/ethnicity into per-metro weight factors over the partner cells
(age x education x race) — the population-average marginal standing in
for whatever the visitor left unset. Pure numpy, no I/O.
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
PILLARS = ["pool", "match", "reach", "cost", "weather", "students"]
# m3.0.0: the slider control and its one-version deprecated alias
SLIDER_CONTROL = "pool_vs_match"
DEPRECATED_SLIDER_ALIAS = "pool_vs_balance"
KERNEL_COMPONENTS = ("age", "edu", "race")
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
    # m3.0.0: the two OPTIONAL seeker attributes, as cube level names
    # (None = not disclosed -> population-average marginal)
    self_edu: str | None = None
    self_race: str | None = None
    raw: dict = field(default_factory=dict, compare=False)


@dataclass
class SameSexTerms:
    """m3.2.0 (Phase 3b B3): the pairing terms fitted on same-sex couples,
    served to a same-sex search for the components in `components` (at
    dial 1); the others keep the opposite-sex term with the metro's dial.
    `log_norm` is the normaliser of exactly that served composition over
    the national single adults of the seeker's OWN sex."""
    f_age: np.ndarray            # (2, K_ss, 105)
    cohort_of_age: np.ndarray    # (53,)
    f_edu: np.ndarray            # (2, 4, 4)
    f_race: np.ndarray           # (2, 8, 8)
    log_norm: np.ndarray         # (n_metros, 2, 53, 4, 8)
    components: tuple[str, ...]


@dataclass
class Kernel:
    """The shipped assortative kernel (pipeline/build/kernel.py, refined by
    kernel_refine.py in m3.2.0). Log multipliers per component in the
    reporting gauge, a per-metro dial (power) per component, and the
    per-metro, per-seeker-type normaliser that makes exp(log w + log_norm)
    average exactly 1 over the national single adult population. m3.2.0:
    the age term is per seeker age cohort (K cohorts; a kernel_v1 artifact
    loads as one cohort), the education matrix is per seeker sex (a
    pooled matrix is stored twice), an optional race x education
    interaction rides undialled, and same-sex terms may be present."""
    f_age: np.ndarray        # (2, K, 105): seeker sex x cohort x (partner age - seeker age + gap_offset)
    f_edu: np.ndarray        # (2, 4, 4):  seeker sex x seeker edu x partner edu
    f_race: np.ndarray       # (2, 8, 8): seeker sex x seeker race x partner race
    dials: np.ndarray        # (n_metros, 3): theta per (age, edu, race); 1 = national
    log_norm: np.ndarray     # (n_metros, 2, 53, 4, 8)
    avail: np.ndarray        # (2, 53, 4, 8): national single adults by sex, age, edu, race
    gap_offset: int = 52
    dial_components: tuple[str, ...] = ()
    meta: dict = field(default_factory=dict)
    cohort_of_age: np.ndarray = field(default_factory=lambda: np.zeros(53, dtype=int))
    f_int: np.ndarray | None = None      # (2, 8, 8, 4, 4): seeker sex x race_s x race_c x edu_s x edu_c
    same_sex: SameSexTerms | None = None


def seeker_weights(k: Kernel, self_sex: str, self_age: int,
                   self_edu: str | None, self_race: str | None,
                   same_sex: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Per-metro kernel factors for one seeker: (age_vec, W) with
    age_vec[m, a_c] the age-gap multiplier by partner age and
    W[m, e_c, r_c] the education x race multiplier — the full weight over
    a partner cell is age_vec[m, a_c] * W[m, e_c, r_c].

    Degradation is the rule, not a special case: an undisclosed education
    or race is a MIXTURE over that attribute's levels with weights = the
    national single population of the seeker's own sex and age at each
    level (times the per-level normaliser, so each mixed-in kernel has
    mean 1). Both disclosed -> a single level; both unset -> the mixture
    over all 32 (education, race) combinations. All four combinations go
    through this one function.

    m3.2.0: the age term reads the seeker's cohort; the race x education
    interaction (when the artifact carries one) multiplies in; a SAME-SEX
    search takes each component the artifact lists from the same-sex fit
    at dial 1 and the rest from the opposite-sex fit with the metro's
    dial (the interaction rides only when both education and race stay
    opposite-sex), normalised by the same-sex normaliser."""
    si = SEX_LEVELS.index(self_sex)
    ai = int(self_age) - 18
    assert 0 <= ai < 53, "seeker age outside the cube"
    theta = k.dials                                            # (M, 3)
    gaps = np.arange(53) - ai + k.gap_offset
    ss = k.same_sex if same_sex else None
    if ss is not None and "age" in ss.components:
        fa = ss.f_age[si, ss.cohort_of_age[ai]][gaps]
        age_vec = np.repeat(np.exp(fa)[None, :], theta.shape[0], axis=0)
    else:
        fa = k.f_age[si, k.cohort_of_age[ai]][gaps]                # (53,)
        age_vec = np.exp(theta[:, 0:1] * fa[None, :])              # (M, 53)
    P = k.avail[si, ai].astype(np.float64).copy()              # (4, 8)
    if self_edu is not None:
        keep = np.zeros(4); keep[EDU_LEVELS.index(self_edu)] = 1.0
        P = P * keep[:, None]
    if self_race is not None:
        keep = np.zeros(8); keep[RACE_LEVELS.index(self_race)] = 1.0
        P = P * keep[None, :]
    if P.sum() <= 0:
        # a level with nobody single of this sex and age nationally: the
        # disclosed level(s) still select, uniformly over what is allowed
        P = np.ones((4, 8))
        if self_edu is not None:
            P *= np.eye(4)[EDU_LEVELS.index(self_edu)][:, None]
        if self_race is not None:
            P *= np.eye(8)[RACE_LEVELS.index(self_race)][None, :]
    P = P / P.sum()
    ln = ss.log_norm if ss is not None else k.log_norm
    mix = P[None, :, :] * np.exp(ln[:, si, ai].astype(np.float64))          # (M, 4, 8)
    M = theta.shape[0]
    if ss is not None and "edu" in ss.components:
        E = np.repeat(np.exp(ss.f_edu[si])[None, :, :], M, axis=0)           # (M, e_s, e_c)
    else:
        E = np.exp(theta[:, 1][:, None, None] * k.f_edu[si][None, :, :])
    if ss is not None and "race" in ss.components:
        R = np.repeat(np.exp(ss.f_race[si])[None, :, :], M, axis=0)          # (M, r_s, r_c)
    else:
        R = np.exp(theta[:, 2][:, None, None] * k.f_race[si][None, :, :])
    use_int = k.f_int is not None and not (
        ss is not None and ("edu" in ss.components or "race" in ss.components))
    if not use_int:
        W = np.einsum("mer,mef,mrg->mfg", mix, E, R)                         # (M, e_c, r_c)
    else:
        # G[r_s, r_c, e_s, e_c] -> (e_s, r_s, e_c, r_c); the full
        # (seeker level x partner cell) tensor is M x 4 x 8 x 4 x 8
        G = np.exp(k.f_int[si]).transpose(2, 0, 3, 1)
        T = (mix[:, :, :, None, None] * E[:, :, None, :, None]
             * R[:, None, :, None, :] * G[None, :, :, :, :])
        W = T.sum(axis=(1, 2))
    return age_vec, W


def _axis_vec(size: int, on: list[int]) -> np.ndarray:
    v = np.zeros(size, dtype=np.float32)
    v[on] = 1.0
    return v


def axis_vectors(sex: str, age_min: int, age_max: int,
                 marital_levels: frozenset[int],
                 education_min: str | None, income_min: int | None,
                 race_cube_levels: tuple[str, ...] | None
                 ) -> tuple[np.ndarray, ...]:
    """The six per-axis 0/1 vectors (sex, age, marital, education, income,
    race) one search selects — shared by the flattened mask and, since
    m3.0.0, by the kernel-weighted path, so the two can never disagree
    about which cells a search covers."""
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
    return s, a, m, e, i, r


def mask_vector(sex: str, age_min: int, age_max: int,
                marital_levels: frozenset[int],
                education_min: str | None, income_min: int | None,
                race_cube_levels: tuple[str, ...] | None) -> np.ndarray:
    s, a, m, e, i, r = axis_vectors(sex, age_min, age_max, marital_levels,
                                    education_min, income_min, race_cube_levels)
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
    # m3.0.0: the optional seeker attributes; neither is ever required
    self_edu = self_.get("education")
    if self_edu is not None and self_edu not in EDU_LEVELS:
        raise ValueError(f"self.education must be one of {EDU_LEVELS}")
    self_race = self_.get("race_ethnicity")
    if self_race is not None:
        if self_race not in SPEC_RACE:
            raise ValueError(f"self.race_ethnicity must be one of {list(SPEC_RACE)}")
        self_race = SPEC_RACE[self_race]
    return Request(self_sex=self_["sex"], self_age=int(self_["age"]),
                   seeking=spec, weights=dict(body.get("weights") or {}),
                   pinned_data_version=body.get("data_version"),
                   pinned_model_version=body.get("model_version"),
                   self_edu=self_edu, self_race=self_race, raw=body)


def slider_weights(s: float, defaults: dict[str, float],
                   mass: float) -> dict[str, float]:
    """One scalar dividing the people-mass: s=0 puts it on pool (size),
    s=1 on match (chances of matching). Identical mechanics to the
    m2.x pool_vs_balance control (ADR 0009)."""
    assert 0.0 <= s <= 1.0, f"{SLIDER_CONTROL} must be in [0,1]"
    w = {k: v for k, v in defaults.items() if k not in ("pool", "match")}
    w["pool"] = mass * (1.0 - s)
    w["match"] = mass * s
    return w


def slider_value(raw: dict) -> float | None:
    """The slider's value from a request body: pool_vs_match, or the
    deprecated pool_vs_balance alias (exactly m3.0.0); naming both is a
    contradiction and raises."""
    new = raw.get(SLIDER_CONTROL)
    old = raw.get(DEPRECATED_SLIDER_ALIAS)
    if new is not None and old is not None:
        raise ValueError(
            f"{DEPRECATED_SLIDER_ALIAS} is the deprecated name for "
            f"{SLIDER_CONTROL}; send one or the other, not both")
    return new if new is not None else old


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
    """Explicit weights win; else the v3 controls (pool_vs_match +
    importance); else defaults. Normalized to sum to 1. pool_vs_balance
    is accepted as a deprecated alias for exactly m3.0.0 (ADR 0009), the
    way size_vs_odds was for m2.0.0; size_vs_odds itself is gone."""
    defaults = dict(manifest_defaults["pillar_weights"])
    svo = manifest_defaults["size_vs_odds"]
    raw = req.raw
    slider = slider_value(raw)
    knobs = [k for k in ("weights",) if k in raw and raw[k] is not None]
    if slider is not None:
        knobs.append(SLIDER_CONTROL)
    if "weights" in knobs and (len(knobs) > 1 or "importance" in raw):
        raise ValueError("pass either weights or the named controls, not both")
    if "size_vs_odds" in raw and raw["size_vs_odds"] is not None:
        raise ValueError(
            f"size_vs_odds left the contract in m2.1.0; send {SLIDER_CONTROL}")
    if slider is not None or "importance" in raw:
        s = float(slider if slider is not None else svo["default_s"])
        if not 0.0 <= s <= 1.0:
            raise ValueError(f"{SLIDER_CONTROL} must be in [0,1]")
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
                                 SLIDER_CONTROL, "importance")
            if k in body}
    # the deprecated alias encodes as the canonical control, so one
    # search has one permalink whichever name the client sent
    if SLIDER_CONTROL not in core and body.get(DEPRECATED_SLIDER_ALIAS) is not None:
        core[SLIDER_CONTROL] = body[DEPRECATED_SLIDER_ALIAS]
    blob = json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    tok = base64.urlsafe_b64encode(blob).decode().rstrip("=")
    return f"/r/{data_version}/{model_version}/{tok}"
