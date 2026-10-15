"""Phase 8 (the round-4 review's R20, after Nathan's go of 15 October 2026 to
make the recommended changes): the photographs the review flagged and Phase 7
left — Charleston's parked cars, York and Reno too small for the city band,
Peoria's bank logo, Fargo's "FARG" — recorded the way the photo review
records photographs (results/phase4/photo_review.json) and applied by its own
apply step. Phase 7's script (results/phase7/card_photos_apply.py) with
Phase 8's brief: nothing outside public domain, CC0, CC BY and CC BY-SA is
applied (no licence was approved in advance this time), and a pick may set a
photograph's focal point, or only that.

A pick (picks.json, one entry per city) is one of
  keep         {"keep": true, "why", "candidates_seen"} — the photograph stays
  focus only   {"focus_only": true, "focus", "why"} — the photograph stays,
               its focal point changes (a `photo_display` entry)
  a new photo  {"file_title", "image_url" (Wikimedia's 1920px rendition),
               "local_file" (those bytes, downloaded and looked at),
               "license", "license_url", "author", "source_url", "alt",
               "focus" (optional), "why", "checked", "alternatives"}
A new photograph becomes an `external_files` entry pinned by the sha256 of
the bytes looked at, with its credit as the file's Commons page states it.
A focal point is a `photo_display` entry added after any earlier one, so the
record keeps both and the later one sets the page. The outcome per city goes
to results/phase8/card_photos.json. Its alt texts are drafts for Nathan.

    PYTHONPATH=. .venv/bin/python atlas/results/phase8/card_photos_apply.py atlas/results/phase8/picks.json
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from atlas.pipeline.build import city_images as CI  # noqa: E402
from atlas.pipeline.build import photo_review as PR  # noqa: E402

HERE = Path(__file__).resolve().parent
WEB = ROOT / "atlas" / "web"
WHY = "Phase 8 (the round-4 review of 12 October 2026, R20; Nathan's go of 15 October 2026): "


def width_of(path: Path) -> int:
    out = subprocess.run(["sips", "-g", "pixelWidth", str(path)], capture_output=True, text=True).stdout
    return int(out.strip().rsplit(" ", 1)[-1]) if "pixelWidth" in out else -1


def main(picks_path: str) -> None:
    picks = json.loads(Path(picks_path).read_text())
    rev = json.loads(PR.REVIEW.read_text())
    city = json.loads((WEB / "src" / "data" / "city-images.json").read_text())
    external, display, record, staged = [], [], {}, []
    for slug, p in sorted(picks.items()):
        cur = city.get(slug, {})
        if p.get("keep"):
            record[slug] = {"outcome": "kept", "why": p["why"], "source_url": cur.get("source_url"),
                            "license": cur.get("license"), "candidates_seen": p.get("candidates_seen", [])}
            continue
        if p.get("focus"):
            display.append({"page": "city", "key": slug, "focus": p["focus"], "why": WHY + p["why"],
                            "was": cur.get("focus")})
        if p.get("focus_only"):
            record[slug] = {"outcome": "kept, new focal point", "focus": p["focus"],
                            "was": cur.get("focus"), "why": p["why"]}
            continue
        lic = p["license"]
        assert CI.ALLOW.match(lic) and not CI.REFUSE.search(lic), f"{slug}: {lic} is not on the list"
        src = ROOT / p["local_file"]
        assert src.is_file(), f"{slug}: {src} missing"
        w = width_of(src)
        assert w >= 1600, f"{slug}: {src.name} is {w}px wide"
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        ext = {"date": time.strftime("%Y-%m-%d"), "page": "city", "key": slug, "why": WHY + p["why"],
               "was": cur.get("source_url"), "title": PR.title_of(p["source_url"]),
               "author": p["author"], "license": lic, "license_url": p.get("license_url"),
               "source_url": p["source_url"], "image_url": p["image_url"], "sha256": sha,
               "alt": p["alt"],
               "licence_evidence": [f"as the file's Commons page states it (its licence section, "
                                    f"read {time.strftime('%Y-%m-%d')}): {lic}, by {p['author']}"],
               "checked": p.get("checked", "")}
        external.append(ext)
        dest = WEB / "public" / "cities" / f"{slug}{CI.external_suffix(p['image_url'])}"
        staged.append((src, dest, cur.get("file")))
        record[slug] = {"outcome": "new", "was": cur.get("source_url"), "file_title": p["file_title"],
                        "source_url": p["source_url"], "license": lic, "author": p["author"],
                        "width": w, "alt": p["alt"], "focus": p.get("focus"), "why": p["why"],
                        **({"alternatives": p["alternatives"]} if p.get("alternatives") else {})}
    new_keys = {e["key"] for e in external}
    rev["external_files"] = [r for r in rev.get("external_files", [])
                             if not (r["page"] == "city" and r["key"] in new_keys)] + external
    # a new photograph's alt text is its record's; an older override would
    # describe the photograph it replaces
    rev["alt_overrides"] = [r for r in rev.get("alt_overrides", [])
                            if not (r.get("page", "city") == "city" and r["key"] in new_keys)]
    # a new photograph keeps no earlier focal point or place caption of the
    # one it replaces; Phase 8's own entries are added after the rest
    rev["photo_display"] = [r for r in rev.get("photo_display", [])
                            if not (r["key"] in new_keys and (r.get("place") or r.get("focus")))
                            and not (r["key"] in {d["key"] for d in display} and r.get("why", "").startswith(WHY))
                            ] + display
    rev["phase8_photographs"] = {
        "date": time.strftime("%Y-%m-%d"),
        "brief": ("Phase 8: the round-4 review's R20 photographs that Phase 7 left — Charleston "
                  "without the parked cars across its foreground (a higher crop or a car-free view "
                  "of Rainbow Row or the Battery); York and Reno at the city band's width (1,056px; "
                  "at least 1,600px wide); Peoria from the bluffs only if clearly better; Fargo's "
                  "band reading its whole sign. A recognisable view of the city, daylight, under "
                  "public domain, CC0, CC BY or CC BY-SA, recorded as the file's page states it; "
                  "the choices and their alt texts are drafts for Nathan"),
        "rules": rev.get("phase6_photographs", {}).get("rules", []),
        "new_photographs": sorted(new_keys),
        "focal_points": {d["key"]: d["focus"] for d in display},
        "kept": sorted(k for k, v in record.items() if v["outcome"] == "kept"),
    }
    PR.REVIEW.write_text(json.dumps(rev, indent=1, ensure_ascii=False) + "\n")
    for src, dest, old_file in staged:
        old = WEB / "public" / "cities" / old_file if old_file else None
        if old and old.exists() and old != dest:
            PR._to_trash(old, "replaced")
        elif old and old.exists() and hashlib.sha256(old.read_bytes()).hexdigest() != hashlib.sha256(src.read_bytes()).hexdigest():
            PR._to_trash(old, "replaced")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    print(f"{len(external)} new photographs, {len(display)} focal points; applying")
    PR.main()
    out = {"date": time.strftime("%Y-%m-%d"), "cities": record}
    (HERE / "card_photos.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v["outcome"] for k, v in record.items()}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
