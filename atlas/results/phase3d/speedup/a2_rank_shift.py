"""Phase 3d A2, proof 3, measured in memory: a candidate kernel (the a2
store's artifact for a form, with the same-sex decision) loaded into the
m3.3.0 build's cubes, snapshotted exactly as phase3b_snapshot does, and
compared with the m3.3.0 snapshot — the served index's move and the rank
shift on the default search (193 metros) and on the same-sex reference
search, plus the disclosed reference searches. Nothing is built or
shipped.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/speedup/a2_rank_shift.py <form_name> <tag>
        -> results/phase3d/snapshot_<tag>.json, rank_shift_m3_3_0_to_<tag>.json/.csv
"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
os.environ["SNAPSHOT_DIR"] = str(Path(__file__).resolve().parents[1])
from atlas import model as engine
from atlas.pipeline.build import phase3b_snapshot as PS
from atlas.pipeline.build.stability_gate import _load

BUILD = "atlas/data/builds/ee4f08cf33e1"


def main(form: str, tag: str) -> None:
    kernel_dir = Path(__file__).resolve().parent / "a2" / "_candidates" / form
    build = _load(BUILD, str(kernel_dir))
    out = {"build": build.manifest["data_version"] + f" + candidate kernel {form} (a2 store, in memory)",
           "model_version": engine.MODEL_VERSION, "kernel_sample": build.kernel.meta.get("fitting_sample"),
           "default_search": PS.DEFAULT, "default": PS.summarise(engine.rank(build, engine.parse_request(PS.DEFAULT))),
           "reference": {}}
    for name, body in PS.REFERENCE.items():
        out["reference"][name] = {"body": body, **PS.summarise(engine.rank(build, engine.parse_request(body)))}
    (PS.P3B / f"snapshot_{tag}.json").write_text(json.dumps(out, indent=1) + "\n")
    PS.compare("m3_3_0", tag)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
