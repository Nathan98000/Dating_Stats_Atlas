"""Phase 4 Stage 3: the photo review, applied (ADR 0012, Nathan's decisions).

Every city photograph, stat-page photograph and the hero was reviewed on
contact sheets (the record: results/phase4/photo_review.json). A
photograph is removed when an identifiable person is its subject, when a
recent US sculpture or mural is a subject of it, or when a government or
agency logo, emblem or seal is prominent in it. A removed photograph
falls back to no photo -- the existing "no file, no photo" rule:

  * its entry leaves web/src/data/city-images.json (or stat-images.json),
    so no page renders it or credits it;
  * its manifest row in results/phase2e/*_images.csv keeps its record and
    reads status "refused_review:<category>";
  * the file moves from web/public to the macOS Trash (not deleted);
  * city_images.source_one refuses its Commons file on any re-run.

Every photograph still in use gains its credit record -- `title` (the
Commons file title) and `cropped` (whether the layout crops it, which
makes it an adaptation: the city and stat pages scale with object-contain,
the hero crops a band) -- beside the author, source link, licence and
licence-version link it already carried, and results/phase4/
photo_credits.json lists them all.

    python -m atlas.pipeline.build.photo_review
"""
from __future__ import annotations

import json
import shutil
import urllib.parse
from pathlib import Path

import pandas as pd

from atlas.pipeline.fetch import RESULTS

REVIEW = RESULTS / "phase4" / "photo_review.json"
CREDITS = RESULTS / "phase4" / "photo_credits.json"
WEB = RESULTS.parents[0] / "web"
P2E = RESULTS / "phase2e"
TRASH = Path.home() / ".Trash" / "Dating_Stats_Atlas_phase4_photo_review"

# how each surface lays its photograph out (the components' classes):
# city and stat photographs scale into their box, the hero crops a band
CROPPED = {"city": False, "stat": False, "hero": True}


def refused_files() -> dict[str, str]:
    """Commons file title -> refusal reason, for every photograph the
    review removed (city_images.source_one reads this on a re-run)."""
    if not REVIEW.exists():
        return {}
    rev = json.loads(REVIEW.read_text())
    return {r["file_title"]: f"refused_review:{r['category']}" for r in rev["removed"]}


def title_of(source_url: str) -> str:
    """The Commons file title, as a credit's title: the file name from the
    description page, without "File:" and the extension."""
    name = urllib.parse.unquote(source_url.rsplit("/", 1)[-1])
    name = name.split("File:", 1)[-1].replace("_", " ")
    return name.rsplit(".", 1)[0] if "." in name else name


def _read(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_render(path: Path, data: dict) -> None:
    # the format city_images.py writes
    path.write_text(json.dumps(data, indent=0, ensure_ascii=False, sort_keys=True) + "\n")


def _to_trash(src: Path, sub: str) -> str | None:
    if not src.exists():
        return None
    dest = TRASH / sub / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return str(dest)


def apply() -> dict:
    rev = _read(REVIEW)
    city_path = WEB / "src" / "data" / "city-images.json"
    stat_path = WEB / "src" / "data" / "stat-images.json"
    hero_path = WEB / "src" / "data" / "hero.json"
    city, stat, hero = _read(city_path), _read(stat_path), _read(hero_path)
    city_csv = pd.read_csv(P2E / "city_images.csv", dtype={"cbsa": str})
    stat_csv = pd.read_csv(P2E / "stat_images.csv")
    moved = []
    for r in rev["removed"]:
        status = f"refused_review:{r['category']}"
        if r["page"] == "city":
            entry = city.pop(r["key"], None)
            city_csv.loc[city_csv["slug"] == r["key"], "status"] = status
            f = (entry or {}).get("file") or f"{r['key']}.jpg"
            moved.append(_to_trash(WEB / "public" / "cities" / f, "cities"))
        else:
            entry = stat.pop(r["key"], None)
            stat_csv.loc[stat_csv["stat"] == r["key"], "status"] = status
            f = (entry or {}).get("file") or f"{r['key']}.jpg"
            moved.append(_to_trash(WEB / "public" / "stats" / f, "stats"))
    for s in rev.get("stray_files", []):
        moved.append(_to_trash(RESULTS.parents[0] / s["file"], "stray"))
    for page, render in (("city", city), ("stat", stat)):
        for v in render.values():
            v["title"] = title_of(v["source_url"])
            v["cropped"] = CROPPED[page]
    hero["title"] = title_of(hero["source_url"])
    hero["cropped"] = CROPPED["hero"]
    _write_render(city_path, city)
    _write_render(stat_path, stat)
    hero_path.write_text(json.dumps(hero, indent=1, ensure_ascii=False) + "\n")
    city_csv.to_csv(P2E / "city_images.csv", index=False)
    stat_csv.to_csv(P2E / "stat_images.csv", index=False)
    return {"removed": len(rev["removed"]), "moved_to_trash": [m for m in moved if m],
            "city_photos": len(city), "stat_photos": len(stat)}


def credits() -> dict:
    """Every photograph in use, with its full credit record."""
    city = _read(WEB / "src" / "data" / "city-images.json")
    stat = _read(WEB / "src" / "data" / "stat-images.json")
    hero = _read(WEB / "src" / "data" / "hero.json")
    rows = []
    for page, render in (("city", city), ("stat", stat)):
        for key, v in sorted(render.items()):
            rows.append({"page": page, "key": key, "title": v["title"],
                         "author": v["author"], "source_url": v["source_url"],
                         "license": v["license"], "license_url": v["license_url"],
                         "cropped": v["cropped"]})
    rows.append({"page": "hero", "key": "hero", "title": hero["title"],
                 "author": hero["author"], "source_url": hero["source_url"],
                 "license": hero["license"], "license_url": hero["license_url"],
                 "cropped": hero["cropped"]})
    by_licence: dict[str, int] = {}
    for r in rows:
        by_licence[r["license"]] = by_licence.get(r["license"], 0) + 1
    # pre-4.0 Creative Commons versions: for Nathan to confirm that one
    # central credits page suits them (4.0 expressly allows a linked page)
    pre4 = [r for r in rows if r["license"].upper().startswith("CC BY")
            and any(v in r["license"] for v in (" 1.0", " 2.0", " 2.5", " 3.0"))]
    return {"photos_in_use": len(rows), "by_licence": dict(sorted(by_licence.items())),
            "cropped": [r["key"] for r in rows if r["cropped"]],
            "cc_before_4_0": {"count": len(pre4),
                              "by_licence": {l: sum(1 for r in pre4 if r["license"] == l)
                                             for l in sorted({r["license"] for r in pre4})},
                              "photos": [{"page": r["page"], "key": r["key"],
                                          "license": r["license"]} for r in pre4]},
            "photos": rows}


def main() -> None:
    out = apply()
    rec = credits()
    CREDITS.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=1))
    print(f"credits: {rec['photos_in_use']} photographs in use; "
          f"{rec['cc_before_4_0']['count']} under CC licences before 4.0 -> {CREDITS}")


if __name__ == "__main__":
    main()
