"""Ranking endpoint — thin transport over atlas.model, speaking the §8.2
contract. Single process, one build loaded at boot, cubes in memory, never
writes. Same-origin posture: no CORS middleware, loopback bind, no public
API (D04).

    BUILD_DIR=/path/to/builds/<data_version> uvicorn atlas.api.app:app \
        --host 127.0.0.1

Documented deviations from the §8.2 sketch (additive only):
  - each ranked row also carries rivals, ratio_moe, n_alloc-adjacent detail
    via n_unweighted (defined as min(allocated, Kish) per Phase 1
    correction 2), flags (incl. low_allocation_purity), and the rendered
    `explanation` string (§9's per-request template output).
  - cross_group_pairing_rate is null until the Phase 3 pairing kernel.
  - `size_vs_odds` is accepted as the D05 slider alternative to weights.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from atlas import model as engine
from atlas.model.preferences import SPEC_MARITAL, SPEC_RACE

BUILDS_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "builds"


def _resolve_build_dir() -> Path:
    env = os.environ.get("BUILD_DIR")
    if env:
        return Path(env)
    candidates = sorted((p for p in BUILDS_DEFAULT.iterdir() if p.is_dir()
                         and (p / "manifest.json").exists()),
                        key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise RuntimeError(f"no builds under {BUILDS_DEFAULT}; set BUILD_DIR")
    return candidates[-1]


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
