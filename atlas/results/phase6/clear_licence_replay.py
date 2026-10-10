"""The clear_licence fix replayed (after the credit audit; Nathan,
2026-10-10): every Commons file the site credits, cleared the old way (the
metadata alone) and the new way (with the file's own page), from the cache
only — the imageinfo the pipeline asked for and the pages the audit read —
with no network call. Where the two differ, and how each compares with the
credit the site shows.

    PYTHONPATH=. .venv/bin/python atlas/results/phase6/clear_licence_replay.py

writes results/phase6/clear_licence_replay.json.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from atlas.pipeline.build import city_images as CI  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC_DATA = ROOT / "atlas" / "web" / "src" / "data"
OUT = HERE / "clear_licence_replay.json"


def cached(url: str, params: dict) -> dict | None:
    p = CI._cache_file(url, params)
    return json.loads(p.read_text()) if p.exists() else None


def no_network(params: dict) -> dict | None:
    return cached(CI.COMMONS_API, params)


def cached_imageinfo(name: str) -> dict | None:
    for n in (name, name.replace("_", " ")):
        d = cached(CI.API, {"action": "query", "titles": f"File:{n}", "prop": "imageinfo",
                            "iiprop": "extmetadata|url|sha1|size|mime",
                            "iiurlwidth": CI.THUMB_WIDTH, "format": "json"})
        for pg in ((d or {}).get("query", {}).get("pages", {}) or {}).values():
            ii = (pg.get("imageinfo") or [None])[0]
            if ii:
                return ii
    return None


def credit(c: dict | None, reason: str) -> dict:
    return ({"license": c["license"], "author": c["author"], "license_url": c["license_url"]}
            if c else {"refused": reason})


def main() -> None:
    CI._commons_json = no_network  # the cache only
    city = json.loads((SRC_DATA / "city-images.json").read_text())
    stat = json.loads((SRC_DATA / "stat-images.json").read_text())
    hero = json.loads((SRC_DATA / "hero.json").read_text())
    rows = ([("city", k, v) for k, v in sorted(city.items())] +
            [("stat", k, v) for k, v in sorted(stat.items())] + [("hero", "hero", hero)])
    replayed, skipped, changed, differs = 0, [], [], []
    for page_kind, key, v in rows:
        u = urllib.parse.urlparse(v.get("source_url") or "")
        if u.netloc != "commons.wikimedia.org":
            continue
        name = urllib.parse.unquote(u.path.split("/wiki/", 1)[-1]).split("File:", 1)[-1]
        ii = cached_imageinfo(name)
        page = CI.file_page(name)
        if not ii or page is None:
            skipped.append({"page": page_kind, "key": key, "file": f"File:{name}",
                            "missing": "imageinfo" if not ii else "page"})
            continue
        replayed += 1
        old = credit(*CI.clear_licence(ii))
        new = credit(*CI.clear_licence(ii, page=page, uploader=lambda n=name: CI.uploader_of(n)))
        shown = {"license": v.get("license"), "author": v.get("author"),
                 "license_url": v.get("license_url")}
        rec = {"page": page_kind, "key": key, "file": f"File:{name}", "old": old, "new": new,
               "site_shows": shown}
        if new != old:
            changed.append(rec)
        if new.get("license") != shown["license"] or new.get("author") != shown["author"]:
            differs.append(rec)
    out = {
        "date": time.strftime("%Y-%m-%d"),
        "what": ("clear_licence the old way (the metadata alone) and the new way (with the file's "
                 "page), replayed from the cache over every Commons file the site credits"),
        "counts": {"commons_files": replayed + len(skipped), "replayed": replayed,
                   "not_in_the_cache": len(skipped), "changed_by_the_fix": len(changed),
                   "new_answer_differs_from_the_site": len(differs)},
        "changed_by_the_fix": changed,
        "new_answer_differs_from_the_site": differs,
        "not_in_the_cache": skipped,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["counts"], indent=1))


if __name__ == "__main__":
    main()
