"""Phase 3d A1: would the goldens change under a candidate kernel? The
candidate artifact is sliced to the pinned 12-metro fixture exactly as
make_fixture.py slices the shipped one, swapped into the fixture build in
memory, and the golden vectors are run and compared with the committed
goldens.json (rankings, scores, score displays, match indices, pools,
suppression). Nothing on disk changes.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/speedup/a1_goldens_check.py <kernel_dir> <out_json>
"""
import json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from atlas import model as engine
from atlas.model.loader import _load_kernel
from atlas.model.tests.golden.make_fixture import FIXTURE, HERE


def sliced_kernel(kernel_dir: Path, chosen: list[str], tmp: Path):
    kz = np.load(kernel_dir / "kernel.npz", allow_pickle=False)
    kj = json.loads((kernel_dir / "kernel.json").read_text())
    levels = list(kz["metro_levels"])
    idx = [levels.index(c) for c in chosen]
    arrays = {k: kz[k] for k in kz.files}
    arrays["metro_levels"] = np.array(chosen)
    for k in ("dials", "log_norm", "ss_log_norm"):
        if k in arrays:
            arrays[k] = arrays[k][idx]
    kj["dials"] = {c: kj["dials"][c] for c in chosen}
    tmp.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(tmp / "kernel.npz", **arrays)
    (tmp / "kernel.json").write_text(json.dumps(kj, indent=1) + "\n")
    return _load_kernel(tmp, chosen)


def main(kernel_dir: str, out_path: str) -> None:
    goldens = json.loads((HERE / "goldens.json").read_text())
    build = engine.load_build(FIXTURE, allow_model_mismatch=True)
    tmp = Path(out_path).with_suffix("") .parent / "_fixture_kernel_tmp"
    build = replace(build, kernel=sliced_kernel(Path(kernel_dir), build.metro_levels, tmp))
    out = {"kernel": str(kernel_dir), "goldens_model_version": goldens["model_version"],
           "engine_model_version": engine.MODEL_VERSION, "vectors": {}, "unchanged": True,
           "compared": ["ranking", "scores", "score_displays", "match_index", "pools", "suppressed", "shown_unranked_cbsas"]}
    worst_score = 0.0
    worst_index = 0.0
    for v in goldens["vectors"]:
        res = engine.rank(build, engine.parse_request(v["request"]))
        exp = v["expect"]
        got = {"ranking": [r["cbsa"] for r in res["ranked"]],
               "scores": {r["cbsa"]: r["score"] for r in res["ranked"]},
               "score_displays": {r["cbsa"]: r["score_display"] for r in res["ranked"]},
               "match_index": {r["cbsa"]: r["match"]["value"] for r in res["ranked"]},
               "pools": {r["cbsa"]: r["pool"] for r in res["ranked"]},
               "suppressed": {r["cbsa"]: r["reason"] for r in res["suppressed"]},
               "shown_unranked_cbsas": sorted(r["cbsa"] for r in res["shown_unranked"])}
        rec = {}
        for k in out["compared"]:
            if k not in exp:
                continue
            rec[k] = bool(got[k] == exp[k])
            if not rec[k]:
                out["unchanged"] = False
        if "scores" in exp and set(exp["scores"]) == set(got["scores"]) and exp["scores"]:
            ds = max(abs(float(got["scores"][c]) - float(exp["scores"][c])) for c in exp["scores"])
            rec["max_abs_score_diff"] = ds
            worst_score = max(worst_score, ds)
        if "match_index" in exp and set(exp["match_index"]) == set(got["match_index"]) and exp["match_index"]:
            di = max(abs(float(got["match_index"][c] or 0) - float(exp["match_index"][c] or 0)) for c in exp["match_index"])
            rec["max_abs_match_index_diff"] = di
            worst_index = max(worst_index, di)
        out["vectors"][v["name"]] = rec
    out["max_abs_score_diff"] = worst_score
    out["max_abs_match_index_diff"] = worst_index
    Path(out_path).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("kernel", "unchanged", "max_abs_score_diff", "max_abs_match_index_diff")}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
