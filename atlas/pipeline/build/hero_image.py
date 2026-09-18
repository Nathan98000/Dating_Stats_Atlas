"""Phase 2g item 2.1: the hero is a couple, sourced through the SAME
licence gate as every other shipped image, still public domain / CC0
only — the hero renders as a cropped band, and cropping a CC-BY-SA
photo makes it an adaptation carrying ShareAlike — and preferring an
image where the faces are NOT identifiable: a recognizable couple on
the front page of a dating-statistics site is a publicity-rights
question, not just a licence one, and Commons images almost never carry
model releases.

Candidates are Commons FILE titles (a couple photograph has no
Wikipedia article whose lead image to take); each is read through
imageinfo -> clear_licence exactly like the city photographs, and the
first to clear the strict PD/CC0 bar ships. The shipped image frames
the couple from the shoulders down — no faces in frame at all, which is
the strongest available answer to the publicity question. The other
candidates reviewed are listed in PHASE2G.md with their licences.

Outputs:
  web/public/hero.jpg            gitignored like every shipped photo;
                                 this script re-materialises it
  results/phase2g/hero_image.csv the committed manifest row
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

from atlas.pipeline.build.city_images import (THUMB_WIDTH, clear_licence,
                                              download, imageinfo)
from atlas.pipeline.fetch import RESULTS

# in preference order; the first to clear the PD/CC0 gate ships
HERO_FILE_CANDIDATES = [
    "Adult couple holding hands.jpg",       # CC0; faces out of frame
    "Senior-3336451 1920.jpg",              # CC0; from behind
    "Couple walking into St Johns College Oxford.jpg",  # PD; from behind
]
HERO_ALT = ("A couple walking a city path holding hands, photographed "
            "from the shoulders down")
STRICT_PD = re.compile(r"^(public domain|pd\b|cc0)", re.IGNORECASE)

P2G = RESULTS / "phase2g"
WEB = RESULTS.parents[0] / "web"


def main() -> None:
    rec = None
    for name in HERO_FILE_CANDIDATES:
        ii = imageinfo(name)
        if not ii:
            print(f"  {name}: no imageinfo")
            continue
        cleared, reason = clear_licence(ii)
        if not cleared:
            print(f"  {name}: {reason}")
            continue
        if not STRICT_PD.match(cleared["license"]):
            print(f"  {name}: {cleared['license']} is not PD/CC0 — the "
                  f"band crop would be an adaptation; skipping")
            continue
        use_thumb = (ii.get("width") or 0) > THUMB_WIDTH
        rec = {
            "file_title": f"File:{name}",
            "source_url": ii.get("descriptionurl"),
            "image_url": (ii.get("thumburl") if use_thumb else None)
                         or ii.get("url"),
            **cleared,
        }
        break
    assert rec is not None, "no hero candidate cleared the PD/CC0 gate"

    dest = WEB / "public" / "hero.jpg"
    if dest.exists():
        dest.unlink()  # this script's job is to materialise the SOURCED hero
    sha = download(rec["image_url"], dest)
    assert sha, f"download failed: {rec['image_url']}"

    retrieved = time.strftime("%Y-%m-%d")
    P2G.mkdir(parents=True, exist_ok=True)
    row = {
        "subject": "couple holding hands (Phase 2g item 2.1)",
        "page_title": "",
        "file_title": rec["file_title"],
        "source_url": rec["source_url"],
        "image_url": rec["image_url"],
        "author": rec.get("author") or "",
        "license": rec["license"],
        "license_url": rec.get("license_url") or "",
        "retrieved": retrieved,
        "sha256": sha,
        "file": "hero.jpg",
        "alt": HERO_ALT,
    }
    with (P2G / "hero_image.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerow(row)

    hero_json = {
        "file": "hero.jpg",
        "sha256": sha,
        "alt": HERO_ALT,
        "author": rec.get("author") or None,
        "license": rec["license"],
        "license_url": rec.get("license_url"),
        "source_url": rec["source_url"],
    }
    out = WEB / "src" / "data" / "hero.json"
    out.write_text(json.dumps(hero_json, indent=1, ensure_ascii=False) + "\n")
    print(f"hero: {rec['file_title']} ({rec['license']}) -> {dest}")
    print(f"manifest: {P2G / 'hero_image.csv'}; render record: {out}")


if __name__ == "__main__":
    main()
