"""Phase 2f item 4.1: source the home hero through the SAME pipeline and
licence gate as the city photographs (city_images.py), preferring public
domain / CC0 — the hero renders as a cropped band, and a crop of a
CC-BY-SA image is an adaptation that drags ShareAlike onto the page, so
this script REFUSES any licence that is not PD/CC0 rather than quietly
shipping one (rendering an attributed image uncropped instead is a
deliberate decision for a person to make, not a fallback for a script).

Subject: Burlington's Church Street Marketplace — the HomeV3 art
direction almost verbatim (people on a pedestrian city street, faces
small, city legible, documentary not stock), whose Wikipedia lead image
cleared as public domain in the Phase 2e run; the licence is re-read
LIVE here, never trusted from the old manifest.

Outputs:
  web/public/hero.jpg            gitignored like every shipped photo;
                                 this script re-materialises it
  results/phase2f/hero_image.csv the committed manifest row
  web/src/data/hero.json         the render-side record; its sha256 is
                                 what lets the page attach attribution
                                 ONLY while the file on disk is this
                                 exact file (Nathan's drop-in override
                                 renders, but never wears this credit)

    python -m atlas.pipeline.build.hero_image
"""
from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path

from atlas.pipeline.build.city_images import download, source_one
from atlas.pipeline.fetch import RESULTS

HERO_ARTICLE = "Burlington, Vermont"
STRICT_PD = re.compile(r"^(public domain|pd\b|cc0)", re.IGNORECASE)

P2F = RESULTS / "phase2f"
WEB = RESULTS.parents[0] / "web"


def main() -> None:
    rec, reason = source_one([HERO_ARTICLE])
    assert rec is not None, f"hero source refused: {reason}"
    assert STRICT_PD.match(rec["license"]), (
        f"hero licence {rec['license']!r} is not public domain/CC0 — the "
        f"band crop would be an adaptation carrying its terms; choose "
        f"another subject or decide to ship uncropped")

    dest = WEB / "public" / "hero.jpg"
    if dest.exists():
        dest.unlink()  # this script's job is to materialise the SOURCED hero
    sha = download(rec["image_url"], dest)
    assert sha, f"download failed: {rec['image_url']}"

    retrieved = time.strftime("%Y-%m-%d")
    P2F.mkdir(parents=True, exist_ok=True)
    row = {
        "subject": HERO_ARTICLE,
        "page_title": rec["page_title"],
        "file_title": rec["file_title"],
        "source_url": rec["source_url"],
        "image_url": rec["image_url"],
        "author": rec.get("author") or "",
        "license": rec["license"],
        "license_url": rec.get("license_url") or "",
        "retrieved": retrieved,
        "sha256": sha,
        "file": "hero.jpg",
        "alt": rec.get("description") or "",
    }
    with (P2F / "hero_image.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerow(row)

    hero_json = {
        "file": "hero.jpg",
        "sha256": sha,
        "alt": rec.get("description") or None,
        "author": rec.get("author") or None,
        "license": rec["license"],
        "license_url": rec.get("license_url"),
        "source_url": rec["source_url"],
    }
    out = WEB / "src" / "data" / "hero.json"
    out.write_text(json.dumps(hero_json, indent=1, ensure_ascii=False) + "\n")
    print(f"hero: {rec['file_title']} ({rec['license']}) -> {dest}")
    print(f"manifest: {P2F / 'hero_image.csv'}; render record: {out}")


if __name__ == "__main__":
    main()
