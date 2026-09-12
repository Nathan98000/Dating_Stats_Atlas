"""atlas.model — the single source of truth for the math.

Standalone importable package: preferences -> masks, scoring, suppression,
intervals, explanation. No I/O except loader.py (documented there). The API
is thin transport over this package; the golden tests exercise it directly.
"""
from atlas.model.loader import Build, load_build
from atlas.model.preferences import (EDU_LEVELS, INC_LEVELS, INCOME_FLOORS,
                                     MARITAL_LEVELS, N_FLAT, PILLARS,
                                     RACE_LEVELS, SEX_LEVELS, SPEC_MARITAL,
                                     SPEC_RACE, Request, mask_vector,
                                     parse_request, permalink, slider_weights)
from atlas.model.scoring import rank
from atlas.model.versions import MODEL_VERSION, SCHEMA_VERSION

__all__ = [
    "Build", "load_build", "mask_vector", "rank", "parse_request",
    "permalink", "slider_weights", "Request",
    "MODEL_VERSION", "SCHEMA_VERSION", "N_FLAT", "PILLARS",
    "SEX_LEVELS", "MARITAL_LEVELS", "EDU_LEVELS", "INC_LEVELS", "RACE_LEVELS",
    "INCOME_FLOORS", "SPEC_RACE", "SPEC_MARITAL",
]
