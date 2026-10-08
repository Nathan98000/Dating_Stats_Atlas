"""Phase 5 G: city photographs whose manifest alt text says nothing — a
filename, a bare "image", or the file's own title — by the rule the city
page applies (web/src/lib/city-photos.usableAlt), restated here. The page
renders alt="" for these (its h1 names the city); drafted alt texts for
Nathan are in PHASE5.md, never written into the manifest.

    python3 atlas/results/phase5/alt_audit.py -> atlas/results/phase5/alt_audit.json
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB = HERE.parents[1] / "web"


def usable(img: dict) -> bool:
    alt = (img.get("alt") or "").strip()
    if not alt or re.fullmatch(r"(?i)image|photo|picture|img", alt):
        return False
    if not re.search(r"\s", alt) and re.search(r"[\d_-]", alt):
        return False
    if re.search(r"(?i)\.(jpe?g|png|gif|tiff?|webp)$", alt):
        return False
    title = img.get("title") or ""
    if title and alt.lower() == title.lower() and not re.search(r"\s", alt):
        return False
    return True


images = json.loads((WEB / "src" / "data" / "city-images.json").read_text())
bad = {slug: {"alt": img.get("alt"), "title": img.get("title"), "file": img["file"],
              "on_disk": (WEB / "public" / "cities" / img["file"]).exists(),
              "source_url": img["source_url"]}
       for slug, img in images.items() if not usable(img)}
(HERE / "alt_audit.json").write_text(json.dumps({"rule": "web/src/lib/city-photos.usableAlt",
                                                 "metros": len(images), "unusable": bad},
                                                indent=1, ensure_ascii=False) + "\n")
print(len(images), "photos;", len(bad), "with an unusable alt")
for s, b in bad.items():
    print(s, "|", b["alt"], "|", b["title"])
