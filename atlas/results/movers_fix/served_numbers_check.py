"""m4.1.1, the movers line: only which items a summary line names may
change. Every score, rank, figure, band and suppression must be what m4.1.0
served, over the ADR 0011 test searches on the same data.

`record` reads a build through the code on PYTHONPATH (m4.1.0's code with
the m4.1.0 manifest, or m4.1.1's with its refreshed manifest; the data files
are the same) and writes, for every test search:

  rest   the digest of the /v1/rank response (the API's own path) with
         the explanations taken out (variants.explain and the columns'
         explain), and the version masked where it appears
  rank   the digests of rank() for the search's seeker as either sex, with
         each row's top_stats and summary_line taken out
  lines  the default variant's summary lines, in its order, each read
         against its row's cards: a phrase named twice, or a stat named
         against the side its card puts the city on (a minus where the card
         says better than most, a plus where it says worse)

`compare` reads the two records and writes served_numbers_check.json.

    PYTHONPATH=<m4.1.0 code> python atlas/results/movers_fix/served_numbers_check.py record <m4.1.0 build> <before.json>
    PYTHONPATH=. python atlas/results/movers_fix/served_numbers_check.py record <m4.1.1 build> <after.json>
    PYTHONPATH=. python atlas/results/movers_fix/served_numbers_check.py compare <before.json> <after.json>
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent / "served_numbers_check.json"
SEXES = ("male", "female")


def sha(x) -> str:
    return hashlib.sha256(json.dumps(x, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def opposite(sex: str) -> str:
    return "female" if sex == "male" else "male"


def api_body(body: dict, sought: str) -> dict:
    out = {k: copy.deepcopy(body[k]) for k in ("weights", "pool_vs_match", "pool_vs_balance",
                                               "importance") if k in body}
    out["self"] = {"age": body["self"]["age"]}
    out["seeking"] = {**copy.deepcopy(body["seeking"]), "sex": sought}
    return out


def without_explanations(resp: dict, mv: str) -> dict:
    out = copy.deepcopy(resp)
    out.pop("model_version", None)
    out["permalink"] = out.get("permalink", "").replace(f"/{mv}/", "/<model_version>/")
    v = out.get("variants") or {}
    v.pop("explain", None)
    (v.get("columns") or {}).pop("explain", None)
    return out


def read_line(line: str, sides: dict[str, int]) -> dict:
    """The phrases a line names, and whether it repeats one or names one
    against its card."""
    head, _, tail = line.partition(" · ")
    pluses, minus = [], None
    if head.startswith("Biggest pluses: "):
        pluses = head[len("Biggest pluses: "):].split(", ")
        if tail:
            minus = tail
    elif head.endswith(" counts against it"):
        minus = head
    if minus:
        minus = minus[:-len(" counts against it")]
        minus = minus[0].lower() + minus[1:]
    named = pluses + ([minus] if minus else [])
    return {"repeated": len(named) != len(set(named)),
            "against_card": any(sides.get(p, 0) < 0 for p in pluses)
            or (minus is not None and sides.get(minus, 0) > 0)}


def record(build_dir: str, out_path: str) -> None:
    os.environ["BUILD_DIR"] = str(Path(build_dir).resolve())
    from fastapi.testclient import TestClient

    from atlas.api import app as api
    from atlas.model.variants import select_variant
    from atlas.pipeline.build import stability_gate as SG
    engine, build = api.engine, api.BUILD
    mv = engine.MODEL_VERSION
    legend = build.legend
    keys = build.manifest["standing_bands"]["keys"]
    mid = (len(keys) - 1) / 2
    position = {k: (i > mid) - (i < mid) for i, k in enumerate(keys)}
    phrase = lambda fid: (legend[fid].get("mover_phrase") or legend[fid]["display_name"]).lower()  # noqa: E731

    def sides_of(row: dict) -> dict[str, int]:
        """Each named phrase's side, read from the row's cards the way
        explain.mover_sides reads it (written out here so the m4.1.0 code
        is read by the same rule)."""
        out = {}
        by_id = {c["id"]: c for c in row["cards"]}
        for s in row["stats"]:
            p = phrase(s["id"])
            card = by_id.get(s["id"]) or next((c for c in row["cards"] if phrase(c["id"]) == p), None)
            band = (card or {}).get("band")
            out[p] = int(legend[s["id"]]["direction"]) * position[band["key"]] if band else 0
        return out

    client = TestClient(api.app)
    t0 = time.time()
    searches = {}
    for name, body in SG.test_searches():
        sought = body["seeking"].get("sex") or opposite(body["self"]["sex"])
        r = client.post("/v1/rank", json=api_body(body, sought))
        assert r.status_code == 200, (name, r.text)
        resp = r.json()
        sel = select_variant(resp)
        lines = [{"cbsa": row["cbsa"], "line": row["summary_line"],
                  **read_line(row["summary_line"], sides_of(row))} for row in sel["ranked"]]
        ranks = {}
        for s in SEXES:
            b = copy.deepcopy(body)
            b["self"]["sex"], b["seeking"]["sex"] = s, sought
            res = engine.rank(build, engine.parse_request(b))
            for row in res["ranked"]:
                row.pop("top_stats"), row.pop("summary_line")
            ranks[s] = sha(res)
        searches[name] = {"rest": sha(without_explanations(resp, mv)), "rank": ranks, "lines": lines}
    Path(out_path).write_text(json.dumps({"build": build.manifest["data_version"], "model_version": mv,
                                          "seconds": round(time.time() - t0, 1),
                                          "searches": searches}) + "\n")
    print(f"{len(searches)} searches -> {out_path} ({time.time() - t0:.0f} s)")


def compare(before: str, after: str) -> None:
    a, b = json.loads(Path(before).read_text()), json.loads(Path(after).read_text())
    assert list(a["searches"]) == list(b["searches"]), "different test searches"
    names = list(a["searches"])
    fails = []
    same_rest = same_rank = rows = changed = 0
    tally = {"repeated": [0, 0], "against_card": [0, 0]}
    examples = []
    for k in names:
        x, y = a["searches"][k], b["searches"][k]
        if x["rest"] == y["rest"]:
            same_rest += 1
        else:
            fails.append(f"{k}: the response moved beyond its explanations")
        for s in SEXES:
            if x["rank"][s] == y["rank"][s]:
                same_rank += 1
            else:
                fails.append(f"{k}: rank() {s} moved beyond its explanations")
        if [r["cbsa"] for r in x["lines"]] != [r["cbsa"] for r in y["lines"]]:
            fails.append(f"{k}: the default variant's order moved")
            continue
        for rx, ry in zip(x["lines"], y["lines"]):
            rows += 1
            for t in tally:
                tally[t][0] += rx[t]
                tally[t][1] += ry[t]
            if rx["line"] != ry["line"]:
                changed += 1
                if (rx["repeated"] or rx["against_card"]) and len(examples) < 8:
                    examples.append({"search": k, "cbsa": rx["cbsa"], "before": rx["line"],
                                     "after": ry["line"]})
    if tally["repeated"][1] or tally["against_card"][1]:
        fails.append("an m4.1.1 line repeats a phrase or names a stat against its card")
    out = {"build": [a["build"], b["build"]],
           "model_version": [a["model_version"], b["model_version"]],
           "test_searches": {"total": len(names),
                             "source": "stability_gate.test_searches (ADR 0011: personas, effects grid, same-sex grid)"},
           "response_without_explanations": {"identical": same_rest, "of": len(names)},
           "single_seeker_rank_without_explanations": {"identical": same_rank, "of": 2 * len(names)},
           "default_variant_lines": {
               "rows": rows, "changed": changed,
               "repeating_a_phrase": {"m4.1.0": tally["repeated"][0], "m4.1.1": tally["repeated"][1]},
               "naming_a_stat_against_its_card": {"m4.1.0": tally["against_card"][0],
                                                  "m4.1.1": tally["against_card"][1]}},
           "examples": examples,
           "failures": fails[:40], "pass": not fails,
           "generated": time.strftime("%Y-%m-%dT%H:%M:%S")}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("model_version", "response_without_explanations",
                                          "single_seeker_rank_without_explanations",
                                          "default_variant_lines", "failures", "pass")},
                     indent=1, ensure_ascii=False))
    print(f"-> {OUT}")
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    if sys.argv[1:2] == ["record"] and len(sys.argv) == 4:
        record(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ["compare"] and len(sys.argv) == 4:
        compare(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
