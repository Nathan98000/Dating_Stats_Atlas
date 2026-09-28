"""Phase 4 Stage 5b: the size of the rank response, measured before and
after the "about you" variants (the brief's budget: the default search's
gzipped rank response may grow to at most 3x its size before the change).

The response is the API's own JSON for each search, through the app in
process (FastAPI's TestClient), serialised exactly as the API sends it;
its gzip is measured at level 6 (the zlib default most servers use) and
at level 9 beside it.

    BUILD_DIR=<build> python -m atlas.pipeline.build.payload_size <out.json> [--searches before|after]
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
from pathlib import Path

# the site's default search as the web sends it (web/src/lib/prefs.ts
# DEFAULT_PREFS -> toRankBody), and the reference searches beside it
BEFORE = {
    "default": {"self": {"sex": "female", "age": 30},
                "seeking": {"age": [28, 40], "marital": ["never_married", "previously_married"]},
                "sort": "best_first"},
    "same_sex_reference": {"self": {"sex": "male", "age": 31},
                           "seeking": {"sex": "male", "age": [27, 38], "marital": ["never_married"],
                                       "education_min": "bachelors"},
                           "sort": "best_first"},
    "disclosed_grad_asian_woman_30": {"self": {"sex": "female", "age": 30, "education": "graduate",
                                               "race_ethnicity": "asian_nh"},
                                      "seeking": {"age": [28, 40],
                                                  "marital": ["never_married", "previously_married"]},
                                      "sort": "best_first"},
}
# after Phase 4 the request carries own age only; the sought sex is explicit
AFTER = {
    "default": {"self": {"age": 30},
                "seeking": {"sex": "male", "age": [28, 40],
                            "marital": ["never_married", "previously_married"]},
                "sort": "best_first"},
    "same_sex_reference": {"self": {"age": 31},
                           "seeking": {"sex": "male", "age": [27, 38], "marital": ["never_married"],
                                       "education_min": "bachelors"},
                           "sort": "best_first"},
}


def measure(searches: dict) -> dict:
    from fastapi.testclient import TestClient
    from atlas.api.app import app
    c = TestClient(app)
    out = {}
    for name, body in searches.items():
        r = c.post("/v1/rank", json=body)
        assert r.status_code == 200, (name, r.status_code, r.text[:300])
        raw = r.content
        t = time.perf_counter()
        for _ in range(5):
            c.post("/v1/rank", json=body)
        out[name] = {"bytes": len(raw),
                     "gzip6_bytes": len(gzip.compress(raw, compresslevel=6)),
                     "gzip9_bytes": len(gzip.compress(raw, compresslevel=9)),
                     "ranked_rows": len(r.json().get("ranked", [])),
                     "in_process_ms_mean_of_5": round((time.perf_counter() - t) / 5 * 1000, 1)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--searches", choices=["before", "after"], default="before")
    a = ap.parse_args()
    from atlas.api.app import BUILD
    from atlas import model as engine
    rec = {"build": BUILD.manifest["data_version"], "model_version": engine.MODEL_VERSION,
           "searches": measure(BEFORE if a.searches == "before" else AFTER),
           "generated": time.strftime("%Y-%m-%dT%H:%M:%S")}
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
