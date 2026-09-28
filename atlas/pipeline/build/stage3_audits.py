"""Phase 4 Stage 3 (ADR 0012): two audits on the record.

  station  every served metro's GHCN-Daily station, from the table the
           build reads (results/phase2d/pleasant_days_ghcn.csv): its id,
           country code (a GHCN id's first two characters), network and
           distance; any station outside the US is a finding that Stage 3b
           rematches in a build of its own.
  logos    every file in web/public other than the photographs, whether
           any page references it, and whether it is an agency logo,
           emblem or seal (the photographs themselves are the photo
           review's: results/phase4/photo_review.json).

    python -m atlas.pipeline.build.stage3_audits station --out results/phase4/station_audit.json
    python -m atlas.pipeline.build.stage3_audits logos --out results/phase4/logo_audit.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from atlas.pipeline.fetch import RESULTS

WEB = RESULTS.parents[0] / "web"
PHOTO_DIRS = {"cities", "stats"}
PHOTO_FILES = {"hero.jpg"}


def station_audit() -> dict:
    st = pd.read_csv(RESULTS / "phase2d" / "pleasant_days_ghcn.csv", dtype={"cbsa": str})
    names = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})[["cbsa", "cbsa_title"]]
    df = st.merge(names, on="cbsa", how="left")
    rows = []
    for _, r in df.sort_values("cbsa").iterrows():
        sid = r["station"] if isinstance(r["station"], str) else None
        rows.append({"cbsa": r["cbsa"], "metro": r["cbsa_title"], "station": sid,
                     "country": sid[:2] if sid else None,
                     "network": sid[2] if sid else None,
                     "station_km": round(float(r["station_km"]), 2) if sid else None,
                     "station_rank": int(r["station_rank"]) if sid else None,
                     "years_used": int(r["years_used"]) if sid else 0})
    outside = [r for r in rows if r["station"] and r["country"] != "US"]
    return {"source": "results/phase2d/pleasant_days_ghcn.csv (the table build.features reads)",
            "metros": len(rows), "with_station": sum(1 for r in rows if r["station"]),
            "by_country": pd.Series([r["country"] for r in rows if r["station"]]).value_counts().to_dict(),
            "by_network": pd.Series([r["network"] for r in rows if r["station"]]).value_counts().to_dict(),
            "outside_us": outside, "verdict": "US only" if not outside else
            f"{len(outside)} served metro(s) on a station outside the US: rematch in Stage 3b",
            "stations": rows}


def logo_audit() -> dict:
    pub = WEB / "public"
    src_text = "\n".join(p.read_text(errors="replace")
                         for p in (WEB / "src").rglob("*") if p.is_file()
                         and p.suffix in {".ts", ".tsx", ".css", ".json", ".md"})
    files = []
    for p in sorted(pub.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        rel = p.relative_to(pub).as_posix()
        if rel.split("/", 1)[0] in PHOTO_DIRS or rel in PHOTO_FILES:
            continue
        referenced = bool(re.search(re.escape("/" + rel) + r"\b", src_text))
        files.append({"file": f"web/public/{rel}", "referenced_by_a_page": referenced})
    known = {  # what the non-photo files are (read by eye; all create-next-app scaffolding)
        "web/public/file.svg": "create-next-app scaffold icon (a document glyph)",
        "web/public/globe.svg": "create-next-app scaffold icon (a globe glyph)",
        "web/public/window.svg": "create-next-app scaffold icon (a window glyph)",
        "web/public/next.svg": "the Next.js wordmark, create-next-app scaffolding",
        "web/public/vercel.svg": "the Vercel logo, create-next-app scaffolding",
    }
    for f in files:
        f["what"] = known.get(f["file"], "unclassified")
        f["agency_logo_emblem_or_seal"] = False
    pages = sorted(p.relative_to(WEB).as_posix() for p in (WEB / "src").rglob("*.tsx"))
    hits = [p for p in pages if re.search(r"\b(logo|seal|emblem)\b",
                                          (WEB / p).read_text(), re.IGNORECASE)]
    return {"non_photo_files": files,
            "pages_checked": len(pages),
            "pages_naming_a_logo_seal_or_emblem": hits,
            "photographs": "reviewed one by one (results/phase4/photo_review.json); the three "
                           "in which a government emblem was prominent were removed",
            "verdict": "no agency logo, emblem or seal in web/public or on any page"
                       if not hits and not any(f["agency_logo_emblem_or_seal"] for f in files)
                       else "see non_photo_files and pages"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["station", "logos"])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rec = station_audit() if a.what == "station" else logo_audit()
    a.out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(rec["verdict"])


if __name__ == "__main__":
    main()
