"""Phase 2g gate 3: trace five cities' rent figures cell by cell.

An INDEPENDENT recomputation — raw HUD county rows joined to the
delineation, weighted by the same ACS renter-household counts, in code
that shares nothing with features.py beyond the adapters — compared to
the value the served build carries and the display string the API
formats from it. One traced metro spans multiple FMR areas (Boston, New
England town rows included) so the join's hardest path is in the trace.

    python -m atlas.pipeline.build.rent_trace <build_dir> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from atlas.model.explain import format_value
from atlas.model.loader import load_build
from atlas.pipeline.adapters.census import (ACS_DATASET, AcsSummaryAdapter,
                                            DelineationAdapter)
from atlas.pipeline.adapters.hud_fmr50 import NEW_ENGLAND, HudFmr50Adapter
from atlas.pipeline.build.features import NE_STATE_FIPS
from atlas.pipeline.fetch import api_get

TRACE = {
    "39340": "Provo-Orem, UT (single FMR area)",
    "12420": "Austin-Round Rock, TX (the metro that started this)",
    "10180": "Abilene, TX (three counties, one FMR area)",
    "35620": "New York-Newark-Jersey City, NY-NJ (multiple HMFAs)",
    "14460": "Boston-Cambridge-Newton, MA-NH (multiple HMFAs, town rows)",
}


def main(build_dir: str, out_path: str) -> None:
    build = load_build(build_dir)
    hud = HudFmr50Adapter()
    hrows = hud.normalize(hud.fetch())
    d = DelineationAdapter()
    dd = d.normalize(d.fetch())

    r_rows = AcsSummaryAdapter("B25003", "county").fetch().meta["rows"]
    rframe = pd.DataFrame(r_rows[1:], columns=r_rows[0])
    county_w = {r["state"] + r["county"]: float(r["B25003_003E"])
                for _, r in rframe.iterrows()}
    cousub_w: dict[tuple[str, str], float] = {}
    cousub_name_w: dict[tuple[str, str], float] = {}
    for st in sorted(NE_STATE_FIPS.values()):
        rows_st = api_get(ACS_DATASET, {"get": "NAME,B25003_003E",
                                        "for": "county subdivision:*",
                                        "in": f"state:{st}"})
        f = pd.DataFrame(rows_st[1:], columns=rows_st[0])
        for _, r in f.iterrows():
            c5 = r["state"] + r["county"]
            cousub_w[(c5, r["county subdivision"])] = float(r["B25003_003E"])
            base = r["NAME"].split(",")[0].lower()
            for suf in (" town city", " city", " town", " plantation"):
                base = base.removesuffix(suf)
            cousub_name_w[(c5, base)] = float(r["B25003_003E"])

    out = {"build": build.manifest["data_version"], "cities": []}
    for cbsa, label in TRACE.items():
        counties = sorted(dd.loc[dd["cbsa"] == cbsa, "county5"])
        rows = hrows[hrows["county5"].isin(counties)]
        num = den = 0.0
        pieces = []
        for _, r in rows.iterrows():
            if r["county_sub_code"] == "99999":
                w = county_w[r["county5"]]
            else:
                key = (r["county5"], r["county_sub_code"])
                w = cousub_w.get(key)
                if w is None:
                    base = str(r["town_name"]).lower()
                    for suf in (" town city", " city", " town", " plantation"):
                        base = base.removesuffix(suf)
                    w = cousub_name_w.get((r["county5"], base), 0.0)
            num += float(r["rent_1br"]) * w
            den += w
            pieces.append({"county5": r["county5"],
                           "sub": r["county_sub_code"],
                           "rent_1br": float(r["rent_1br"]),
                           "renter_households": w})
        traced = num / den
        i = build.metro_levels.index(cbsa)
        served = float(build.static["rent_1br"][i])
        display = format_value(served, build.legend["rent_1br"])
        assert abs(traced - served) < 1e-6, (cbsa, traced, served)
        out["cities"].append({
            "cbsa": cbsa, "label": label,
            "hud_rows": len(rows),
            "fmr_areas": int(rows["hud_area_code"].nunique()),
            "traced_weighted_mean": round(traced, 4),
            "served_value": round(served, 4),
            "api_display": display,
            "rows_summarised": pieces if len(pieces) <= 6 else
                f"{len(pieces)} rows (town-level; full detail in the "
                f"HUD file)",
        })
        ne = rows["state_alpha"].isin(NEW_ENGLAND).any()
        print(f"{label}: {len(rows)} rows, {rows['hud_area_code'].nunique()} "
              f"FMR area(s){' incl. NE towns' if ne else ''} -> "
              f"${display} (traced == served)")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
