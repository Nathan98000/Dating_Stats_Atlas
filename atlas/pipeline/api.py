"""Ranking endpoint: FastAPI, single process, one build loaded at boot,
cubes held in memory, never writes.

    BUILD_DIR=/path/to/builds/<data_version> uvicorn api:app --host 127.0.0.1

Same-origin only: no CORS middleware is installed, and the recommended bind
is loopback behind the site's own reverse proxy. There is no public API.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

import score as engine

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


class Seeker(BaseModel):
    sex: Literal["male", "female"]
    age: int = Field(ge=18, le=70)


class PoolFilter(BaseModel):
    sex: Optional[Literal["male", "female"]] = None
    age_min: int = Field(ge=18, le=70)
    age_max: int = Field(ge=18, le=70)
    marital: Literal["never", "not_married", "any"]
    education_min: Optional[Literal["some_college", "bachelors", "graduate"]] = None
    income_min: Optional[int] = None
    race: Optional[Literal[tuple(engine.RACE_LEVELS)]] = None  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _check(self):
        if self.age_min > self.age_max:
            raise ValueError("age_min > age_max")
        if self.income_min is not None and self.income_min not in engine.INCOME_FLOORS:
            raise ValueError(
                f"income_min must be a cube band edge: {sorted(engine.INCOME_FLOORS)}")
        return self


class Weights(BaseModel):
    pool: float = Field(default=0.5, ge=0)
    balance: float = Field(default=0.5, ge=0)

    @model_validator(mode="after")
    def _check(self):
        if self.pool + self.balance <= 0:
            raise ValueError("weights must not both be zero")
        return self


class RankRequest(BaseModel):
    seeker: Seeker
    pool: PoolFilter
    weights: Weights = Weights()


@app.get("/v1/health")
def health() -> dict:
    return {"status": "ok",
            "data_version": BUILD.manifest["data_version"],
            "model_version": engine.MODEL_VERSION,
            "schema_version": BUILD.manifest["schema_version"],
            "metros": len(BUILD.metro_levels),
            "ranked_set": int(BUILD.ranked_set.sum())}


@app.post("/v1/rank")
def rank(req: RankRequest) -> dict:
    try:
        result = engine.rank(BUILD, req.seeker.sex, req.seeker.age,
                             req.pool.model_dump(), req.weights.model_dump())
    except AssertionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"data_version": BUILD.manifest["data_version"],
            "model_version": engine.MODEL_VERSION, **result}
