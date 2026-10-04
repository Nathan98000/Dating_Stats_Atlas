"""Phase 4e: nice days a year per metro, before (m4.1.1's rule, as served by
build 2dbd9ebfa7ff) and after (Nathan's new rule, the new build).

Reads each build's own served values (Build.static["pleasant_days"]), the
station table each was computed from, and the old rule re-run on the
re-fetched station files (which separates NOAA's revisions to the
historical record since 2026-09-17 from the rule change itself). Writes:

  nice_days.json            the distribution before and after (all 387 and
                            the 193 ranked), the 10 biggest drops and rises,
                            the top and bottom 10 under the new rule, the
                            metros with no qualifying station before and
                            after, station changes, the snow-data counts
  nice_days_by_metro.csv    every metro: before, the old rule on the new
                            download, after, the change, the station

    PYTHONPATH=. .venv/bin/python atlas/results/phase4e/nice_days_measure.py \\
        <before_build> <after_build> <old_station_csv> <old_rule_on_refetch_csv>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def dist(v: pd.Series) -> dict:
    v = v.dropna()
    q = v.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
    return {"n": int(len(v)), "min": round(float(v.min()), 1), "p10": round(float(q[0.1]), 1),
            "p25": round(float(q[0.25]), 1), "median": round(float(q[0.5]), 1),
            "p75": round(float(q[0.75]), 1), "p90": round(float(q[0.9]), 1),
            "max": round(float(v.max()), 1), "mean": round(float(v.mean()), 1)}


def main(before_dir: str, after_dir: str, old_csv: str, old_rule_new_data_csv: str) -> None:
    from atlas.model.loader import load_build
    from atlas.pipeline.fetch import RESULTS
    from atlas.pipeline.registry.loader import load_registry
    b = load_build(Path(before_dir), allow_model_mismatch=True)
    a = load_build(Path(after_dir))
    assert b.metro_levels == a.metro_levels
    st_old = pd.read_csv(old_csv, dtype={"cbsa": str}).set_index("cbsa")
    st_new = pd.read_csv(RESULTS / "phase2d" / "pleasant_days_ghcn.csv", dtype={"cbsa": str}).set_index("cbsa")
    old_new_data = pd.read_csv(old_rule_new_data_csv, dtype={"cbsa": str}).set_index("cbsa")
    df = pd.DataFrame({
        "cbsa": a.metro_levels,
        "metro": a.display_names,
        "ranked": a.ranked_set,
        "before": b.static["pleasant_days"],
        "after": a.static["pleasant_days"],
    }).set_index("cbsa")
    df["old_rule_refetched"] = old_new_data["pleasant_days"].reindex(df.index)
    df["change"] = df["after"] - df["before"]
    df["revision_part"] = df["old_rule_refetched"] - df["before"]
    df["rule_part"] = df["after"] - df["old_rule_refetched"]
    df["station_before"] = st_old["station"].reindex(df.index)
    df["station_after"] = st_new["station"].reindex(df.index)
    df["removed_by_snow"] = (st_new["pleasant_days_no_snow_rule"] - st_new["pleasant_days"]).reindex(df.index)
    # the served values are the station table's, to the build's precision
    assert np.allclose(df["after"].dropna(), st_new["pleasant_days"].reindex(df.index).dropna(), atol=1e-3)

    def rows(d: pd.DataFrame) -> list[dict]:
        return [{"metro": r.metro, "cbsa": i, "ranked": bool(r.ranked),
                 "before": round(float(r.before), 1), "after": round(float(r.after), 1),
                 "change": round(float(r.change), 1)} for i, r in d.iterrows()]

    fin = df.dropna(subset=["before", "after"])
    rk = fin[fin["ranked"]]
    out = {
        "before": {"build": b.manifest["data_version"], "model_version": b.manifest["model_version"],
                   "rule": "a high between 55 and 85°F, a low of at least 40°F, at most 0.1 in of rain"},
        "after": {"build": a.manifest["data_version"], "model_version": a.manifest["model_version"],
                  "rule": load_registry().pleasant_day},
        "distribution": {
            "all_metros": {"before": dist(fin["before"]), "after": dist(fin["after"])},
            "ranked_set": {"before": dist(rk["before"]), "after": dist(rk["after"])},
            "change_all_metros": dist(fin["change"]),
            "metros_up": int((fin["change"] > 0.05).sum()),
            "metros_down": int((fin["change"] < -0.05).sum()),
        },
        "biggest_drops": rows(fin.sort_values("change").head(10)),
        "biggest_rises": rows(fin.sort_values("change", ascending=False).head(10)),
        "top10_new_rule_ranked": rows(rk.sort_values("after", ascending=False).head(10)),
        "bottom10_new_rule_ranked": rows(rk.sort_values("after").head(10)),
        "top10_new_rule_all": rows(fin.sort_values("after", ascending=False).head(10)),
        "bottom10_new_rule_all": rows(fin.sort_values("after").head(10)),
        "rank_order_spearman_all": round(float(fin["before"].rank().corr(fin["after"].rank())), 3),
        "no_qualifying_station": {
            "before": sorted(df.index[df["before"].isna()]),
            "after": sorted(df.index[df["after"].isna()]),
        },
        "station_changes": [{"cbsa": i, "metro": r.metro, "before": r.station_before,
                             "after": r.station_after}
                            for i, r in df[df["station_before"].fillna("") != df["station_after"].fillna("")].iterrows()],
        "noaa_revisions": {
            "what": "the m4.1.1 rule re-run on the re-fetched station files, against the values served; "
                    "separates NOAA's revisions to the 1991-2020 record since the 2026-09-17 download "
                    "from the rule change",
            "metros_moved_more_than_0_05_days": int((df["revision_part"].abs() > 0.05).sum()),
            "max_abs_days": round(float(df["revision_part"].abs().max()), 2),
            "median_abs_days": round(float(df["revision_part"].abs().median()), 3),
        },
        "snow": json.loads((RESULTS / "phase2d" / "pleasant_days_report.json").read_text()).get("snow"),
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out["no_qualifying_station"]["unchanged"] = (out["no_qualifying_station"]["before"]
                                                 == out["no_qualifying_station"]["after"])
    (HERE / "nice_days.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    df.round(3).to_csv(HERE / "nice_days_by_metro.csv")
    print(json.dumps({k: out[k] for k in ("distribution", "no_qualifying_station", "noaa_revisions", "snow")},
                     indent=1, ensure_ascii=False))
    print(f"-> {HERE / 'nice_days.json'}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
