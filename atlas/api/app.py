"""Ranking endpoint — thin transport over atlas.model, speaking the §8.2
contract as amended by ADRs 0002/0003. Single process, one build loaded at
boot, cubes in memory, never writes. Same-origin posture: no CORS
middleware, loopback bind, no public API (D04) — the site reaches this only
through its own server-side proxy.

    BUILD_DIR=/path/to/builds/<data_version> uvicorn atlas.api.app:app \
        --host 127.0.0.1

When BUILD_DIR is unset, the fallback loads the single complete build under
data/builds — and REFUSES to guess when more than one is present. Serving a
build by accident of file timestamps is the same class of failure as the
Phase 1 mask bug: a silent choice where an explicit one is owed.

Documented deviations from the §8.2 sketch:
  - `comparator` is REMOVED (ADR 0003 retires D10). Everything else is
    additive: rivals, ratio_moe, flags (low_allocation_purity, gq_flag,
    missing_features), n_unweighted = min(allocated, Kish), the rendered
    `explanation`, a full per-metro `stats` block (metro and compare pages
    render from one response, preserving per-query normalization), counts
    by suppression reason, and — with a race filter — the interim
    cross-group pairing rate with its replicate-measured margin.
  - `shown_unranked` is a permanently empty array (ADR 0002); the
    cv_above_20 / cv_above_30 reason strings can no longer be produced.
  - `size_vs_odds` is accepted as the D05 slider alternative to weights.
  - GET /v1/meta serves the display legend, policy strings and provenance
    records so no user-facing label or wording lives in frontend code.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from atlas import model as engine
from atlas.model.preferences import SPEC_MARITAL, SPEC_RACE
from atlas.model.suppression import (FEW_METROS_NOTICE, GQ_SHARE_FLAG_BAR,
                                     N_GATE_MIN, POLICY_STRINGS,
                                     PURITY_FLAG_BAR)

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
app = FastAPI(title="Dating Stats Atlas ranking", docs_url=None, redoc_url=None)


class SelfSpec(BaseModel):
    sex: Literal["male", "female"]
    age: int = Field(ge=18, le=70)
    education: Optional[Literal[tuple(engine.EDU_LEVELS)]] = None  # type: ignore[valid-type]
    race_ethnicity: Optional[Literal[tuple(SPEC_RACE)]] = None     # type: ignore[valid-type]


class SeekingSpec(BaseModel):
    sex: Optional[Literal["male", "female"]] = None
    age: tuple[int, int]
    education_min: Optional[Literal["some_college", "bachelors", "graduate"]] = None
    income_min: Optional[int] = None
    marital: list[Literal[tuple(SPEC_MARITAL)]]                    # type: ignore[valid-type]
    race_ethnicity: Optional[list[Literal[tuple(SPEC_RACE)]]] = None  # type: ignore[valid-type]
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
    pool: float = Field(ge=0, default=0)
    balance: float = Field(ge=0, default=0)
    reach: float = Field(ge=0, default=0)
    cost: float = Field(ge=0, default=0)
    lifestyle: float = Field(ge=0, default=0)


class RankRequest(BaseModel):
    data_version: Optional[str] = None
    model_version: Optional[str] = None
    self: SelfSpec
    seeking: SeekingSpec
    weights: Optional[Weights] = None
    size_vs_odds: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check(self):
        if self.weights is not None and self.size_vs_odds is not None:
            raise ValueError("pass either weights or size_vs_odds, not both")
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
    the single source every rendered label and margin sentence comes from
    (ADR 0003: no user-facing label lives in code, frontend included)."""
    m = BUILD.manifest
    return {
        "data_version": m["data_version"],
        "model_version": engine.MODEL_VERSION,
        "schema_version": m["schema_version"],
        "pillars": m["pillars"],
        "pillar_order": engine.PILLARS,
        "features": m["features_block"],
        "policy_strings": POLICY_STRINGS,
        "tier_policy": m["tier_policy"],
        "interval_model": {k: m["interval_model"][k] for k in
                           ("mechanism", "validation", "copy_rule")},
        "model_defaults": m["model_defaults"],
        "thresholds": {"n_gate_min": N_GATE_MIN,
                       "purity_flag_bar": PURITY_FLAG_BAR,
                       "gq_share_flag_bar": GQ_SHARE_FLAG_BAR,
                       "few_metros_notice": FEW_METROS_NOTICE},
        "controls": {
            "income_band_edges": sorted(engine.INCOME_FLOORS),
            "education_levels": engine.EDU_LEVELS,
            "marital": list(engine.SPEC_MARITAL),
            "race_ethnicity": list(engine.SPEC_RACE),
            "age": [18, 70],
        },
        "sources": m["sources"],
        "metros": [{"cbsa": c, "title": BUILD.titles[c],
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
    try:
        parsed = engine.parse_request(body)
        result = engine.rank(BUILD, parsed)
    except (ValueError, AssertionError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"data_version": dv, "model_version": engine.MODEL_VERSION,
            "permalink": engine.permalink(dv, engine.MODEL_VERSION, body),
            **result}
