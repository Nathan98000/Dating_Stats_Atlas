"""City profiles: POST /v1/profile ({"cbsa": ...}) serves every metro's stat
cards and crime block, so the 194 metros below the ranked set's population
floor — which no search returns — get the profile their city page promises.
The endpoint only reads, and the build does not change, so nothing the site
ranks or scores may move, and every /v1/rank response must be the same
bytes as before, the build id included.

The two records are Phase 4d's `record`, unchanged (results/phase4d/
served_numbers_check.py: every ADR 0011 test search's /v1/rank response
through the API's own path, and rank() for its seeker as either sex), run
on the same build through the code before the change and through the code
with it:

    PYTHONPATH=. .venv/bin/python atlas/results/phase4d/served_numbers_check.py record <build_dir> atlas/results/city_profile/_record_before.json
    PYTHONPATH=. .venv/bin/python atlas/results/phase4d/served_numbers_check.py record <build_dir> atlas/results/city_profile/_record_after.json

Phase 4d's own `compare` reads a build change (features.parquet) into its
pass rule and writes Phase 4d's result file, so this script compares the
two records itself, more strictly — the same build, so the same bytes —
and reads the new endpoint for every metro of the build:

    PYTHONPATH=. .venv/bin/python atlas/results/city_profile/served_numbers_check.py <before.json> <after.json> <build_dir>
        -> results/city_profile/served_numbers_check.json
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "atlas" / "results" / "city_profile" / "served_numbers_check.json"
SEXES = ("male", "female")
# the site's stated default search (web lib/prefs DEFAULT_PREFS: someone of
# 30 seeking men 28-40, never or previously married): every search returns
# each ranked-set metro as a ranked or a suppressed row, whose blocks the
# profiles are held to
BODY = {"self": {"age": 30},
        "seeking": {"sex": "male", "age": [28, 40],
                    "marital": ["never_married", "previously_married"]}}


def compare_records(a: dict, b: dict) -> tuple[dict, list[str]]:
    assert list(a["searches"]) == list(b["searches"]), "different test searches"
    names = list(a["searches"])
    fails: list[str] = []
    same = {"digest": 0, "bytes": 0, "gzip6": 0, "rank": 0}
    for k in names:
        x, y = a["searches"][k]["api"], b["searches"][k]["api"]
        for f in ("digest", "bytes", "gzip6"):
            if x[f] == y[f]:
                same[f] += 1
            else:
                fails.append(f"{k}: the rank response's {f} moved")
        for s in SEXES:
            if a["searches"][k]["rank"][s] == b["searches"][k]["rank"][s]:
                same["rank"] += 1
            else:
                fails.append(f"{k}: rank() {s} moved")
    if a["build"] != b["build"]:
        fails.append(f"the build changed: {a['build']} -> {b['build']}")
    meta_moved = sorted(k for k in set(a["meta_keys"]) | set(b["meta_keys"])
                        if a["meta_keys"].get(k) != b["meta_keys"].get(k))
    fails += [f"/v1/meta {k} moved" for k in meta_moved]
    if a["political_lean_endpoint"] != b["political_lean_endpoint"]:
        fails.append("/v1/political_lean moved")
    out = {
        "build": [a["build"], b["build"]],
        "model_version": [a["model_version"], b["model_version"]],
        "code": [a["code"], b["code"]],
        "test_searches": {"total": len(names),
                          "source": "stability_gate.test_searches (ADR 0011: personas, effects grid, same-sex grid)"},
        "api_rank_response": {
            "same_digest_build_id_masked": same["digest"],
            "same_bytes": same["bytes"],
            "same_gzip6_bytes": same["gzip6"],
            "total_bytes": [sum(a["searches"][k]["api"]["bytes"] for k in names),
                            sum(b["searches"][k]["api"]["bytes"] for k in names)]},
        "single_seeker_rank": {"rankings_checked": 2 * len(names), "identical": same["rank"]},
        "meta_keys_changed": meta_moved,
        "political_lean_endpoint": [a["political_lean_endpoint"], b["political_lean_endpoint"]],
    }
    return out, fails


def read_profiles(build_dir: str) -> tuple[dict, list[str]]:
    os.environ["BUILD_DIR"] = str(Path(build_dir).resolve())
    from fastapi.testclient import TestClient

    from atlas.api import app as api
    client = TestClient(api.app)
    meta = client.get("/v1/meta").json()
    rank = client.post("/v1/rank", json=BODY)
    assert rank.status_code == 200, rank.text
    rows = {r["cbsa"]: r for r in rank.json()["ranked"] + rank.json()["suppressed"]}
    lean = client.get("/v1/political_lean").json()["metros"]
    fails: list[str] = []
    sizes: list[int] = []
    count = {"metros": 0, "ranked_set": 0, "below_floor": 0,
             "below_floor_crime_figure": 0, "below_floor_political_lean": 0,
             "rows_agreeing": 0}
    for m in meta["metros"]:
        c = m["cbsa"]
        r = client.post("/v1/profile", json={"cbsa": c})
        if r.status_code != 200:
            fails.append(f"{c}: /v1/profile answered {r.status_code}")
            continue
        p = r.json()
        sizes.append(len(r.content))
        count["metros"] += 1
        if [x["id"] for x in p["cards"]] != meta["city_cards"]:
            fails.append(f"{c}: the cards are not the registry's city_cards")
        if not all(x.get("missing") or (x.get("display") and x.get("band")) for x in p["cards"]):
            fails.append(f"{c}: a card without its figure or band")
        if not p["crime"].get("caution"):
            fails.append(f"{c}: the crime block has no caution")
        if m["ranked_set"]:
            count["ranked_set"] += 1
            row = rows.get(c)
            if row is None:
                fails.append(f"{c}: a ranked-set metro the search did not return")
            elif row["cards"] == p["cards"] and row["crime"] == p["crime"]:
                count["rows_agreeing"] += 1
            else:
                fails.append(f"{c}: the profile differs from the search row's blocks")
        else:
            count["below_floor"] += 1
            if c in rows:
                fails.append(f"{c}: a search returned a metro below the floor")
            count["below_floor_crime_figure"] += bool(p["crime"]["available"])
            count["below_floor_political_lean"] += bool(lean[c]["available"])
    for bad in ("99999", "abc"):
        if client.post("/v1/profile", json={"cbsa": bad}).status_code != 404:
            fails.append(f"/v1/profile {bad!r} did not answer 404")
    # the body names the metro and nothing else: a search detail is refused
    stray = client.post("/v1/profile", json={"cbsa": meta["metros"][0]["cbsa"], "seeking": BODY["seeking"]})
    if stray.status_code != 422:
        fails.append(f"/v1/profile with a search detail answered {stray.status_code}")
    out = {"build": meta["data_version"], "search_held_to": BODY, "counts": count,
           "response_bytes": {"min": min(sizes), "median": statistics.median(sizes),
                              "max": max(sizes)},
           "unknown_metro": "404", "body_beyond_the_metro": "422"}
    return out, fails


def main(before: str, after: str, build_dir: str) -> None:
    a = json.loads(Path(before).read_text())
    b = json.loads(Path(after).read_text())
    rec, fails = compare_records(a, b)
    prof, pfails = read_profiles(build_dir)
    fails += pfails
    out = {**rec, "profile_endpoint": prof, "failures": fails[:40], "pass": not fails,
           "generated": time.strftime("%Y-%m-%dT%H:%M:%S")}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("build", "code", "api_rank_response", "single_seeker_rank",
                                          "meta_keys_changed", "profile_endpoint", "failures", "pass")},
                     indent=1, ensure_ascii=False))
    print(f"-> {OUT}")
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
