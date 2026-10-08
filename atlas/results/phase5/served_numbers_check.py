"""Phase 5: what the API serves, before and after each commit.

No commit may move a score, rank, pool, balance, compatibility figure, band
or suppression. Commit C changes which movers a line names and its wording
(and adds `movers` to each explanation); commit I adds one field per
variant, `score_median`. Everything else must be the same bytes.

`record` reads a build through the code on PYTHONPATH and writes, for every
ADR 0011 test search (stability_gate.test_searches):

  full     the digest of the whole /v1/rank response, the model version
           masked where it appears
  numbers  the same with the explanations taken out (variants.explain,
           the columns' explain) and any `score_median` taken off the
           variant list: everything a number lives in
  rank     the digests of rank() for the search's seeker as either sex,
           each row's top_stats, summary_line and movers taken out
  lines    the default variant's summary lines in its order

and, beside them, the digest of POST /v1/profile for every metro, of GET
/v1/political_lean, and the two reference searches' default variants
(pipeline/build/payload_size.AFTER: the site's default search and the
same-sex reference search) row by row, their lines included.

`compare <before> <after> same <tag>` passes only if every full digest is
identical. `compare <before> <after> numbers <tag>` passes if every numbers
digest is identical (the lines may change). Both write
served_numbers_<tag>.json beside this file.

    PYTHONPATH=.. ../.venv/bin/python results/phase5/served_numbers_check.py record <build_dir> <out.json>
    PYTHONPATH=.. ../.venv/bin/python results/phase5/served_numbers_check.py compare <before> <after> numbers commit_c
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEXES = ("male", "female")
EXPLAIN_ROW = ("top_stats", "summary_line", "movers")


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


def numbers_only(resp: dict) -> dict:
    out = copy.deepcopy(resp)
    v = out.get("variants") or {}
    v.pop("explain", None)
    (v.get("columns") or {}).pop("explain", None)
    for entry in v.get("list", []):
        entry.pop("score_median", None)
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
        resp = masked(r.json(), mv)
        sel = select_variant(resp)
        ranks = {}
        for s in SEXES:
            b = copy.deepcopy(body)
            b["self"]["sex"], b["seeking"]["sex"] = s, sought
            res = engine.rank(build, engine.parse_request(b))
            for row in res["ranked"]:
                for k in EXPLAIN_ROW:
                    row.pop(k, None)
            ranks[s] = sha(res)
        searches[name] = {"full": sha(resp), "numbers": sha(numbers_only(resp)), "rank": ranks,
                          "lines": [row["summary_line"] for row in sel["ranked"]]}
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
                                     "rank": row["rank"], "score": row["score"],
                                     "summary_line": row["summary_line"]}
                                    for row in sel["ranked"]]}
    Path(out_path).write_text(json.dumps({
        "build": build.manifest["data_version"], "model_version": mv,
        "seconds": round(time.time() - t0, 1), "searches": searches,
        "profiles": profiles, "political_lean": [lean.status_code, sha(lean.json())],
        "reference": reference}) + "\n")
    print(f"{len(searches)} searches, {len(profiles)} profiles -> {out_path} ({time.time() - t0:.0f} s)")


def compare(before: str, after: str, mode: str, tag: str) -> None:
    a, b = json.loads(Path(before).read_text()), json.loads(Path(after).read_text())
    assert list(a["searches"]) == list(b["searches"]), "different test searches"
    names = list(a["searches"])
    same = {f: sum(a["searches"][k][f] == b["searches"][k][f] for k in names)
            for f in ("full", "numbers")}
    same_rank = sum(a["searches"][k]["rank"][s] == b["searches"][k]["rank"][s]
                    for k in names for s in SEXES)
    rows = changed = 0
    for k in names:
        la, lb = a["searches"][k]["lines"], b["searches"][k]["lines"]
        rows += len(lb)
        changed += sum(x != y for x, y in zip(la, lb))
    same_prof = sum(a["profiles"].get(c) == h for c, h in b["profiles"].items())
    ref_numbers = {name: [{k: r[k] for k in ("cbsa", "rank", "score")} for r in a["reference"][name]["rows"]]
                   == [{k: r[k] for k in ("cbsa", "rank", "score")} for r in b["reference"][name]["rows"]]
                   for name in a["reference"]}
    out = {"build": [a["build"], b["build"]], "model_version": [a["model_version"], b["model_version"]],
           "mode": mode,
           "test_searches": {"total": len(names),
                             "source": "stability_gate.test_searches (ADR 0011: personas, effects grid, same-sex grid)"},
           "rank_response_identical": same["full"],
           "rank_response_identical_without_explanations": same["numbers"],
           "single_seeker_rank_identical_without_explanations": {"identical": same_rank, "of": 2 * len(names)},
           "default_variant_lines": {"rows": rows, "changed": changed},
           "profiles_identical": {"identical": same_prof, "of": len(b["profiles"])},
           "political_lean_identical": a["political_lean"] == b["political_lean"],
           "reference_searches_rank_and_score_identical": ref_numbers,
           "generated": time.strftime("%Y-%m-%dT%H:%M:%S")}
    key = "full" if mode == "same" else "numbers"
    out["pass"] = (same[key] == len(names) and same_rank == 2 * len(names)
                   and same_prof == len(b["profiles"]) == len(a["profiles"])
                   and out["political_lean_identical"] and all(ref_numbers.values())
                   and a["build"] == b["build"])
    dest = HERE / f"served_numbers_{tag}.json"
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"-> {dest}")
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    if sys.argv[1:2] == ["record"] and len(sys.argv) == 4:
        record(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ["compare"] and len(sys.argv) == 6:
        compare(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        raise SystemExit(__doc__)
