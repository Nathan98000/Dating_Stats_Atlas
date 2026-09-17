"""Ranking endpoint — thin transport over atlas.model, m2.0.0 (ADR 0004).
Single process, one build loaded at boot, cubes in memory, never writes.
Same-origin posture: no CORS middleware, loopback bind, no public API
(D04) — the site reaches this only through its own server-side proxy.

When BUILD_DIR is unset, the fallback loads the single complete build under
data/builds — and REFUSES to guess when more than one is present.

Contract, m2.0.0 (second breaking change after ADR 0003's comparator
removal — both noted here as the contract docs):
  - REMOVED from rows: ratio, ratio_moe, rivals (the rival apparatus left
    the model), cross_group_pairing_rate and its display fields (race
    filters carry no claim about who partners with whom), explanation
    (replaced by summary_line), n_below_100-era reason "no_rivals".
  - ADDED: balance {available, value, per_100, display, standing} — the
    plain sex ratio, gated separately from the pool, present on ranked AND
    suppressed rows; score_display; summary_line; cards (the v3 city-page
    stat cards with national standing bands); display_name / slug per
    metro; counts by reason.
  - marital accepts only never_married / previously_married; the cube
    keeps its third level.
  - weights come from named controls: {pool_vs_balance: 0..1, importance:
    {cost|reach|lifestyle: not_much|some|a_lot}}, mapped through registry
    constants server-side. size_vs_odds stays accepted-but-deprecated for
    exactly this version. Explicit weight vectors still win.
  - pool_moe and cv are STILL returned (the interval machinery is intact;
    Gate 0's bound stays in the manifest) — they are simply never rendered
    by the site. Technical wording lives under /v1/meta technical_strings.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from atlas import model as engine
from atlas.model.preferences import ALLOWED_MARITAL, SELECTABLE_RACES
from atlas.model.suppression import (FEW_METROS_NOTICE, GQ_SHARE_FLAG_BAR,
                                     N_GATE_MIN, POLICY_STRINGS,
                                     PURITY_FLAG_BAR, TECHNICAL_STRINGS)

BUILDS_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "builds"


def _resolve_build_dir() -> Path:
    env = os.environ.get("BUILD_DIR")
    if env:
        return Path(env)
    complete = sorted(
        p for p in BUILDS_DEFAULT.iterdir()
        if p.is_dir() and (p / "manifest.json").exists()
        and ((p / "pool_cube.npy").exists() or (p / "fixture.npz").exists()))
    if not complete:
        raise RuntimeError(f"no complete builds under {BUILDS_DEFAULT}; "
                           f"set BUILD_DIR")
    if len(complete) > 1:
        raise RuntimeError(
            "multiple complete builds present: "
            + ", ".join(p.name for p in complete)
            + " — refusing to guess; set BUILD_DIR to the one to serve")
    return complete[0]


BUILD = engine.load_build(_resolve_build_dir())
_METROS_META = json.loads((BUILD.path / "metros.json").read_text())
app = FastAPI(title="Dating Stats Atlas ranking", docs_url=None, redoc_url=None)


class SelfSpec(BaseModel):
    sex: Literal["male", "female"]
    age: int = Field(ge=18, le=70)
    education: Optional[Literal[tuple(engine.EDU_LEVELS)]] = None  # type: ignore[valid-type]
    race_ethnicity: Optional[Literal[tuple(engine.SPEC_RACE)]] = None  # type: ignore[valid-type]


class SeekingSpec(BaseModel):
    sex: Optional[Literal["male", "female"]] = None
    age: tuple[int, int]
    education_min: Optional[Literal["some_college", "bachelors", "graduate"]] = None
    income_min: Optional[int] = None
    # m2.0.0: the site counts single people only (ADR 0004)
    marital: list[Literal[tuple(ALLOWED_MARITAL)]]                 # type: ignore[valid-type]
    # only the six selectable groups arrive here; the two always-counted
    # groups are ORed in by the model (preferences.resolve_race_levels)
    race_ethnicity: Optional[list[Literal[tuple(SELECTABLE_RACES)]]] = None  # type: ignore[valid-type]
    religion: Optional[str] = None

    @model_validator(mode="after")
    def _check(self):
        lo, hi = self.age
        if not (18 <= lo <= hi <= 70):
            raise ValueError("seeking.age must satisfy 18 <= lo <= hi <= 70")
        if self.income_min is not None and self.income_min not in engine.INCOME_FLOORS:
            raise ValueError(
                f"income_min must be a cube band edge: {sorted(engine.INCOME_FLOORS)}")
        if not self.marital:
            raise ValueError("seeking.marital must list at least one status")
        if self.religion is not None:
            raise ValueError("religion is the modelled tier and ships in Phase 4")
        return self


class Weights(BaseModel):
    # defaults are float literals: pydantic keeps a default's type, so an
    # int 0 here would make the canonical permalink JSON render "0" for
    # defaulted pillars and "0.0" for user-sent ones — two encodings of the
    # same request. The shared permalink test (web/tests) pins this.
    pool: float = Field(ge=0, default=0.0)
    balance: float = Field(ge=0, default=0.0)
    reach: float = Field(ge=0, default=0.0)
    cost: float = Field(ge=0, default=0.0)
    lifestyle: float = Field(ge=0, default=0.0)


class Importance(BaseModel):
    cost: Literal["not_much", "some", "a_lot"] = "some"
    reach: Literal["not_much", "some", "a_lot"] = "some"
    lifestyle: Literal["not_much", "some", "a_lot"] = "some"


class RankRequest(BaseModel):
    data_version: Optional[str] = None
    model_version: Optional[str] = None
    self: SelfSpec
    seeking: SeekingSpec
    weights: Optional[Weights] = None
    pool_vs_balance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    importance: Optional[Importance] = None
    # deprecated alias for pool_vs_balance, accepted for m2.0.0 only
    size_vs_odds: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sort: Literal["best_first", "worst_first"] = "best_first"

    @model_validator(mode="after")
    def _check(self):
        named = (self.pool_vs_balance is not None
                 or self.importance is not None)
        if self.weights is not None and (named or self.size_vs_odds is not None):
            raise ValueError("pass either weights or the named controls, not both")
        if self.size_vs_odds is not None and named:
            raise ValueError(
                "size_vs_odds is the deprecated name for pool_vs_balance; "
                "send one, not both")
        if self.weights is not None and sum(
                self.weights.model_dump().values()) <= 0:
            raise ValueError("weights must not all be zero")
        return self


@app.get("/v1/health")
def health() -> dict:
    return {"status": "ok",
            "data_version": BUILD.manifest["data_version"],
            "model_version": engine.MODEL_VERSION,
            "schema_version": BUILD.manifest["schema_version"],
            "metros": len(BUILD.metro_levels),
            "ranked_set": int(BUILD.ranked_set.sum()),
            "interval": BUILD.manifest["interval_model"]["validation"]}


@app.get("/v1/meta")
def meta() -> dict:
    """Display legend, policy wording, provenance and control vocabulary —
    the single source every rendered label and sentence comes from
    (ADR 0003/0004: no user-facing label lives in code, frontend
    included)."""
    m = BUILD.manifest
    return {
        "data_version": m["data_version"],
        "model_version": engine.MODEL_VERSION,
        "schema_version": m["schema_version"],
        "pillars": m["pillars"],
        "pillar_order": engine.PILLARS,
        "features": m["features_block"],
        "policy_strings": POLICY_STRINGS,
        "technical_strings": TECHNICAL_STRINGS,
        "tier_policy": m["tier_policy"],
        "standing_bands": m["standing_bands"],
        "city_cards": m["city_cards"],
        "interval_model": {k: m["interval_model"][k] for k in
                           ("mechanism", "validation", "copy_rule")},
        "licenses": m.get("licenses", {}),
        "thresholds": {"n_gate_min": N_GATE_MIN,
                       "purity_flag_bar": PURITY_FLAG_BAR,
                       "gq_share_flag_bar": GQ_SHARE_FLAG_BAR,
                       "few_metros_notice": FEW_METROS_NOTICE},
        "controls": {
            "income_band_edges": sorted(engine.INCOME_FLOORS),
            "education_levels": engine.EDU_LEVELS,
            "marital": list(ALLOWED_MARITAL),
            "race_ethnicity": list(SELECTABLE_RACES),
            "importance_levels": list(m["model_defaults"]["importance_levels"]),
            "age": [18, 70],
        },
        "sources": m["sources"],
        "metros": [{"cbsa": c,
                    "title": BUILD.titles[c],
                    "display_name": BUILD.display_names[i],
                    "display_name_full": BUILD.display_names_full[i],
                    "slug": BUILD.slugs[i],
                    "description": BUILD.descriptions[i],
                    "lat": _METROS_META[i].get("lat"),
                    "lon": _METROS_META[i].get("lon"),
                    "ranked_set": bool(BUILD.ranked_set[i])}
                   for i, c in enumerate(BUILD.metro_levels)],
    }


@app.post("/v1/rank")
def rank(req: RankRequest) -> dict:
    dv = BUILD.manifest["data_version"]
    if req.data_version and req.data_version != dv:
        raise HTTPException(409, f"data_version {req.data_version!r} not loaded "
                                 f"(this process serves {dv!r})")
    if req.model_version and req.model_version != engine.MODEL_VERSION:
        raise HTTPException(409, f"model_version {req.model_version!r} != "
                                 f"{engine.MODEL_VERSION!r}")
    body = req.model_dump(exclude_none=True)
    sort = body.pop("sort", "best_first")
    try:
        parsed = engine.parse_request(body)
        result = engine.rank(BUILD, parsed)
    except (ValueError, AssertionError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if sort == "worst_first":
        # a reversal of the same ranked array: same cities, same scores,
        # same ranks — never widened to fill the bottom (ADR 0004)
        result["ranked"] = list(reversed(result["ranked"]))
    result["sort"] = sort
    return {"data_version": dv, "model_version": engine.MODEL_VERSION,
            "permalink": engine.permalink(dv, engine.MODEL_VERSION, body),
            **result}
