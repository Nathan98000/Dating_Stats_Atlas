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
    # lifestyle alias still accepted at the transport; the slider is
    # pool_vs_match since m3.0.0 (ADR 0009)
    {"self": {"sex": "female", "age": 34},
     "seeking": {"age": [30, 44],
                 "marital": ["never_married", "previously_married"]},
     "pool_vs_match": 0.7,
     "importance": {"cost": "a_lot", "reach": "not_much",
                    "students": "a_lot", "weather": "not_much"}},
    {"self": {"sex": "female", "age": 34},
     "seeking": {"age": [30, 44], "marital": ["never_married"]},
     "pool_vs_match": 1.0,
     "importance": {"weather": "some"}},
    # m3.0.0: the optional seeker attributes ride in self, and the
    # deprecated pool_vs_balance name encodes as the canonical control
    {"self": {"sex": "female", "age": 31, "education": "bachelors",
              "race_ethnicity": "black_nh"},
     "seeking": {"age": [28, 40],
                 "marital": ["never_married", "previously_married"]}},
    {"self": {"sex": "male", "age": 44, "education": "hs_or_less"},
     "seeking": {"age": [35, 50], "marital": ["previously_married"]},
     "pool_vs_match": 0.25},
    {"self": {"sex": "female", "age": 27, "race_ethnicity": "hispanic"},
     "seeking": {"age": [25, 35], "marital": ["never_married"]},
     "pool_vs_balance": 0.6},
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
    # m2.2.0 (ADR 0006): the formerly always-counted pair as an ordinary
    # selection, and an explicit all-eight list (the API accepts it as
    # no-filter; the frontend round-trips it to no filter)
    {"self": {"sex": "female", "age": 31},
     "seeking": {"age": [26, 40], "marital": ["never_married"],
                 "race_ethnicity": ["two_or_more_nh", "other_nh"]}},
    {"self": {"sex": "female", "age": 31},
     "seeking": {"age": [26, 40], "marital": ["never_married"],
                 "race_ethnicity": ["hispanic", "white_nh", "black_nh",
                                    "asian_nh", "aian_nh", "nhpi_nh",
                                    "two_or_more_nh", "other_nh"]}},
    # float-typed fields: integral floats are the dialect trap (Python
    # renders 1.0, JSON.stringify renders 1)
    {"self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]},
     "pool_vs_match": 0.0},
    {"self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]},
     "pool_vs_match": 1.0},
    {"self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]},
     "pool_vs_match": 0.35},
    {"self": {"sex": "female", "age": 30},
     "seeking": {"age": [28, 40], "marital": ["never_married"]},
     "pool_vs_match": 0.4545},
    {"self": {"sex": "male", "age": 33},
     "seeking": {"age": [26, 38], "marital": ["never_married"]},
     "weights": {"pool": 0.5, "match": 0.5}},
    {"self": {"sex": "male", "age": 33},
     "seeking": {"age": [26, 38], "marital": ["never_married"]},
     "weights": {"pool": 0.3, "match": 0.25, "reach": 0.2, "cost": 0.15,
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
