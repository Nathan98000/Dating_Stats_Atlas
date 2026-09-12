"""atlas.model — the single source of truth for the math.

Standalone importable package: preferences -> masks, scoring, suppression,
explanation. No I/O except loader.py (documented there). The API is thin
transport over this package; the golden tests exercise it directly.
"""
from atlas.model.loader import Build, load_build
from atlas.model.preferences import (EDU_LEVELS, INC_LEVELS, INCOME_FLOORS,
                                     MARITAL_LEVELS, MARITAL_SETS, N_FLAT,
                                     RACE_LEVELS, SEX_LEVELS, mask_vector)
from atlas.model.scoring import rank
from atlas.model.versions import MODEL_VERSION, SCHEMA_VERSION

__all__ = [
    "Build", "load_build", "mask_vector", "rank",
    "MODEL_VERSION", "SCHEMA_VERSION", "N_FLAT",
    "SEX_LEVELS", "MARITAL_LEVELS", "EDU_LEVELS", "INC_LEVELS", "RACE_LEVELS",
    "INCOME_FLOORS", "MARITAL_SETS",
]
