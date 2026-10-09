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

After Phase 4c (Nathan's calls, 2026-09-29: "keep all photos except the
Waco, Texas and Savannah ones; find replacements for them"):

  * the review's `restored` list holds the fifteen removals he kept: each
    goes back as it was — its file returns from the Trash (or is fetched
    again from the recorded rendition), checked against the manifest's
    sha256; its manifest row reads "ok" again; its render entry is rebuilt
    by the city_images functions from the recorded row;
  * the `replaced` list names, per page, the Commons file that replaces a
    photograph (Waco's collage stays refused; Savannah's Tarangire
    photograph was the wrong place): the old file leaves for the Trash, the
    named file is cleared and fetched through city_images (the same licence
    rule, Wikimedia's own rendition), and city_images.main() sources that
    named file on any re-run (pinned_files).

    python -m atlas.pipeline.build.photo_review
"""
from __future__ import annotations

import hashlib
import json
import sys
import shutil
import time
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
# stat photographs scale into their box, the hero crops a band. After the
# Phase 5 report (Nathan, 2026-10-08) every city photograph is cropped —
# the home page's cards and the city page's band: public domain, CC0, CC BY
# and CC BY-SA each permit an adaptation (the credit says "cropped" and
# names the licence; a cropped BY-SA photograph stays BY-SA), and a
# photograph from elsewhere is used by the permission Nathan arranges.
CROPPED = {"city": True, "stat": False, "hero": True}


def refused_files() -> dict[str, str]:
    """Commons file title -> refusal reason, for every photograph the
    review removed or replaced (city_images.source_one reads this on a
    re-run)."""
    if not REVIEW.exists():
        return {}
    rev = json.loads(REVIEW.read_text())
    out = {r["file_title"]: f"refused_review:{r['category']}" for r in rev["removed"]}
    for r in rev.get("replaced", []):
        out[r["was"]] = f"replaced_review:{r['category']}"
    # Phase 4e: candidates the review refused before they ever shipped
    for r in rev.get("phase4e_stat_pages", {}).get("refused", []):
        out[r["file_title"]] = f"refused_review:{r['category']}"
    return out


def pinned_files() -> dict[tuple[str, str], str]:
    """(page, key) -> the Commons file the review names in place of a
    replaced photograph; city_images sources exactly that file."""
    if not REVIEW.exists():
        return {}
    rev = json.loads(REVIEW.read_text())
    # Phase 4e: a stat page none of whose subjects passes takes a named file
    named = rev.get("replaced", []) + rev.get("phase4e_stat_pages", {}).get("pinned", [])
    return {(r["page"], r["key"]): r["file_title"] for r in named}


def pinned_alts() -> dict[tuple[str, str], str]:
    """(page, key) -> the alt text the review gives a replacement whose
    Commons description cannot serve (Savannah's is only in Italian)."""
    if not REVIEW.exists():
        return {}
    rev = json.loads(REVIEW.read_text())
    named = rev.get("replaced", []) + rev.get("phase4e_stat_pages", {}).get("pinned", [])
    # after the Phase 5 report: a kept photograph's alt text, rewritten
    named += rev.get("alt_overrides", [])
    return {(r["page"], r["key"]): r["alt"] for r in named if r.get("alt")}


def external_files() -> dict[tuple[str, str], dict]:
    """(page, key) -> a photograph the review takes from outside Wikimedia
    Commons (Nathan's everyday prices pick, 2026-10-07): its credit, its
    alt text and its exact bytes (sha256), with the evidence for its
    licence beside them in the review record. city_images sources it from
    the record, never from the Commons API."""
    if not REVIEW.exists():
        return {}
    rev = json.loads(REVIEW.read_text())
    return {(r["page"], r["key"]): r for r in rev.get("external_files", [])}


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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _none(v):
    """A manifest cell as a render value: pandas reads a blank as NaN."""
    return None if v is None or (isinstance(v, float) and v != v) else v


def _surface(r: dict, city: dict, stat: dict, city_csv: pd.DataFrame, stat_csv: pd.DataFrame):
    """(render dict, manifest, row selector, folder, trash subfolder,
    cropped) for a review entry's page."""
    if r["page"] == "city":
        return (city, city_csv, city_csv["slug"] == r["key"], WEB / "public" / "cities",
                "cities", CROPPED["city"])
    return (stat, stat_csv, stat_csv["stat"] == r["key"], WEB / "public" / "stats",
            "stats", CROPPED["stat"])


def _alt(file_title: str) -> str | None:
    """The alt text city_images gives a file: its Commons description, to
    160 characters (from the cached imageinfo)."""
    from atlas.pipeline.build import city_images as CI
    ii = CI.imageinfo(file_title.split("File:", 1)[-1]) or {}
    cleared, _ = CI.clear_licence(ii) if ii else (None, "")
    desc = (cleared or {}).get("description") or ""
    return desc[:160].rstrip() or None


def _restore(r: dict, city: dict, stat: dict, city_csv: pd.DataFrame,
             stat_csv: pd.DataFrame) -> dict:
    """A removal Nathan kept (after Phase 4c): the recorded file back —
    from the Trash when it is there, else Wikimedia's recorded rendition,
    either way matching the manifest's sha256 — the row "ok" again, and
    the render entry rebuilt from the row as city_images composes it."""
    render, csv, sel, folder, sub, cropped = _surface(r, city, stat, city_csv, stat_csv)
    row = csv.loc[sel].iloc[0].to_dict()
    assert row["file_title"] == r["file_title"], f"{r['key']}: the manifest row names another file"
    dest = folder / row["file"]
    trashed = TRASH / sub / row["file"]
    if dest.exists() and _sha(dest) == row["sha256"]:
        how = "in place"
    elif trashed.exists() and _sha(trashed) == row["sha256"]:
        shutil.move(str(trashed), str(dest))
        how = "from the Trash"
    else:
        from atlas.pipeline.build import city_images as CI
        CI.download(row["image_url"], dest)
        how = "fetched again"
    assert dest.exists() and _sha(dest) == row["sha256"], f"{dest.name}: not the recorded file"
    csv.loc[sel, "status"] = "ok"
    render[r["key"]] = {"file": row["file"], "alt": _alt(row["file_title"]),
                        "author": _none(row["author"]), "license": row["license"],
                        "license_url": _none(row["license_url"]),
                        "source_url": row["source_url"],
                        "title": title_of(row["source_url"]), "cropped": cropped}
    return {"key": r["key"], "file": how}


def _replace(r: dict, city: dict, stat: dict, city_csv: pd.DataFrame,
             stat_csv: pd.DataFrame, retrieved: str) -> dict:
    """The Commons file the review names in place of a photograph: the old
    file to the Trash, the named one cleared and fetched as city_images
    sources any photograph (Wikimedia's own rendition), its manifest row
    and render entry rewritten. Re-running changes nothing once applied."""
    from atlas.pipeline.build import city_images as CI
    render, csv, sel, folder, sub, cropped = _surface(r, city, stat, city_csv, stat_csv)
    row = csv.loc[sel].iloc[0].to_dict()
    if (row.get("file_title") == r["file_title"] and row.get("status") == "ok"
            and (folder / str(row["file"])).exists()
            and _sha(folder / str(row["file"])) == row["sha256"]):
        how = "in place"
    else:
        rec, reason = CI.source_file(r["file_title"])
        assert rec, f"{r['key']}: {r['file_title']} does not clear the licence rule: {reason}"
        _to_trash(folder / str(_none(row.get("file")) or f"{r['key']}.jpg"), "replaced")
        ext = {"image/png": ".png", "image/webp": ".webp"}.get(rec["mime"], ".jpg")
        dest = folder / f"{r['key']}{ext}"
        sha = CI.download(rec["image_url"], dest)
        assert sha, f"{r['key']}: the download of {r['file_title']} failed"
        for k, v in {"status": "ok", "page_title": None, "file_title": rec["file_title"],
                     "source_url": rec["source_url"], "image_url": rec["image_url"],
                     "author": rec["author"], "license": rec["license"],
                     "license_url": rec["license_url"], "retrieved": retrieved,
                     "sha256": sha, "file": dest.name}.items():
            csv[k] = csv[k].astype(object)
            csv.loc[sel, k] = v
        row = csv.loc[sel].iloc[0].to_dict()
        how = "replaced"
    render[r["key"]] = {"file": row["file"], "alt": r.get("alt") or _alt(row["file_title"]),
                        "author": _none(row["author"]), "license": row["license"],
                        "license_url": _none(row["license_url"]),
                        "source_url": row["source_url"],
                        "title": title_of(row["source_url"]), "cropped": cropped}
    return {"key": r["key"], "file": how, "file_title": row["file_title"]}


def _external(r: dict, city: dict, stat: dict, city_csv: pd.DataFrame,
              stat_csv: pd.DataFrame, retrieved: str) -> dict:
    """After the Phase 5 report: a city photograph from outside Commons, as
    the review records it (its credit, alt text and exact bytes): the old
    file to the Trash unless it already is these bytes, the recorded file
    fetched and checked by city_images.source_external, the manifest row
    and render entry rewritten. Re-running changes nothing once applied."""
    from atlas.pipeline.build import city_images as CI
    render, csv, sel, folder, sub, cropped = _surface(r, city, stat, city_csv, stat_csv)
    row = csv.loc[sel].iloc[0].to_dict()
    dest = folder / f"{r['key']}{CI.external_suffix(r['image_url'])}"
    old = folder / str(_none(row.get("file")) or f"{r['key']}.jpg")
    if old.exists() and not (old == dest and _sha(old) == r["sha256"]):
        _to_trash(old, "replaced")
    new_row, entry = CI.source_external(r["key"], r, retrieved, page=r["page"])
    assert entry, f"{r['key']}: the pinned photograph is unavailable ({new_row['status']})"
    for k, v in new_row.items():
        if k in csv.columns:
            csv[k] = csv[k].astype(object)
            csv.loc[sel, k] = v
    render[r["key"]] = entry
    return {"key": r["key"], "file": entry["file"], "source": r["source_url"]}


DISPLAY_FIELDS = ("place", "place_caption", "focus")


def apply_display(rev: dict, city: dict, stat: dict) -> list[str]:
    """Phase 6: how a photograph is shown, from the review's
    `photo_display` entries — `place`, the place it shows when that is
    elsewhere in its metro (F29: the city band's caption, "Daytona Beach,
    in the Deltona metro area"), `place_caption`, a caption that is not
    that template ("Vineyards outside Santa Maria"), and `focus`, its focal
    point as an object-position value (F30: the card, the band and the
    link-preview crop; "50% 35%" when absent). A photograph's entries are
    merged, and together they set every display field it has, so removing
    one from the review removes it from the page. Offline and idempotent."""
    merged: dict[tuple[str, str], dict] = {}
    for r in rev.get("photo_display", []):
        fields = merged.setdefault((r["page"], r["key"]), {})
        fields.update({k: r[k] for k in DISPLAY_FIELDS if r.get(k)})
    done = []
    for (page, key), fields in merged.items():
        target = city if page == "city" else stat
        entry = target.get(key)
        if entry is None:
            continue
        for k in DISPLAY_FIELDS:
            if k in fields:
                entry[k] = fields[k]
            else:
                entry.pop(k, None)
        done.append(key)
    return done


def display_only() -> dict:
    """The display fields alone, on the render manifests as they are
    (`python -m atlas.pipeline.build.photo_review display`): no file moves,
    no network."""
    rev = _read(REVIEW)
    city_path = WEB / "src" / "data" / "city-images.json"
    stat_path = WEB / "src" / "data" / "stat-images.json"
    city, stat = _read(city_path), _read(stat_path)
    done = apply_display(rev, city, stat)
    _write_render(city_path, city)
    _write_render(stat_path, stat)
    return {"display_entries_applied": done}


def apply() -> dict:
    rev = _read(REVIEW)
    city_path = WEB / "src" / "data" / "city-images.json"
    stat_path = WEB / "src" / "data" / "stat-images.json"
    hero_path = WEB / "src" / "data" / "hero.json"
    city, stat, hero = _read(city_path), _read(stat_path), _read(hero_path)
    city_csv = pd.read_csv(P2E / "city_images.csv", dtype={"cbsa": str})
    stat_csv = pd.read_csv(P2E / "stat_images.csv")
    moved = []
    # after the Phase 5 report: a city page that takes a photograph from
    # outside Commons no longer takes an older removal, restoration or
    # replacement (seven of the restored photographs gave way to card photos)
    outside_pages = {(r["page"], r["key"]) for r in rev.get("external_files", [])
                     if r["page"] == "city"}
    # a replaced photograph's page takes the named file, so a removal on
    # the same page (Waco's collage) no longer touches it
    replaced_pages = {(r["page"], r["key"]) for r in rev.get("replaced", [])}
    for r in rev["removed"]:
        if (r["page"], r["key"]) in replaced_pages | outside_pages:
            continue
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
    # after Phase 4c (Nathan's calls): the removals he kept, then the
    # replacements the review names
    restored = [_restore(r, city, stat, city_csv, stat_csv) for r in rev.get("restored", [])
                if (r["page"], r["key"]) not in outside_pages]
    retrieved = time.strftime("%Y-%m-%d")
    replaced = [_replace(r, city, stat, city_csv, stat_csv, retrieved)
                for r in rev.get("replaced", []) if (r["page"], r["key"]) not in outside_pages]
    # after the Phase 5 report: city photographs from outside Commons, and
    # kept photographs' rewritten alt texts
    outside = [_external(r, city, stat, city_csv, stat_csv, retrieved)
               for r in rev.get("external_files", []) if r["page"] == "city"]
    for r in rev.get("alt_overrides", []):
        target = city if r["page"] == "city" else stat
        if r["key"] in target:
            target[r["key"]]["alt"] = r["alt"]
    apply_display(rev, city, stat)
    external = external_files()
    for page, render in (("city", city), ("stat", stat)):
        for key, v in render.items():
            # a photograph from outside Commons keeps its recorded title
            if (page, key) not in external:
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
            "restored": restored, "replaced": replaced, "outside_commons": outside,
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
    if sys.argv[1:2] == ["display"]:
        print(json.dumps(display_only(), indent=1))
        return
    out = apply()
    rec = credits()
    CREDITS.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=1))
    print(f"credits: {rec['photos_in_use']} photographs in use; "
          f"{rec['cc_before_4_0']['count']} under CC licences before 4.0 -> {CREDITS}")


if __name__ == "__main__":
    main()
