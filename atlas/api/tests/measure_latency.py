"""Measure /v1/rank latency against a real build (not the fixture).

    python atlas/tests/measure_latency.py <build_dir> [n_requests]

Reports p50/p95/p99 over a mix of golden vectors and randomized queries,
single process, through the ASGI stack (TestClient), after a warmup.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ["BUILD_DIR"] = sys.argv[1]

from fastapi.testclient import TestClient  # noqa: E402

from atlas.api import app as api  # noqa: E402

N = int(sys.argv[2]) if len(sys.argv) > 2 else 400
rng = random.Random(7)
EDU = [None, "some_college", "bachelors", "graduate"]
INC = [None, 25000, 50000, 75000, 100000, 150000, 250000]
MAR = ["never", "not_married", "any"]


MARITAL_LISTS = [["never_married"], ["previously_married"],
                 ["never_married", "previously_married"]]
SPEC_RACES = [None, None, None, "hispanic", "white_nh", "black_nh", "asian_nh"]


def random_request() -> dict:
    sex = rng.choice(["male", "female"])
    age = rng.randint(22, 60)
    lo = rng.randint(18, 55)
    seeking = {"age": [lo, min(70, lo + rng.randint(4, 20))],
               "marital": rng.choice(MARITAL_LISTS)}
    if (e := rng.choice(EDU)):
        seeking["education_min"] = e
    if (i := rng.choice(INC)):
        seeking["income_min"] = i
    if (r := rng.choice(SPEC_RACES)):
        seeking["race_ethnicity"] = [r]
    return {"self": {"sex": sex, "age": age}, "seeking": seeking}


def main() -> None:
    client = TestClient(api.app)
    reqs = [random_request() for _ in range(N)]
    for r in reqs[:20]:  # warmup
        client.post("/v1/rank", json=r)
    times = []
    for r in reqs:
        t0 = time.perf_counter()
        resp = client.post("/v1/rank", json=r)
        times.append((time.perf_counter() - t0) * 1000)
        assert resp.status_code == 200, resp.text
    times.sort()
    out = {"n": N,
           "p50_ms": round(times[int(0.50 * N)], 2),
           "p95_ms": round(times[int(0.95 * N)], 2),
           "p99_ms": round(times[int(0.99 * N)], 2),
           "max_ms": round(times[-1], 2),
           "target_p95_ms": 60}
    print(json.dumps(out, indent=2))
    (Path(__file__).resolve().parents[2] / "results" / "phase2" /
     "latency.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
