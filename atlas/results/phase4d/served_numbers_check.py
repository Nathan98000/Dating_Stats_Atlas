"""Phase 4d: political lean is context only, so nothing the site ranks or
scores may move. The feature adds three vote columns to features.parquet,
which gives the build a new id; the ranking must not notice.

`record` reads a build through the code checked out and writes, for every
ADR 0011 test search (stability_gate.test_searches: the golden personas,
the effects grid, the same-sex grid), digests of what is served:

  api    the /v1/rank response through the API's own path (TestClient):
         its bytes and gzipped bytes, and the digest of the whole response
         with the build id masked (data_version, and the build id inside
         the permalink) — every variant's ranks, scores, figures,
         explanations and balance
  rank   rank() for the search's seeker as male and as female (the
         single-seeker reference the goldens use), whole

and, once, the digest of each key of /v1/meta (build id masked), and
whether /v1/political_lean answers.

`compare` reads a record from before the change and one from after and
writes served_numbers_check.json: every rank response and every rank()
identical but for the build id; the /v1/meta keys that changed; the
manifest's data files that changed; the goldens, the fixture's manifest
and the shared web cases against their committed copies.

    PYTHONPATH=. .venv/bin/python atlas/results/phase4d/served_numbers_check.py record <build_dir> <out.json>
    PYTHONPATH=. .venv/bin/python atlas/results/phase4d/served_numbers_check.py compare <before.json> <after.json>
        -> results/phase4d/served_numbers_check.json
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SEXES = ("male", "female")
OUT = ROOT / "atlas" / "results" / "phase4d" / "served_numbers_check.json"


def raw(x) -> str:
    """As the API serialises it (insertion order, no spaces)."""
    return json.dumps(x, separators=(",", ":"), ensure_ascii=False)


def sha(x) -> str:
    return hashlib.sha256(raw(x).encode()).hexdigest()


def opposite(sex: str) -> str:
    return "female" if sex == "male" else "male"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout


def masked(resp: dict, dv: str) -> dict:
    out = copy.deepcopy(resp)
    if "data_version" in out:
        out["data_version"] = "<data_version>"
    if "permalink" in out:
        out["permalink"] = out["permalink"].replace(f"/{dv}/", "/<data_version>/")
    return out


def api_body(body: dict, sought: str) -> dict:
    """The m4.0.0 contract: own age only, the sought sex explicit."""
    out = {k: copy.deepcopy(body[k]) for k in ("weights", "pool_vs_match", "pool_vs_balance",
                                               "importance") if k in body}
    out["self"] = {"age": body["self"]["age"]}
    out["seeking"] = {**copy.deepcopy(body["seeking"]), "sex": sought}
    return out


def record(build_dir: str, out_path: str) -> None:
    os.environ["BUILD_DIR"] = str(Path(build_dir).resolve())
    from fastapi.testclient import TestClient

    from atlas.api import app as api
    from atlas.pipeline.build import stability_gate as SG
    engine, build = api.engine, api.BUILD
    dv = build.manifest["data_version"]
    client = TestClient(api.app)
    t0 = time.time()
    searches: dict[str, dict] = {}
    for name, body in SG.test_searches():
        self_sex = body["self"]["sex"]
        sought = body["seeking"].get("sex") or opposite(self_sex)
        r = client.post("/v1/rank", json=api_body(body, sought))
        assert r.status_code == 200, (name, r.text)
        entry = {"sought": sought, "self_sex": self_sex,
                 "api": {"bytes": len(r.content),
                         "gzip6": len(gzip.compress(r.content, 6)),
                         "digest": sha(masked(r.json(), dv))},
                 "rank": {}}
        for s in SEXES:
            b = copy.deepcopy(body)
            b["self"]["sex"] = s
            b["seeking"]["sex"] = sought
            entry["rank"][s] = sha(engine.rank(build, engine.parse_request(b)))
        searches[name] = entry
    meta = masked(client.get("/v1/meta").json(), dv)
    lean = client.get("/v1/political_lean")
    dirty = bool(git("status", "--porcelain", "--", "atlas/model", "atlas/api").strip())
    rec = {"build": dv, "model_version": engine.MODEL_VERSION,
           "code": git("rev-parse", "HEAD").strip() + ("+working-tree" if dirty else ""),
           "seconds": round(time.time() - t0, 1),
           "meta_keys": {k: sha(v) for k, v in meta.items()},
           "political_lean_endpoint": (
               {"status": lean.status_code,
                "metros": len(lean.json()["metros"]),
                "available": sum(bool(v["available"]) for v in lean.json()["metros"].values())}
               if lean.status_code == 200 else {"status": lean.status_code}),
           "searches": searches}
    Path(out_path).write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{len(searches)} searches -> {out_path} ({rec['seconds']} s)")


def diff_paths(a, b, path: str = "") -> list[str]:
    if type(a) is not type(b):
        return [path or "/"]
    if isinstance(a, dict):
        out: list[str] = []
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a or k not in b:
                out.append(f"{path}/{k}")
            else:
                out += diff_paths(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [path or "/"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_paths(x, y, f"{path}/{i}")
        return out
    return [] if a == b else [path or "/"]


def goldens_check(before_rev: str) -> dict:
    rel = "atlas/model/tests/golden/goldens.json"
    old_txt = git("show", f"{before_rev}:{rel}")
    old, new = json.loads(old_txt), json.loads((ROOT / rel).read_text())
    return {"file": rel,
            "vectors_identical": old["vectors"] == new["vectors"],
            "byte_identical": old_txt == (ROOT / rel).read_text(),
            "paths_that_differ": diff_paths(old, new),
            "model_version": [old["model_version"], new["model_version"]],
            "fixture_of": [old["fixture_of"], new["fixture_of"]]}


def manifest_check(before_rev: str, build: str) -> dict:
    rel = "atlas/results/phase2/build_manifest.json"
    old = json.loads(git("show", f"{before_rev}:{rel}"))
    d = ROOT / "atlas" / "data" / "builds" / build
    new = json.loads((d / "manifest.json").read_text())
    on_disk = {f: hashlib.sha256((d / f).read_bytes()).hexdigest() for f in new["file_sha256"]}
    so, sn = old["strings"], new["strings"]
    return {"build": [old["data_version"], new["data_version"]],
            "model_version": [old["model_version"], new["model_version"]],
            "keys_changed": sorted(k for k in set(old) | set(new)
                                   if k not in ("created_at",) and old.get(k) != new.get(k)),
            "data_files_changed": sorted(f for f in set(old["file_sha256"]) | set(new["file_sha256"])
                                         if old["file_sha256"].get(f) != new["file_sha256"].get(f)),
            "data_files_match_manifest": on_disk == new["file_sha256"],
            "strings_added": sorted(set(sn) - set(so)),
            "strings_removed": sorted(set(so) - set(sn)),
            "strings_changed": sorted(k for k in so if k in sn and so[k] != sn[k]),
            "features_added": sorted(set(new["features_block"]) - set(old["features_block"])),
            "features_changed": sorted(k for k in old["features_block"]
                                       if new["features_block"].get(k) != old["features_block"][k]),
            "stat_pages": [old["stat_pages"], new["stat_pages"]],
            "licenses_added": sorted(set(new["licenses"]) - set(old["licenses"]))}


def variant_cases_check(before_rev: str, dv_before: str, dv_after: str) -> dict:
    rel = "atlas/web/tests/variant_cases.json"
    old_txt = git("show", f"{before_rev}:{rel}")
    new_txt = (ROOT / rel).read_text()
    return {"file": rel, "byte_identical": old_txt == new_txt,
            "identical_but_the_build_id": old_txt.replace(dv_before, "<dv>")
            == new_txt.replace(dv_after, "<dv>")}


def compare(before_path: str, after_path: str) -> None:
    a = json.loads(Path(before_path).read_text())
    b = json.loads(Path(after_path).read_text())
    assert list(a["searches"]) == list(b["searches"]), "different test searches"
    names = list(a["searches"])
    fails: list[str] = []
    same_api = same_rank = same_bytes = 0
    for k in names:
        x, y = a["searches"][k], b["searches"][k]
        if x["api"]["digest"] == y["api"]["digest"]:
            same_api += 1
        else:
            fails.append(f"{k}: the rank response moved")
        if x["api"]["bytes"] == y["api"]["bytes"]:
            same_bytes += 1
        for s in SEXES:
            if x["rank"][s] == y["rank"][s]:
                same_rank += 1
            else:
                fails.append(f"{k}: rank() {s} moved")
    before_rev = a["code"].split("+")[0]
    man = manifest_check(before_rev, b["build"])
    gold = goldens_check(before_rev)
    out = {
        "build": [a["build"], b["build"]],
        "model_version": [a["model_version"], b["model_version"]],
        "code": [a["code"], b["code"]],
        "test_searches": {"total": len(names),
                          "source": "stability_gate.test_searches (ADR 0011: personas, effects grid, same-sex grid)"},
        "api_rank_response": {
            "identical_but_the_build_id": same_api,
            "same_bytes": same_bytes,
            "total_bytes": [sum(a["searches"][k]["api"]["bytes"] for k in names),
                            sum(b["searches"][k]["api"]["bytes"] for k in names)],
            "total_gzip6_bytes": [sum(a["searches"][k]["api"]["gzip6"] for k in names),
                                  sum(b["searches"][k]["api"]["gzip6"] for k in names)]},
        "single_seeker_rank": {"rankings_checked": 2 * len(names), "identical": same_rank},
        "meta_keys_changed": sorted(k for k in set(a["meta_keys"]) | set(b["meta_keys"])
                                    if a["meta_keys"].get(k) != b["meta_keys"].get(k)),
        "political_lean_endpoint": [a["political_lean_endpoint"], b["political_lean_endpoint"]],
        "manifest": man,
        "goldens": gold,
        "variant_cases": variant_cases_check(before_rev, a["build"], b["build"]),
        "failures": fails[:40],
        "pass": (not fails and gold["vectors_identical"] and man["data_files_match_manifest"]
                 and man["data_files_changed"] == ["features.parquet"]),
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("build", "model_version", "api_rank_response",
                                          "single_seeker_rank", "meta_keys_changed",
                                          "political_lean_endpoint", "failures", "pass")},
                     indent=1, ensure_ascii=False))
    print(f"-> {OUT}")
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    if sys.argv[1] == "record":
        record(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
