"""After the Phase 5 report (Nathan, 8 October 2026): "Choose appropriate
photos for each city and implement them. Do not use the map on the city
cards on the home page." Then: "Photos do not have to come specifically
from Wikimedia. Assume that I will be able to get license permission. Just
get the most representative photos you can for each city."

Every ranked city can be a home-page card, so each of the 193 needs a
representative photograph a card may crop. The picks — the twelve top
cities chosen on contact sheets (results/phase5/_card_photos/h_picks.json),
the rest in eight reviewed batches (…/batch_*.json), then the final
review's own replacements (…/review_picks.json, given last so they win) —
come in two kinds, and this script records each the way the photo review
already records photographs (results/phase4/photo_review.json), then runs
the review's apply step:

  keep_current   the city's photograph stays; its reviewed alt text is
                 recorded as an `alt_overrides` entry
  a new photo    an `external_files` entry pinned by the exact bytes the
                 batch downloaded and looked at (sha256), with the exact
                 link it came from and its credit as the source states it
                 (for a Commons file: its author, licence and licence link
                 from the pipeline's cached imageinfo). Wikimedia was
                 refusing this machine's requests for original files (HTTP
                 429) while the batches ran, so nothing here asks it for
                 anything: the old file goes to the Trash and the pinned
                 bytes go in place. Nathan arranges any permission needed

and writes results/phase5/card_photos.json: every city's outcome, and
which photographs need permission.

    PYTHONPATH=. .venv/bin/python atlas/results/phase5/card_photos_apply.py <picks.json> [...]
"""
from __future__ import annotations

import hashlib
import json
import re
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
PREFETCHED = HERE / "_card_photos"
OPEN = re.compile(r"^(public domain|pd\b|cc0|cc[ -]by(\b|[ -]sa\b))", re.IGNORECASE)


def needs_permission(licence: str | None) -> bool:
    """Not public domain, CC0, CC BY or CC BY-SA: a non-commercial or
    no-derivatives licence (the cards crop every photograph), another free
    licence the site's rule does not list, or none stated."""
    return not OPEN.match(licence or "") or bool(CI.REFUSE.search(licence or ""))


def cached_imageinfo(name: str) -> dict | None:
    """city_images.imageinfo's answer as its cache holds it (the batches
    asked it for every Commons pick) — no network call."""
    params = {"action": "query", "titles": f"File:{name}", "prop": "imageinfo",
              "iiprop": "extmetadata|url|sha1|size|mime", "iiurlwidth": CI.THUMB_WIDTH,
              "format": "json"}
    key = hashlib.sha256((CI.API + json.dumps(params, sort_keys=True)).encode()).hexdigest()[:20]
    path = CI.CACHE / f"{key}.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    for pg in d.get("query", {}).get("pages", {}).values():
        ii = (pg.get("imageinfo") or [None])[0]
        if ii:
            return ii
    return None


def width_of(path: Path) -> int:
    out = subprocess.run(["sips", "-g", "pixelWidth", str(path)], capture_output=True, text=True).stdout
    return int(out.strip().rsplit(" ", 1)[-1]) if "pixelWidth" in out else -1


def local_file(slug: str, p: dict) -> Path | None:
    """The file the batch downloaded for this pick."""
    lf = p.get("local_file") or ""
    cands = []
    if lf:
        cands += [ROOT / lf, ROOT / "atlas" / lf.replace("atlas/", "", 1)]
    cands += sorted(PREFETCHED.glob(f"{slug}.*"))
    for cand in cands:
        if cand.is_file() and cand.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            return cand
    return None


