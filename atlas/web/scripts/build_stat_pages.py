"""Generate src/data/stat-pages.json (Phase 2d item 9): one page per
STATIC statistic, ranking the 193 ranked-set cities — the same universe
the search list returns — on that one measure.

Cell-for-cell agreement with the city pages is by construction: values,
display strings and bands come from the SAME build artifact through the
SAME model code (Build.static, format_value/format_pop, the engine's
_band_of), and the build id is stamped so a mismatch is detectable. No
API call and no recomputation at request time; the JSON is the page.

    python scripts/build_stat_pages.py [build_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
REPO = WEB.parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from atlas.model.explain import format_pop, format_value  # noqa: E402
from atlas.model.loader import load_build  # noqa: E402
from atlas.model.scoring import _band_of  # noqa: E402

DEFAULT_BUILD = REPO / "atlas" / "data" / "builds" / "2c8d7285c720"


def main() -> None:
    build_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BUILD
    build = load_build(build_dir)
    m = build.manifest
    pages: dict[str, dict] = {}
    for fid in m["stat_pages"]:
        le = build.legend[fid]
        vals = build.static[fid]
        rows = []
        for i in np.where(build.ranked_set)[0]:
            v = float(vals[i])
            if np.isnan(v):
                continue
            if fid == "who_lives_here":
                display = format_pop(v)
                unit_line = le["unit_template"].format(
                    adults=format_pop(float(build.pool_pop[i])))
            else:
                display = format_value(v, le)
                unit_line = le.get("unit", "")
            band = _band_of(build, fid, int(i))
            rows.append({
                "slug": build.slugs[i],
                "name": build.display_names[i],
                "_v": v,
                "display": display,
                "unit_line": unit_line,
                "band": ({"label": band["label"], "tone": band["tone"],
                          "key": band["key"]} if band else None),
            })
        # order by the measure itself; direction decides which end leads
        # (cheap rent first, most venues first) — never by any score.
        # Positions are numbered ONCE in this order; the page's reverse
        # sort shows the same numbers in reverse (item 1).
        reverse = int(le["direction"]) > 0
        rows.sort(key=lambda r: r["_v"], reverse=reverse)
        for pos, r in enumerate(rows):
            r["pos"] = pos + 1
        # the distribution strip (Phase 2e item 6): every ranked city as
        # a tick along the stat's own range, plus formatted end labels —
        # computed here from the same values the rows carry
        finite = sorted(r["_v"] for r in rows)
        lo_v, hi_v = finite[0], finite[-1]
        span = (hi_v - lo_v) or 1.0
        ticks = [round((r["_v"] - lo_v) / span * 100, 2) for r in rows]
        if fid == "who_lives_here":
            axis = [format_pop(lo_v), format_pop(hi_v)]
        else:
            axis = [format_value(lo_v, le), format_value(hi_v, le)]
        for r in rows:
            del r["_v"]

        missing = int(build.ranked_set.sum()) - len(rows)
        pages[fid] = {
            # the page heading says "Cities by {title}" — population's
            # entry carries a registry stat_page_name because "cities by
            # who lives here" is not a sentence
            "title": le.get("stat_page_name") or le["display_name"],
            "unit": le.get("unit", ""),
            "definition": le["definition"],
            "rows": rows,
            "missing_in_ranked_set": missing,
            # position #1 is the registry-direction-good end; the page's
            # reverse toggle shows the SAME numbers in reverse (item 1)
            "default_is_low_first": not reverse,
            "strip": {"ticks": ticks, "axis": axis},
            # per-page disclosure sentences from the registry (the rent
            # page's rent-stabilisation note, item 9.4)
            "note": {"median_gross_rent": m["strings"].get("rent_page_note")}
                    .get(fid),
        }
    out = WEB / "src" / "data" / "stat-pages.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    # the pages are API-free by design (item 9), so the registry strings
    # they render ride along in the JSON
    payload = {"of_build": m["data_version"], "pages": pages,
               "order": list(m["stat_pages"]),
               "strings": {"intro": m["strings"]["stat_page_intro"],
                           "missing": m["strings"]["stat_page_missing"],
                           "sort_low": m["strings"]["stat_sort_low"],
                           "sort_high": m["strings"]["stat_sort_high"],
                           "strip_label": m["strings"]["stat_strip_label"]}}
    out.write_text(json.dumps(payload, separators=(",", ":"),
                              ensure_ascii=False) + "\n", encoding="utf-8")
    n = len(pages)
    print(f"{out}: {n} stat pages x {len(next(iter(pages.values()))['rows'])} "
          f"cities ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
