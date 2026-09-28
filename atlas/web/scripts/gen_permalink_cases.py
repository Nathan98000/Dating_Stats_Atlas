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

# m4.0.0 (ADR 0018): a request carries the own age and an explicit sought
# sex; the visitor's own sex, education and race never travel, so no
# token encodes them (the cases before m4.0.0 differed by them only where
# they are now the same request, and are listed once)
BODIES = [
    {"self": {"age": 30}, "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married", "previously_married"]}},
    {"self": {"age": 32}, "seeking": {"sex": "male", "age": [30, 40], "marital": ["never_married"], "education_min": "bachelors", "income_min": 75000}},
    {"self": {"age": 29}, "seeking": {"sex": "male", "age": [27, 38], "marital": ["never_married"], "education_min": "graduate"}},
    {"self": {"age": 34}, "seeking": {"sex": "male", "age": [30, 44], "marital": ["never_married", "previously_married"]}, "pool_vs_match": 0.7, "importance": {"cost": "a_lot", "reach": "not_much", "students": "a_lot", "weather": "not_much"}},
    {"self": {"age": 34}, "seeking": {"sex": "male", "age": [30, 44], "marital": ["never_married"]}, "pool_vs_match": 1.0, "importance": {"weather": "some"}},
    {"self": {"age": 31}, "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married", "previously_married"]}},
    {"self": {"age": 44}, "seeking": {"sex": "female", "age": [35, 50], "marital": ["previously_married"]}, "pool_vs_match": 0.25},
    {"self": {"age": 27}, "seeking": {"sex": "male", "age": [25, 35], "marital": ["never_married"]}, "pool_vs_balance": 0.6},
    {"self": {"age": 36}, "seeking": {"sex": "female", "age": [30, 42], "marital": ["never_married"]}, "importance": {"lifestyle": "a_lot"}},
    {"self": {"age": 29}, "seeking": {"sex": "male", "age": [28, 38], "marital": ["never_married", "previously_married"], "race_ethnicity": ["black_nh"]}},
    {"self": {"age": 45}, "seeking": {"sex": "female", "age": [40, 55], "marital": ["never_married", "previously_married"], "race_ethnicity": ["white_nh", "asian_nh"], "income_min": 250000}},
    {"self": {"age": 31}, "seeking": {"sex": "male", "age": [26, 40], "marital": ["never_married"], "race_ethnicity": ["two_or_more_nh", "other_nh"]}},
    {"self": {"age": 31}, "seeking": {"sex": "male", "age": [26, 40], "marital": ["never_married"], "race_ethnicity": ["hispanic", "white_nh", "black_nh", "asian_nh", "aian_nh", "nhpi_nh", "two_or_more_nh", "other_nh"]}},
    {"self": {"age": 30}, "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married"]}, "pool_vs_match": 0.0},
    {"self": {"age": 30}, "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married"]}, "pool_vs_match": 1.0},
    {"self": {"age": 30}, "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married"]}, "pool_vs_match": 0.35},
    {"self": {"age": 30}, "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married"]}, "pool_vs_match": 0.4545},
    {"self": {"age": 33}, "seeking": {"sex": "female", "age": [26, 38], "marital": ["never_married"]}, "weights": {"pool": 0.5, "match": 0.5}},
    {"self": {"age": 33}, "seeking": {"sex": "female", "age": [26, 38], "marital": ["never_married"]}, "weights": {"pool": 0.3, "match": 0.25, "reach": 0.2, "cost": 0.15, "weather": 0.06, "students": 0.04}},
]

DV, MV = "2c8d7285c720", engine.MODEL_VERSION


def main() -> None:
    cases = []
    for raw in BODIES:
        body = RankRequest.model_validate(raw).model_dump(exclude_none=True)
        body.pop("sort", None)  # exactly as app.py does before encoding
        cases.append({"body": body,
                      "permalink": engine.permalink(DV, MV, body)})
    # the alias case must encode to the canonical control's token
    alias = [c for c in cases if "pool_vs_balance" in c["body"]]
    assert alias, "an alias case is part of the gate"
    for c in alias:
        canon = {k: v for k, v in c["body"].items() if k != "pool_vs_balance"}
        canon["pool_vs_match"] = c["body"]["pool_vs_balance"]
        assert engine.permalink(DV, MV, canon) == c["permalink"]
    out = WEB / "tests" / "permalink_cases.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(
        {"data_version": DV, "model_version": MV, "cases": cases},
        indent=1) + "\n")
    print(f"{out}: {len(cases)} cases")


if __name__ == "__main__":
    main()