def main(paths: list[str]) -> None:
    picks: dict[str, dict] = {}
    for p in paths:
        picks.update(json.loads(Path(p).read_text()))
    rev = json.loads(PR.REVIEW.read_text())
    refused = PR.refused_files()
    city = json.loads((WEB / "src" / "data" / "city-images.json").read_text())
    import pandas as pd
    csv = pd.read_csv(PR.P2E / "city_images.csv", dtype={"cbsa": str})
    approved_alts = {r["key"] for r in rev.get("replaced", []) if r.get("alt")}
    external, alts, record = [], [], {}
    staged: list[tuple[Path, Path, str | None]] = []
    for slug, p in sorted(picks.items()):
        if p.get("none"):
            record[slug] = {"outcome": "none", "why": p.get("why", "")}
            continue
        row = csv[csv["slug"] == slug]
        ok = len(row) and row.iloc[0].get("status") == "ok"
        was = row.iloc[0]["file_title"] if ok else None
        old_file = row.iloc[0]["file"] if ok else None
        why = ("After the Phase 5 report (Nathan, 2026-10-08): the most representative photograph "
               "of each city for its home-page card. " + p.get("why", ""))
        ft = p.get("file_title")
        if p.get("keep_current") or (ft and ft == was):
            cur = city.get(slug)
            assert cur, f"{slug}: kept, but the city has no photograph"
            # an alt text Nathan approved (Phase 4c: Waco's and Savannah's
            # replacements) stays as he approved it
            if p.get("alt") and p["alt"] != cur.get("alt") and slug not in approved_alts:
                alts.append({"page": "city", "key": slug, "alt": p["alt"], "why": why})
            record[slug] = {"outcome": "kept", "license": cur["license"], "author": cur["author"],
                            "source_url": cur["source_url"], "alt": p.get("alt") or cur.get("alt"),
                            "permission_needed": needs_permission(cur["license"])}
            continue
        ii = cached_imageinfo(ft.split("File:", 1)[-1]) if ft else None
        cleared, _ = CI.clear_licence(ii) if ii else (None, "no cached imageinfo")
        # pinned by the bytes the batch downloaded
        assert not (ft and ft in refused), f"{slug}: {ft} was refused by the photo review"
        src = local_file(slug, p)
        assert src, f"{slug}: no downloaded file for {p.get('source_url')}"
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        licence = (cleared or {}).get("license") or p.get("license") or "unknown — permission needed"
        image_url = p.get("image_url")
        assert image_url, f"{slug}: no image link recorded"
        assert width_of(src) >= 1000, f"{slug}: {src} is too small ({width_of(src)}px)"
        source_url = p.get("source_url") or (ii or {}).get("descriptionurl")
        title = PR.title_of(source_url) if ft and source_url else (p.get("title") or p.get("where") or slug)
        ext = {"date": time.strftime("%Y-%m-%d"), "page": "city", "key": slug, "why": why,
               "was": was, "title": title,
               "author": (cleared or {}).get("author") or p.get("author") or "unknown",
               "license": licence,
               "license_url": (cleared or {}).get("license_url") or p.get("license_url"),
               "source_url": source_url,
               "image_url": image_url, "sha256": sha, "alt": p["alt"],
               "licence_evidence": [f"as the source states it: {licence}",
                                    "Nathan, 2026-10-08: assume he gets licence permission"]}
        external.append(ext)
        dest = WEB / "public" / "cities" / f"{slug}{CI.external_suffix(image_url)}"
        staged.append((src, dest, old_file))
        record[slug] = {"outcome": "new", "from_commons": bool(ft), "was": was, "source_url": source_url,
                        "license": licence, "author": ext["author"], "alt": p["alt"],
                        "permission_needed": needs_permission(licence)}
    # the review's earlier entries stand (Phase 4c's replacements and
    # restorations are Nathan's calls; a city taking a new photograph skips
    # them when the review applies); only this script's own entries renew
    keys = {e["key"] for e in external + alts}
    rev["external_files"] = [r for r in rev.get("external_files", [])
                             if not (r["page"] == "city" and r["key"] in keys)] + external
    rev["alt_overrides"] = [r for r in rev.get("alt_overrides", []) if r["key"] not in keys] + alts
    rev["phase5_card_photos"] = {
        "date": time.strftime("%Y-%m-%d"),
        "brief": ("Nathan, after the Phase 5 report: the most representative photograph of each "
                  "city, from any source (he gets the licence permission); no locator map on the "
                  "home page's cards; every city photograph may be cropped"),
        "rules": ["the view people recognise: a skyline, signature landmark, famous street, "
                  "district or waterfront, in daylight", "the photo review's rules: no "
                  "identifiable person as the subject, no recent sculpture or mural as a subject, "
                  "no prominent government seal", "landscape, good cropped to 16:10 and 16:7"],
        "new_photographs": len([r for r in rev["external_files"] if r["page"] == "city"]),
        "alt_overrides": len(rev["alt_overrides"]),
    }
    PR.REVIEW.write_text(json.dumps(rev, indent=1, ensure_ascii=False) + "\n")
    # stage the outside files: the old file to the Trash, the pinned bytes in place
    for src, dest, old_file in staged:
        old = WEB / "public" / "cities" / old_file if isinstance(old_file, str) else None
        new_sha = hashlib.sha256(src.read_bytes()).hexdigest()
        if old and old.exists() and hashlib.sha256(old.read_bytes()).hexdigest() != new_sha:
            PR._to_trash(old, "replaced")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    print(f"{len(external)} new photographs, {len(alts)} alt texts; applying")
    PR.main()
    city = json.loads((WEB / "src" / "data" / "city-images.json").read_text())
    idx = json.loads((WEB / "src" / "data" / "search-index.json").read_text())
    missing = [e["s"] for e in idx if e["r"] and not (
        e["s"] in city and (WEB / "public" / "cities" / city[e["s"]]["file"]).exists())]
    path = HERE / "card_photos.json"
    prior = json.loads(path.read_text()) if path.exists() else {"cities": {}}
    cities = {**prior.get("cities", {}), **record}
    out = {"date": time.strftime("%Y-%m-%d"), "cities": cities,
           "permission_needed": sorted(k for k, v in cities.items() if v.get("permission_needed")),
           "ranked_without_a_photo_on_disk": missing}
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"ranked cities without a photo on disk: {missing}")
    print(f"photographs needing permission: {out['permission_needed']}")


if __name__ == "__main__":
    main(sys.argv[1:])
