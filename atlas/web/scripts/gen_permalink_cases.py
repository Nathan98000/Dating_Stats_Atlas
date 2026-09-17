"""Emit the shared permalink test cases (acceptance gate 5): request bodies
run through the API's OWN pydantic path (RankRequest.model_dump, exactly as
app.py does) and encoded by atlas.model.preferences.permalink. The vitest
suite asserts the frontend's decode inverts these and its encode reproduces
them byte for byte — a drift between the two dialects fails CI instead of
shipping.

    python scripts/gen_permalink_cases.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB.parents[1]))

from atlas import model as engine  # noqa: E402
from atlas.api.app import RankRequest  # noqa: E402

BODIES = [
    {"self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40],
                 "marital": ["never_married", "previously_married"]}},
    {"self": {"sex": "female", "age": 32},
     "seeking": {"age": [30, 40], "marital": ["never_married"],
                 "education_min": "bachelors", "income_min": 75000}},
    {"self": {"sex": "male", "age": 29},
     "seeking": {"sex": "male", "age": [27, 38], "marital": ["never_married"],
                 "education_min": "graduate"}},
    # m2.1.0 named controls (ADR 0005): four of them, plus the one-version
    # lifestyle alias still accepted at the transport
    {"self": {"sex": "female", "age": 34},
     "seeking": {"age": [30, 44],
                 "marital": ["never_married", "previously_married"]},
     "pool_vs_balance": 0.7,
     "importance": {"cost": "a_lot", "reach": "not_much",
                    "students": "a_lot", "weather": "not_much"}},
    {"self": {"sex": "female", "age": 34},
     "seeking": {"age": [30, 44], "marital": ["never_married"]},
     "pool_vs_balance": 1.0,
     "importance": {"weather": "some"}},
    {"self": {"sex": "male", "age": 36},
     "seeking": {"age": [30, 42], "marital": ["never_married"]},
     "importance": {"lifestyle": "a_lot"}},
    {"self": {"sex": "female", "age": 29},
     "seeking": {"age": [28, 38],
                 "marital": ["never_married", "previously_married"],
                 "race_ethnicity": ["black_nh"]}},
    {"self": {"sex": "male", "age": 45},
     "seeking": {"age": [40, 55],
                 "marital": ["never_married", "previously_married"],
                 "race_ethnicity": ["white_nh", "asian_nh"],
                 "income_min": 250000}},
    # float-typed fields: integral floats are the dialect trap (Python
    # renders 1.0, JSON.stringify renders 1)
    {"self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]},
     "pool_vs_balance": 0.0},
    {"self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]},
     "pool_vs_balance": 1.0},
    {"self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]},
     "pool_vs_balance": 0.35},
    {"self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]},
     "pool_vs_balance": 0.4545},
    {"self": {"sex": "male", "age": 33},
     "seeking": {"age": [26, 38], "marital": ["never_married"]},
     "weights": {"pool": 0.5, "balance": 0.5}},
    {"self": {"sex": "male", "age": 33},
     "seeking": {"age": [26, 38], "marital": ["never_married"]},
     "weights": {"pool": 0.3, "balance": 0.25, "reach": 0.2, "cost": 0.15,
                 "weather": 0.06, "students": 0.04}},
]

DV, MV = "2c8d7285c720", engine.MODEL_VERSION


def main() -> None:
    cases = []
    for raw in BODIES:
        body = RankRequest.model_validate(raw).model_dump(exclude_none=True)
        body.pop("sort", None)  # exactly as app.py does before encoding
        cases.append({"body": body,
                      "permalink": engine.permalink(DV, MV, body)})
    out = WEB / "tests" / "permalink_cases.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(
        {"data_version": DV, "model_version": MV, "cases": cases},
        indent=1) + "\n")
    print(f"{out}: {len(cases)} cases")


if __name__ == "__main__":
    main()
