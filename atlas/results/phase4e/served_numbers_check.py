"""Phase 4e: what the API serves, before and after each commit.

Commits A (copy) and B (photos) may move no number; commit C (the new
nice-day rule) moves scores and ranks, and its rank shift is measured here.

`record` reads a build through the code on PYTHONPATH and writes, for every
ADR 0011 test search (stability_gate.test_searches):

  rest     the digest of the /v1/rank response, the whole of it (the
           explanations included), with the model version masked where it
           appears (C bumps it)
  rank     the digests of rank() for the search's seeker as either sex
  order    the default variant's (cbsa, rank, score) in its order

and, beside them, the digest of POST /v1/profile for every metro of the
build, of GET /v1/political_lean, and the two reference searches' default
variants in full (the site's default search and the same-sex reference
search, as pipeline/build/payload_size.AFTER sends them).

`compare <before> <after> same` passes only if every digest is identical
(A and B). `compare <before> <after> scored <tag>` reports how much moved
and writes the rank shift on the two reference searches (C):
rank_shift_<tag>.json and .csv beside this file.

    PYTHONPATH=. .venv/bin/python atlas/results/phase4e/served_numbers_check.py record <build_dir> <out.json>
    PYTHONPATH=. .venv/bin/python atlas/results/phase4e/served_numbers_check.py compare <before.json> <after.json> same
    PYTHONPATH=. .venv/bin/python atlas/results/phase4e/served_numbers_check.py compare <before.json> <after.json> scored m4_1_1_to_m4_2_0
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEXES = ("male", "female")


def sha(x) -> str:
    return hashlib.sha256(json.dumps(x, separators=(",", ":"), ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()


def opposite(sex: str) -> str:
    return "female" if sex == "male" else "male"


def api_body(body: dict, sought: str) -> dict:
    out = {k: copy.deepcopy(body[k]) for k in ("weights", "pool_vs_match", "pool_vs_balance",
                                               "importance") if k in body}
    out["self"] = {"age": body["self"]["age"]}
    out["seeking"] = {**copy.deepcopy(body["seeking"]), "sex": sought}
    return out


def masked(resp: dict, mv: str) -> dict:
    out = copy.deepcopy(resp)
    out.pop("model_version", None)
    out["permalink"] = out.get("permalink", "").replace(f"/{mv}/", "/<model_version>/")
    return out


def record(build_dir: str, out_path: str) -> None:
    os.environ["BUILD_DIR"] = str(Path(build_dir).resolve())
    from fastapi.testclient import TestClient

    from atlas.api import app as api
    from atlas.model.variants import select_variant
    from atlas.pipeline.build import payload_size as PS
    from atlas.pipeline.build import stability_gate as SG
    engine, build = api.engine, api.BUILD
    mv = engine.MODEL_VERSION
    client = TestClient(api.app)
    t0 = time.time()
    searches = {}
    for name, body in SG.test_searches():
        sought = body["seeking"].get("sex") or opposite(body["self"]["sex"])
        r = client.post("/v1/rank", json=api_body(body, sought))
        assert r.status_code == 200, (name, r.text)
        resp = r.json()
        sel = select_variant(resp)
        ranks = {}
        for s in SEXES:
            b = copy.deepcopy(body)
            b["self"]["sex"], b["seeking"]["sex"] = s, sought
            ranks[s] = sha(engine.rank(build, engine.parse_request(b)))
        searches[name] = {"rest": sha(masked(resp, mv)), "rank": ranks,
                          "order": [[row["cbsa"], row["rank"], row["score"]] for row in sel["ranked"]]}
    profiles = {}
    for cbsa in build.metro_levels:
        r = client.post("/v1/profile", json={"cbsa": str(cbsa)})
        assert r.status_code == 200, (cbsa, r.text)
        profiles[str(cbsa)] = sha(r.json())
    lean = client.get("/v1/political_lean")
    reference = {}
    for name in ("default", "same_sex_reference"):
        r = client.post("/v1/rank", json=PS.AFTER[name])
        assert r.status_code == 200, (name, r.text)
        sel = select_variant(r.json())
        reference[name] = {"body": PS.AFTER[name],
                           "rows": [{"cbsa": row["cbsa"], "metro": row["display_name"],
                                     "rank": row["rank"], "score": row["score"]}
                                    for row in sel["ranked"]]}
    Path(out_path).write_text(json.dumps({
        "build": build.manifest["data_version"], "model_version": mv,
        "seconds": round(time.time() - t0, 1), "searches": searches,
        "profiles": profiles, "political_lean": [lean.status_code, sha(lean.json())],
        "reference": reference}) + "\n")
    print(f"{len(searches)} searches, {len(profiles)} profiles -> {out_path} ({time.time() - t0:.0f} s)")


def kendall_tau(a: list[int], b: list[int]) -> float:
    n, s = len(a), 0
    for i in range(n):
        for j in range(i + 1, n):
            x, y = a[i] - a[j], b[i] - b[j]
            s += (x > 0) - (x < 0) if y > 0 else ((x < 0) - (x > 0) if y < 0 else 0)
    return s / (n * (n - 1) / 2)


def shift(before: dict, after: dict) -> dict:
    a = {r["cbsa"]: r for r in before["rows"]}
    b = {r["cbsa"]: r for r in after["rows"]}
    common = [c for c in a if c in b]
    moves = sorted(({"metro": b[c]["metro"], "cbsa": c, "rank_before": a[c]["rank"],
                     "rank_after": b[c]["rank"], "move": a[c]["rank"] - b[c]["rank"],
                     "score_before": a[c]["score"], "score_after": b[c]["score"]}
                    for c in common), key=lambda m: (-abs(m["move"]), m["rank_after"]))
    absm = sorted(abs(m["move"]) for m in moves)
    dscore = [abs(m["score_after"] - m["score_before"]) for m in moves]
    p90 = absm[min(len(absm) - 1, int(round(0.9 * (len(absm) - 1))))]
    return {
        "metros_compared": len(common),
        "only_before": sorted(set(a) - set(b)), "only_after": sorted(set(b) - set(a)),
        "ranks_changed": sum(m["move"] != 0 for m in moves),
        "kendall_tau": round(kendall_tau([a[c]["rank"] for c in common],
                                         [b[c]["rank"] for c in common]), 3),
        "median_abs_move": statistics.median(absm), "p90_abs_move": p90, "max_abs_move": absm[-1],
        "score_change": {"median_abs": round(statistics.median(dscore), 2),
                         "max_abs": round(max(dscore), 2)},
        "top10_before": [r["metro"] for r in before["rows"][:10]],
        "top10_after": [r["metro"] for r in after["rows"][:10]],
        "biggest_moves": moves[:12],
    }, moves


def compare(before: str, after: str, mode: str, tag: str | None) -> None:
    a, b = json.loads(Path(before).read_text()), json.loads(Path(after).read_text())
    assert list(a["searches"]) == list(b["searches"]), "different test searches"
    names = list(a["searches"])
    same_rest = sum(a["searches"][k]["rest"] == b["searches"][k]["rest"] for k in names)
    same_rank = sum(a["searches"][k]["rank"][s] == b["searches"][k]["rank"][s]
                    for k in names for s in SEXES)
    same_order = sum([x[0] for x in a["searches"][k]["order"]] == [x[0] for x in b["searches"][k]["order"]]
                     for k in names)
    same_prof = sum(a["profiles"].get(c) == h for c, h in b["profiles"].items())
    out = {"build": [a["build"], b["build"]], "model_version": [a["model_version"], b["model_version"]],
           "test_searches": len(names),
           "rank_response_identical": same_rest,
           "single_seeker_rank_identical": {"identical": same_rank, "of": 2 * len(names)},
           "default_variant_order_identical": same_order,
           "profiles_identical": {"identical": same_prof, "of": len(b["profiles"])},
           "political_lean_identical": a["political_lean"] == b["political_lean"],
           "generated": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if mode == "same":
        out["pass"] = (same_rest == len(names) and same_rank == 2 * len(names)
                       and same_prof == len(b["profiles"]) == len(a["profiles"])
                       and out["political_lean_identical"] and a["build"] == b["build"]
                       and a["model_version"] == b["model_version"])
        dest = HERE / f"served_numbers_{tag or 'same'}.json"
    else:
        out["rank_shift"] = {}
        rows_csv = []
        for name in ("default", "same_sex_reference"):
            s, moves = shift(a["reference"][name], b["reference"][name])
            out["rank_shift"][name] = {"body": b["reference"][name]["body"], **s}
            rows_csv += [{"search": name, **m} for m in sorted(moves, key=lambda m: m["rank_after"])]
        dest = HERE / f"rank_shift_{tag}.json"
        with open(HERE / f"rank_shift_{tag}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows_csv[0]))
            w.writeheader()
            w.writerows(rows_csv)
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rank_shift"}, indent=1))
    for name, s in out.get("rank_shift", {}).items():
        print(name, {k: s[k] for k in ("metros_compared", "ranks_changed", "kendall_tau",
                                       "median_abs_move", "p90_abs_move", "max_abs_move", "score_change")})
    print(f"-> {dest}")
    if mode == "same":
        sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    if sys.argv[1:2] == ["record"] and len(sys.argv) == 4:
        record(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ["compare"] and len(sys.argv) in (5, 6):
        compare(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) == 6 else None)
    else:
        raise SystemExit(__doc__)
