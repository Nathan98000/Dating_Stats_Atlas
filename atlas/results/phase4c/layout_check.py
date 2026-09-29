"""Phase 4c: two ways to send the search's one balance, measured against
m4.0.0's response (a copy per own sex, variants.by_sex). Both hold the
same blocks; only where they sit differs:

  columns  variants.balance: the words and every row's block together,
           aligned to the rows (what ships)
  rows     each ranked and suppressed row carries its own block again,
           the words at the top (tried first, not shipped)

For every ADR 0011 test search the shipped response comes from the API's
own path (TestClient) and is rebuilt in the rows layout — each block put
back where rank() places it, after "tier" in a ranked row and after
"flags" in a suppressed one — then both are serialised as the API
serialises (Starlette's JSONResponse) and gzipped. The before sizes are
the m4.0.0 record served_numbers_check.py wrote (_served_before.json).

    PYTHONPATH=. .venv/bin/python atlas/results/phase4c/layout_check.py <build_dir> <before.json>
        -> results/phase4c/layout_check.json
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from served_numbers_check import api_body, opposite  # noqa: E402

OUT = ROOT / "atlas" / "results" / "phase4c" / "layout_check.json"


def render(obj) -> bytes:
    """Starlette's JSONResponse.render, exactly."""
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=None,
                      separators=(",", ":")).encode("utf-8")


def after(row: dict, key: str, name: str, value) -> dict:
    out = {}
    for k, v in row.items():
        out[k] = v
        if k == key:
            out[name] = value
    assert name in out, (key, list(row))
    return out


def rows_layout(resp: dict) -> dict:
    B = resp["variants"]["balance"]
    out: dict = {}
    for k, v in resp.items():
        if k == "ranked":
            out[k] = [after(r, "tier", "balance", B["ranked"][i]) for i, r in enumerate(v)]
        elif k == "suppressed":
            out[k] = [after(r, "flags", "balance", B["suppressed"][j]) for j, r in enumerate(v)]
        elif k == "variants":
            out[k] = {kk: vv for kk, vv in v.items() if kk != "balance"}
        else:
            out[k] = v
        if k == "few_metros_notice":
            out["balance_words"] = B["balance_words"]
    return out


def sizes(b: bytes) -> dict:
    return {"bytes": len(b), "gzip6": len(gzip.compress(b, 6)), "gzip9": len(gzip.compress(b, 9))}


def main(build_dir: str, before_path: str) -> None:
    os.environ["BUILD_DIR"] = str(Path(build_dir).resolve())
    from fastapi.testclient import TestClient

    from atlas.api import app as api
    from atlas.pipeline.build import stability_gate as SG
    client = TestClient(api.app)
    before = json.loads(Path(before_path).read_text())["searches"]
    t0 = time.time()
    per: dict[str, dict] = {}
    for name, body in SG.test_searches():
        sought = body["seeking"].get("sex") or opposite(body["self"]["sex"])
        r = client.post("/v1/rank", json=api_body(body, sought))
        assert r.status_code == 200, (name, r.text)
        resp = r.json()
        assert render(resp) == r.content, f"{name}: the re-rendered response differs from the API's"
        per[name] = {"before": {k: before[name]["api"][k] for k in ("bytes", "gzip6", "gzip9")},
                     "columns": sizes(r.content), "rows": sizes(render(rows_layout(resp)))}

    def summary(layout: str) -> dict:
        ratios = {f: [per[k][layout][f] / per[k]["before"][f] for k in per] for f in ("bytes", "gzip6", "gzip9")}
        return {"larger_than_before": {f: sum(x > 1 for x in ratios[f]) for f in ratios},
                "ratio_to_before": {f: {"min": round(min(v), 4), "max": round(max(v), 4)} for f, v in ratios.items()},
                "total": {f: sum(per[k][layout][f] for k in per) for f in ("bytes", "gzip6", "gzip9")}}

    out = {"build": api.BUILD.manifest["data_version"], "model_version": api.engine.MODEL_VERSION,
           "searches": len(per),
           "before_total": {f: sum(per[k]["before"][f] for k in per) for f in ("bytes", "gzip6", "gzip9")},
           "columns_shipped": summary("columns"), "rows_not_shipped": summary("rows"),
           "default_search": per["female:30:undisclosed"],
           "same_sex_reference_search": per["persona:same_sex_pool"],
           "seconds": round(time.time() - t0, 1),
           "generated": time.strftime("%Y-%m-%dT%H:%M:%S")}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("columns_shipped", "rows_not_shipped", "default_search")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
