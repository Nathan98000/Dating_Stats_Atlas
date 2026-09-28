"""Emit the shared variant-selection cases (m4.0.0, ADR 0018): /v1/rank
responses from the API's own path over the pinned fixture build, and for
each a set of "about you" details with the rows atlas.model.variants
.select_variant selects for them. The vitest suite (tests/variants.test.ts)
asserts the browser's lib/variants selects exactly these — the browser
copies the API's numbers and never computes one.

    python scripts/gen_variant_cases.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB.parents[1]))
os.environ["BUILD_DIR"] = str(WEB.parents[0] / "model" / "tests" / "golden" / "fixture_build")

from fastapi.testclient import TestClient  # noqa: E402

from atlas.api import app as api  # noqa: E402

SEARCHES = {
    "default": {"self": {"age": 30},
                "seeking": {"sex": "male", "age": [28, 40],
                            "marital": ["never_married", "previously_married"]}},
    "same_sex": {"self": {"age": 31},
                 "seeking": {"sex": "male", "age": [27, 38], "marital": ["never_married"],
                             "education_min": "bachelors"}},
    # a narrow search: cities left out, with the balance that survives
    "narrow_worst_first": {"self": {"age": 30},
                           "seeking": {"sex": "female", "age": [25, 35],
                                       "marital": ["never_married"],
                                       "education_min": "graduate", "income_min": 150000},
                           "pool_vs_match": 0.9, "sort": "worst_first"},
}
# the browser's details (lib/about-you AboutYou): sex absent = the
# opposite of the sought sex; race counts only with the switch on
ABOUT = [
    {},
    {"sex": "male"},
    {"sex": "female"},
    {"edu": "graduate"},
    {"sex": "male", "edu": "hs_or_less"},
    {"raceOn": True},
    {"raceOn": True, "race": "asian_nh"},
    {"sex": "male", "edu": "bachelors", "raceOn": True, "race": "hispanic"},
    {"sex": "female", "edu": "some_college", "raceOn": True, "race": "black_nh"},
    {"race": "white_nh"},
]


def main() -> None:
    c = TestClient(api.app)
    cases = []
    for name, body in SEARCHES.items():
        r = c.post("/v1/rank", json=body)
        assert r.status_code == 200, r.text
        resp = r.json()
        sels = []
        for a in ABOUT:
            race = a.get("race") if a.get("raceOn") and a.get("race") else None
            got = api.engine.select_variant(resp, a.get("sex"), a.get("edu"), race)
            sels.append({"about": a, "expected": json.loads(json.dumps(got))})
        cases.append({"name": name, "response": resp, "selections": sels})
    out = WEB / "tests" / "variant_cases.json"
    out.write_text(json.dumps({"model_version": api.engine.MODEL_VERSION, "cases": cases},
                              separators=(",", ":")) + "\n")
    print(f"{out}: {len(cases)} searches x {len(ABOUT)} selections")


if __name__ == "__main__":
    main()
