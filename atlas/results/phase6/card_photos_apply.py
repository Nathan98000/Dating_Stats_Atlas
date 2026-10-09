"""Phase 6 (commit I, the round-3 review §7 / F30): the photographs that
change — Los Angeles without the Hollywood Sign, and the weak photographs
the review lists, each replaced only where a clearly better candidate
passes the licence list (public domain, CC0, CC BY, CC BY-SA) — recorded
the way the photo review records photographs (results/phase4/
photo_review.json) and applied by its own apply step.

A pick (picks.json, one entry per city) is either
  keep         {"keep": true, "why": ...} — the current photograph stays
  a new photo  {"file_title", "image_url" (Wikimedia's 1920px rendition),
               "local_file" (those bytes, downloaded and looked at),
               "license", "license_url", "author", "source_url", "alt",
               "why", "alternatives": [...] (Los Angeles: the two others)}
A new photograph becomes an `external_files` entry pinned by the sha256 of
the bytes looked at, with its credit as the file's Commons page states it;
nothing outside the four licences is applied (it goes on the permission
list instead). Kalamazoo's alt text is an `alt_overrides` entry. The
outcome per city goes to results/phase6/card_photos.json.

    PYTHONPATH=. .venv/bin/python atlas/results/phase6/card_photos_apply.py atlas/results/phase6/picks.json
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
WHY = "Phase 6 (the round-3 review of 8 October 2026, §7 and F30; Nathan's decisions 6 and 10): "


def width_of(path: Path) -> int:
    out = subprocess.run(["sips", "-g", "pixelWidth", str(path)], capture_output=True, text=True).stdout
    return int(out.strip().rsplit(" ", 1)[-1]) if "pixelWidth" in out else -1


def main(picks_path: str) -> None:
    picks = json.loads(Path(picks_path).read_text())
    rev = json.loads(PR.REVIEW.read_text())
    city = json.loads((WEB / "src" / "data" / "city-images.json").read_text())
    external, alts, record, staged = [], [], {}, []
    for slug, p in sorted(picks.items()):
        cur = city.get(slug, {})
        if p.get("alt_only"):
            alts.append({"page": "city", "key": slug, "alt": p["alt"], "why": WHY + p["why"]})
            record[slug] = {"outcome": "kept, new alt text (draft)", "alt": p["alt"], "why": p["why"]}
            continue
        if p.get("keep"):
            record[slug] = {"outcome": "kept", "why": p["why"], "source_url": cur.get("source_url"),
                            "license": cur.get("license"), "candidates_seen": p.get("candidates_seen", [])}
            continue
        lic = p["license"]
        assert CI.ALLOW.match(lic) and not CI.REFUSE.search(lic), f"{slug}: {lic} is outside the licence list"
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
                        "width": w, "alt": p["alt"], "why": p["why"],
                        **({"alternatives": p["alternatives"]} if p.get("alternatives") else {})}
    keys = {e["key"] for e in external + alts}
    rev["external_files"] = [r for r in rev.get("external_files", [])
                             if not (r["page"] == "city" and r["key"] in keys)] + external
    rev["alt_overrides"] = [r for r in rev.get("alt_overrides", []) if r["key"] not in keys] + alts
    # a city whose new photograph shows the city itself loses its place caption
    rev["photo_display"] = [r for r in rev.get("photo_display", [])
                            if not (r["key"] in {e["key"] for e in external} and r.get("place"))]
    rev["phase6_photographs"] = {
        "date": time.strftime("%Y-%m-%d"),
        "brief": ("Phase 6 §I: Los Angeles without the Hollywood Sign (the downtown skyline with the "
                  "San Gabriel Mountains first); the weak photographs of the review's §7 replaced "
                  "only by a clearly better candidate — a recognisable view of the city, daylight "
                  "where possible, at least 1,600px wide — under public domain, CC0, CC BY or CC "
                  "BY-SA; focal points for five crops"),
        "rules": rev.get("phase5_card_photos", {}).get("rules", []) + [
            "no prominent logo, seal or trademark as the subject (the Hollywood Sign; a hotel brand)"],
        "new_photographs": [e["key"] for e in external],
        "alt_overrides": [a["key"] for a in alts],
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
    print(f"{len(external)} new photographs, {len(alts)} alt texts; applying")
    PR.main()
    out = {"date": time.strftime("%Y-%m-%d"), "cities": record,
           "permission_needed": sorted(k for k, v in record.items() if v.get("permission_needed"))}
    (HERE / "card_photos.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v["outcome"] for k, v in record.items()}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
