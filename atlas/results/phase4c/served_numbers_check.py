"""Phase 4c (ADR 0004 amended, Nathan's decision): what the balance change
moves, and what it may not. Dating pool balance becomes the single people
of the sought sex per 100 single people of the OTHER sex, so it no longer
depends on the visitor's own sex: a same-sex search shows the figure an
opposite-sex search for the same people shows. Nothing scored reads
balance (since m3.0.0), so every score and rank must stay exactly as it
was.

`record` reads a build through the code checked out and writes, for every
ADR 0011 test search (stability_gate.test_searches: the golden personas,
the effects grid, the same-sex grid), digests of what is served:

  api    the /v1/rank response through the API's own path (TestClient): its
         bytes and gzipped bytes; the digest of everything but balance (rows
         without their balance block, variants without by_sex, no
         balance_words or balance_applies at the top; the model version
         masked) — every variant's ranks, scores, figures and explanations;
         and, per own sex, the digest of the balance that own sex is shown
         (its words and the block of every ranked and left-out row, as the
         API serialises them)
  rank   rank() for the search's seeker as male and as female (the
         single-seeker reference the goldens use): the digest of everything
         but balance, and the digest of the balance

`compare` reads a record from before the change and one from after and
writes served_numbers_check.json: everything but balance identical; the
opposite-sex balance byte-identical; the same-sex balance after equal to
the opposite-sex balance of the same search; every same-sex block before
not applicable; no response larger. It also holds the persona snapshot and
the goldens against their m4.0.0 records, and the shared variant cases
against theirs.

    PYTHONPATH=. .venv/bin/python atlas/results/phase4c/served_numbers_check.py record <build_dir> <out.json>
    PYTHONPATH=. .venv/bin/python atlas/results/phase4c/served_numbers_check.py compare <before.json> <after.json>
        -> results/phase4c/served_numbers_check.json
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
OUT = ROOT / "atlas" / "results" / "phase4c" / "served_numbers_check.json"
EXAMPLE = "persona:same_sex_pool"


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


def without_balance(resp: dict, mv: str | None = None) -> dict:
    out = copy.deepcopy(resp)
    for k in ("balance_applies", "balance_words"):
        out.pop(k, None)
    for part in ("ranked", "suppressed", "shown_unranked"):
        for r in out.get(part, []):
            r.pop("balance", None)
    if "variants" in out:
        out["variants"].pop("by_sex", None)
        out["variants"].pop("balance", None)
    if mv is not None:
        out["model_version"] = "<model_version>"
        out["permalink"] = out["permalink"].replace(f"/{mv}/", "/<model_version>/")
    return out


def rows_balance(words: dict, rows: list[dict], blocks: list[dict]) -> dict:
    """A balance keyed by metro (sorted), so two orders of the same rows
    compare equal; each block keeps the order its keys were served in."""
    by = {r["cbsa"]: b for r, b in zip(rows, blocks)}
    return {"words": words, "rows": {c: by[c] for c in sorted(by)}}


def api_balance(resp: dict) -> dict[str, dict]:
    """The balance each own sex is shown, one shape for both contracts:
    m4.0.0's variants.by_sex (a copy per own sex), and since Phase 4c
    variants.balance (one for the search)."""
    V = resp["variants"]
    rows = resp["ranked"] + resp["suppressed"]
    if "by_sex" in V:
        return {s: rows_balance(V["by_sex"][s]["balance_words"], rows,
                                V["by_sex"][s]["ranked"] + V["by_sex"][s]["suppressed"])
                for s in SEXES}
    B = V["balance"]
    one = rows_balance(B["balance_words"], rows, B["ranked"] + B["suppressed"])
    return {s: one for s in SEXES}


def api_applies(resp: dict) -> dict[str, bool | None]:
    V = resp["variants"]
    if "by_sex" in V:
        return {s: V["by_sex"][s]["balance_applies"] for s in SEXES}
    return {s: resp.get("balance_applies") for s in SEXES}


def blocks_summary(bal: dict) -> dict:
    blocks = list(bal["rows"].values())
    return {"rows": len(blocks), "available": sum(bool(b["available"]) for b in blocks),
            "notes": sorted({b.get("note") for b in blocks if not b["available"]})}


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
    mv = engine.MODEL_VERSION
    client = TestClient(api.app)
    t0 = time.time()
    searches: dict[str, dict] = {}
    for name, body in SG.test_searches():
        self_sex = body["self"]["sex"]
        sought = body["seeking"].get("sex") or opposite(self_sex)
        r = client.post("/v1/rank", json=api_body(body, sought))
        assert r.status_code == 200, (name, r.text)
        resp = r.json()
        bal = api_balance(resp)
        entry = {"sought": sought, "self_sex": self_sex,
                 "api": {"bytes": len(r.content),
                         "gzip6": len(gzip.compress(r.content, 6)),
                         "gzip9": len(gzip.compress(r.content, 9)),
                         "ranked": len(resp["ranked"]), "suppressed": len(resp["suppressed"]),
                         "nb": sha(without_balance(resp, mv)),
                         "bal": {s: sha(bal[s]) for s in SEXES},
                         "applies": api_applies(resp),
                         "blocks": {s: blocks_summary(bal[s]) for s in SEXES}},
                 "rank": {}}
        for s in SEXES:
            b = copy.deepcopy(body)
            b["self"]["sex"] = s
            b["seeking"]["sex"] = sought
            out = engine.rank(build, engine.parse_request(b))
            rows = out["ranked"] + out["suppressed"]
            entry["rank"][s] = {
                "nb": sha(without_balance(out)),
                "bal": sha(rows_balance(out["balance_words"], rows, [x["balance"] for x in rows])),
                "applies": out.get("balance_applies")}
        if name == EXAMPLE:
            entry["example"] = [
                {"cbsa": x["cbsa"], "city": x["display_name"],
                 **{s: (bal[s]["rows"][x["cbsa"]].get("display")
                        or bal[s]["rows"][x["cbsa"]].get("note")) for s in SEXES}}
                for x in resp["ranked"][:5]]
        searches[name] = entry
    dirty = bool(git("status", "--porcelain", "--", "atlas/model", "atlas/api").strip())
    rec = {"build": build.manifest["data_version"], "model_version": mv,
           "code": git("rev-parse", "HEAD").strip() + ("+working-tree" if dirty else ""),
           "seconds": round(time.time() - t0, 1), "searches": searches}
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
    old = json.loads(git("show", f"{before_rev}:{rel}"))
    new = json.loads((ROOT / rel).read_text())
    named = lambda g: {**{k: v for k, v in g.items() if k != "vectors"},  # noqa: E731
                       "vectors": {v["name"]: v for v in g["vectors"]}}
    paths = diff_paths(named(old), named(new))
    # a path is /vectors/<name>/expect/<field>/<metro>
    moved = sorted({p.split("/")[2] for p in paths if p.startswith("/vectors/")})
    fields = sorted({p.split("/")[4] for p in paths if p.startswith("/vectors/")
                     and len(p.split("/")) > 4})
    ss = new["vectors"][[v["name"] for v in new["vectors"]].index("same_sex_pool")]["expect"]
    return {"file": rel,
            "sha256_before": hashlib.sha256(git("show", f"{before_rev}:{rel}").encode()).hexdigest(),
            "sha256_after": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(),
            "model_version": [old["model_version"], new["model_version"]],
            "vectors_moved": moved, "fields_moved": fields,
            "other_paths": [p for p in paths if not p.startswith("/vectors/")],
            "same_sex_pool_after": {"balance_per_100": ss["balance_per_100"],
                                    "suppressed_balance_available": ss["suppressed_balance_available"]}}


def snapshot_check() -> dict:
    res = ROOT / "atlas" / "results"
    a = res / "phase4" / "snapshot_m4_0_0.json"
    b = res / "phase4c" / "snapshot_m4_1_0.json"
    if not b.exists():
        return {"missing": str(b.relative_to(ROOT))}
    pa, pb = json.loads(a.read_text()), json.loads(b.read_text())
    return {"m4_0_0_record": str(a.relative_to(ROOT / "atlas")),
            "m4_1_0_record": str(b.relative_to(ROOT / "atlas")),
            "paths_that_differ": diff_paths(pa, pb),
            "identical_but_the_model_version": diff_paths(pa, pb) == ["/model_version"]}


def variant_cases_check(before_rev: str) -> dict:
    rel = "atlas/web/tests/variant_cases.json"
    old = json.loads(git("show", f"{before_rev}:{rel}"))
    new = json.loads((ROOT / rel).read_text())
    out: dict = {"file": rel, "model_version": [old["model_version"], new["model_version"]],
                 "cases": {}}
    for co, cn in zip(old["cases"], new["cases"]):
        assert co["name"] == cn["name"]
        ro, rn = co["response"], cn["response"]
        sels = []
        for so, sn in zip(co["selections"], cn["selections"]):
            assert so["about"] == sn["about"]
            eo, en = so["expected"], sn["expected"]
            sels.append({"about": so["about"],
                         "everything_but_balance_identical":
                             raw(without_balance(eo, old["model_version"]))
                             == raw(without_balance(en, new["model_version"])),
                         "balance_identical": raw(rows_balance(eo["balance_words"], eo["ranked"] + eo["suppressed"],
                                                               [x["balance"] for x in eo["ranked"] + eo["suppressed"]]))
                         == raw(rows_balance(en["balance_words"], en["ranked"] + en["suppressed"],
                                             [x["balance"] for x in en["ranked"] + en["suppressed"]]))})
        out["cases"][co["name"]] = {
            "response_everything_but_balance_identical":
                raw(without_balance(ro, old["model_version"])) == raw(without_balance(rn, new["model_version"])),
            "response_bytes": [len(raw(ro)), len(raw(rn))],
            "selections": len(sels),
            "selections_everything_but_balance_identical": sum(s["everything_but_balance_identical"] for s in sels),
            "selections_balance_identical": sum(s["balance_identical"] for s in sels),
            "selections_balance_moved": [s["about"] for s in sels if not s["balance_identical"]]}
    return out


def manifest_check(before_rev: str, build: str) -> dict:
    """The build keeps its id: every data file still matches the hash its
    manifest names, and the manifest differs from m4.0.0's committed copy
    (results/phase2/build_manifest.json) only in its stamp, the model
    version and the registry strings."""
    rel = "atlas/results/phase2/build_manifest.json"
    old = json.loads(git("show", f"{before_rev}:{rel}"))
    d = ROOT / "atlas" / "data" / "builds" / build
    new = json.loads((d / "manifest.json").read_text())
    on_disk = {f: hashlib.sha256((d / f).read_bytes()).hexdigest() for f in new["file_sha256"]}
    so, sn = old["strings"], new["strings"]
    return {"build": build, "data_version": [old["data_version"], new["data_version"]],
            "keys_changed": sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k)),
            "model_version": [old["model_version"], new["model_version"]],
            "strings_added": {k: sn[k] for k in sorted(set(sn) - set(so))},
            "strings_removed": sorted(set(so) - set(sn)),
            "strings_changed": sorted(k for k in so if k in sn and so[k] != sn[k]),
            "file_sha256_unchanged": old["file_sha256"] == new["file_sha256"],
            "data_files_match_manifest": on_disk == new["file_sha256"],
            "data_files": len(on_disk)}


def compare(before_path: str, after_path: str) -> None:
    a = json.loads(Path(before_path).read_text())
    b = json.loads(Path(after_path).read_text())
    assert list(a["searches"]) == list(b["searches"]), "different test searches"
    names = list(a["searches"])
    n = len(names)
    same_sex = [k for k in names if a["searches"][k]["self_sex"] == a["searches"][k]["sought"]]
    api = {"nb": 0, "os_bal": 0, "ss_bal_eq_os": 0, "ss_before_not_applicable": 0,
           "ss_after_available_rows": 0, "ss_after_rows": 0}
    rank = {"nb": 0, "os_bal": 0, "ss_bal_eq_os": 0}
    fails: list[str] = []
    grew: list[dict] = []
    ratios = []
    notes_before: set[str] = set()
    for k in names:
        x, y = a["searches"][k], b["searches"][k]
        sought = x["sought"]
        os_sex, ss_sex = opposite(sought), sought
        if x["api"]["nb"] == y["api"]["nb"]:
            api["nb"] += 1
        else:
            fails.append(f"{k}: api everything-but-balance")
        if x["api"]["bal"][os_sex] == y["api"]["bal"][os_sex]:
            api["os_bal"] += 1
        else:
            fails.append(f"{k}: api opposite-sex balance")
        if y["api"]["bal"][ss_sex] == x["api"]["bal"][os_sex]:
            api["ss_bal_eq_os"] += 1
        else:
            fails.append(f"{k}: api same-sex balance != opposite-sex")
        bs = x["api"]["blocks"][ss_sex]
        notes_before.update(n_ for n_ in bs["notes"] if n_)
        if bs["available"] == 0 and x["api"]["applies"][ss_sex] is False:
            api["ss_before_not_applicable"] += 1
        api["ss_after_rows"] += y["api"]["blocks"][ss_sex]["rows"]
        api["ss_after_available_rows"] += y["api"]["blocks"][ss_sex]["available"]
        for s in SEXES:
            if x["rank"][s]["nb"] == y["rank"][s]["nb"]:
                rank["nb"] += 1
            else:
                fails.append(f"{k}: rank() {s} everything-but-balance")
        if x["rank"][os_sex]["bal"] == y["rank"][os_sex]["bal"]:
            rank["os_bal"] += 1
        else:
            fails.append(f"{k}: rank() opposite-sex balance")
        if y["rank"][ss_sex]["bal"] == x["rank"][os_sex]["bal"]:
            rank["ss_bal_eq_os"] += 1
        else:
            fails.append(f"{k}: rank() same-sex balance != opposite-sex")
        ratio = y["api"]["gzip6"] / x["api"]["gzip6"]
        ratios.append(ratio)
        if y["api"]["bytes"] > x["api"]["bytes"] or y["api"]["gzip6"] > x["api"]["gzip6"]:
            grew.append({"search": k, "bytes": [x["api"]["bytes"], y["api"]["bytes"]],
                         "gzip6": [x["api"]["gzip6"], y["api"]["gzip6"]]})

    def size(k: str) -> dict:
        x, y = a["searches"][k]["api"], b["searches"][k]["api"]
        return {f: [x[f], y[f]] for f in ("bytes", "gzip6", "gzip9")} | {"ranked": x["ranked"]}

    before_rev = a["code"].split("+")[0]
    out = {
        "build": b["build"],
        "model_version": [a["model_version"], b["model_version"]],
        "code": [a["code"], b["code"]],
        "test_searches": {"total": n, "same_sex": len(same_sex), "opposite_sex": n - len(same_sex),
                          "source": "stability_gate.test_searches (ADR 0011: personas, effects grid, same-sex grid)"},
        "api_rank_response": {
            "everything_but_balance_identical": api["nb"],
            "opposite_sex_balance_byte_identical": api["os_bal"],
            "same_sex_balance_equals_the_opposite_sex_balance": api["ss_bal_eq_os"],
            "same_sex_balance_before_not_applicable": api["ss_before_not_applicable"],
            "same_sex_notes_before": sorted(notes_before),
            "same_sex_rows_after": api["ss_after_rows"],
            "same_sex_rows_after_available": api["ss_after_available_rows"],
            "responses_larger_after": grew,
            "gzip6_ratio_after_over_before": {"min": round(min(ratios), 4), "max": round(max(ratios), 4)},
            "total_bytes": [sum(a["searches"][k]["api"]["bytes"] for k in names),
                            sum(b["searches"][k]["api"]["bytes"] for k in names)],
            "total_gzip6_bytes": [sum(a["searches"][k]["api"]["gzip6"] for k in names),
                                  sum(b["searches"][k]["api"]["gzip6"] for k in names)],
            "default_search": size("female:30:undisclosed"),
            "same_sex_reference_search": size(EXAMPLE),
        },
        "single_seeker_rank": {
            "rankings_checked": 2 * n,
            "everything_but_balance_identical": rank["nb"],
            "opposite_sex_balance_byte_identical": rank["os_bal"],
            "same_sex_balance_equals_the_opposite_sex_balance": rank["ss_bal_eq_os"],
        },
        "example_man_seeking_men_27_38": {"search": EXAMPLE,
                                          "before": a["searches"][EXAMPLE].get("example"),
                                          "after": b["searches"][EXAMPLE].get("example")},
        "manifest": manifest_check(before_rev, b["build"]),
        "goldens": goldens_check(before_rev),
        "snapshot": snapshot_check(),
        "variant_cases": variant_cases_check(before_rev),
        "failures": fails[:40],
        "pass": not fails and not grew and manifest_check(before_rev, b["build"])["data_files_match_manifest"],
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("test_searches", "api_rank_response", "single_seeker_rank",
                                          "pass")}, indent=1, ensure_ascii=False)[:4000])
    print(f"-> {OUT}")
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    if sys.argv[1] == "record":
        record(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
