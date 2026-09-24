"""What each Part B refinement does to the SERVED index (the brief's B2
question, answered for every refinement the same way): the candidate
kernel (kernel_refine.py candidate --form <name>) loaded into the m3.1.0
build in memory beside the baseline form's candidate, and the index
compared over a grid of disclosed seekers — both sexes, ages 25/30/35/
40/50, every education level and race group, the site's default window
— plus the eighteen golden personas. Writes results/phase3b/
refine_effects.json and refine_effects_<form>.csv: per search the median
and largest absolute change across the ranked metros, the Kendall tau of
the index, whether the top city by the index changes, and the top-10 of
the full score under default weights; and the ten most affected searches
with their top city before and after.

    python -m atlas.pipeline.build.phase3b_refine_effects <build_dir> <form> [<form> ...]
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from atlas import model as engine
from atlas.model.loader import _load_kernel
from atlas.model.preferences import EDU_LEVELS, RACE_LEVELS, SEX_LEVELS, SPEC_RACE
from atlas.model.scoring import match_index
from atlas.model.tests.golden.make_fixture import GOLDEN_VECTORS
from atlas.pipeline.fetch import RESULTS

P3B = RESULTS / "phase3b"
CUBE_TO_SPEC = {v: k for k, v in SPEC_RACE.items()}


def body_for(sex, age, edu=None, race=None):
    self_ = {"sex": sex, "age": age}
    if edu:
        self_["education"] = edu
    if race:
        self_["race_ethnicity"] = CUBE_TO_SPEC[race]
    return {"self": self_, "seeking": {"age": [max(18, age - 2), min(70, age + 10)],
                                       "marital": ["never_married", "previously_married"]}}


def main(build_dir: str, forms: list[str]) -> None:
    build = engine.load_build(build_dir, allow_model_mismatch=True)
    ranked = build.ranked_set
    names = np.array(build.display_names)
    base = replace(build, kernel=_load_kernel(P3B / "_candidates" / "baseline", build.metro_levels))
    searches = [("persona:" + v["name"], {k: v[k] for k in ("self", "seeking") if k in v}) for v in GOLDEN_VECTORS]
    for sex in SEX_LEVELS:
        for age in (25, 30, 35, 40, 50):
            searches.append((f"{sex}:{age}:undisclosed", body_for(sex, age)))
            for e in EDU_LEVELS:
                searches.append((f"{sex}:{age}:edu={e}", body_for(sex, age, edu=e)))
            for r in RACE_LEVELS:
                searches.append((f"{sex}:{age}:race={r}", body_for(sex, age, race=r)))
            for e in EDU_LEVELS:
                for r in RACE_LEVELS:
                    searches.append((f"{sex}:{age}:edu={e}:race={r}", body_for(sex, age, edu=e, race=r)))
    out = {"build": build.manifest["data_version"], "searches": len(searches), "forms": {}}
    for form in forms:
        alt = replace(build, kernel=_load_kernel(P3B / "_candidates" / form, build.metro_levels))
        rows = []
        for name, body in searches:
            req = engine.parse_request(body)
            a = match_index(base, req)["index"][ranked]
            b = match_index(alt, req)["index"][ranked]
            ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() < 10:
                continue
            d = np.abs(b - a)[ok]
            ta = names[ranked][np.argsort(-np.where(ok, a, -np.inf))[:3]]
            tb = names[ranked][np.argsort(-np.where(ok, b, -np.inf))[:3]]
            top_a = [r["cbsa"] for r in engine.rank(base, req)["ranked"][:10]]
            top_b = [r["cbsa"] for r in engine.rank(alt, req)["ranked"][:10]]
            rows.append({"search": name, "metros": int(ok.sum()),
                         "median_abs_change_pts": round(float(np.median(d)), 2),
                         "p90_abs_change_pts": round(float(np.percentile(d, 90)), 2),
                         "max_abs_change_pts": round(float(d.max()), 2),
                         "kendall_tau_index": round(float(kendalltau(a[ok], b[ok]).statistic), 3),
                         "top_by_index_before": " | ".join(ta), "top_by_index_after": " | ".join(tb),
                         "top1_changes": bool(ta[0] != tb[0]),
                         "top10_score_overlap": len(set(top_a) & set(top_b))})
        df = pd.DataFrame(rows)
        df.to_csv(P3B / f"refine_effects_{form}.csv", index=False)
        big = df.sort_values("median_abs_change_pts", ascending=False).head(10)
        out["forms"][form] = {
            "searches": int(len(df)),
            "median_of_median_abs_change_pts": round(float(df["median_abs_change_pts"].median()), 2),
            "p90_of_median_abs_change_pts": round(float(df["median_abs_change_pts"].quantile(0.9)), 2),
            "largest_median_abs_change_pts": round(float(df["median_abs_change_pts"].max()), 2),
            "searches_where_top1_changes": int(df["top1_changes"].sum()),
            "min_kendall_tau_index": round(float(df["kendall_tau_index"].min()), 3),
            "median_kendall_tau_index": round(float(df["kendall_tau_index"].median()), 3),
            "min_top10_score_overlap": int(df["top10_score_overlap"].min()),
            "personas_median_abs_change_pts": round(float(df[df["search"].str.startswith("persona:")]
                                                          ["median_abs_change_pts"].median()), 2),
            "most_affected": big.to_dict(orient="records")}
        print(form, json.dumps({k: v for k, v in out["forms"][form].items() if k != "most_affected"}), flush=True)
    (P3B / "refine_effects.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
