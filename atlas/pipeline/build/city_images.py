"""Source real photographs for city pages and stat pages (Phase 2e items
4 and 6), with the licence recorded or the image refused.

Pipeline per metro (and per configured stat page): the principal city's
Wikipedia article via the REST summary endpoint -> the article's lead
image name via the MediaWiki pageimages API -> that file's licence,
author, links and hashes via imageinfo/extmetadata. An image ships only
when the licence is readable from the API and on Nathan's cleared list
(public domain, CC0, CC-BY, CC-BY-SA — any NC or ND term refuses), and —
because CC-BY/BY-SA attribution needs an author — only when the author
field is readable for those licences.

Obligations satisfied by construction, not memory:
  - the served file is Wikimedia's own scaled rendition (iiurlwidth) —
    scaling, never cropping, recolouring or compositing, so no
    adaptation is created and share-alike never attaches to one;
  - the attribution string (author, licence name, licence deed link,
    source file link) is composed HERE into the manifest, and the page
    renders the manifest rather than recomposing.

Outputs:
  results/phase2e/city_images.csv        the committed manifest
  results/phase2e/stat_images.csv        the committed stat-page manifest
  web/src/data/city-images.json          what the pages render
  web/src/data/stat-images.json
  web/public/cities/<slug>.<ext>         the files themselves (gitignored,
  web/public/stats/<fid>.<ext>           re-fetchable; hashes pin them)
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.parse
from pathlib import Path

import pandas as pd
import requests

from atlas.pipeline.fetch import DATA, RESULTS

WEB = RESULTS.parents[0] / "web"
P2E = RESULTS / "phase2e"
CACHE = DATA / "raw" / "wiki_images"
UA = {"User-Agent": "DatingStatsAtlas/0.1 (research build; contact via repo)"}

SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
API = "https://en.wikipedia.org/w/api.php"
THUMB_WIDTH = 1600

# licences Nathan cleared: PD, CC0, CC-BY, CC-BY-SA — nothing NC or ND,
# nothing unreadable
ALLOW = re.compile(r"^(public domain|pd\b|cc0|cc[ -]by(\b|[ -]sa\b))", re.IGNORECASE)
REFUSE = re.compile(r"\b(nc|nd)\b", re.IGNORECASE)

# stat-page subjects (item 6): hand-chosen article per page, few enough
# to review by hand; the lead image rides the same licensing pipeline
STAT_SUBJECTS = {
    "median_gross_rent": ["Apartment"],
    "everyday_prices": ["Supermarket", "Grocery store"],
    "venues_per_100k": ["Nightlife", "Restaurant", "Coffeehouse"],
    "resident_walkability_index": ["Sidewalk", "Pedestrian"],
    "pleasant_days": ["Picnic", "Park"],
    "students_per_1k_adults": ["College town", "Campus"],
    "who_lives_here": ["Crowd", "Pedestrian zone"],
}


def _get_json(url: str, params: dict | None = None) -> dict | None:
    key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True))
                         .encode()).hexdigest()[:20]
    cache = CACHE / f"{key}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 404:
                d = {"__404__": True}
            else:
                r.raise_for_status()
                d = r.json()
            CACHE.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(d))
            time.sleep(0.15)
            return d
        except Exception:  # noqa: PERF203
            time.sleep(2.0 * (attempt + 1))
    return None


def _strip_html(s: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()
    # Commons' Creator template leaves its label in the text
    return re.sub(r"^creator:\s*", "", t, flags=re.IGNORECASE)


def summary(title: str) -> dict | None:
    # the REST endpoint speaks underscored titles: "Portland, Oregon"
    # must travel as Portland,_Oregon — %20 silently 404s (the first run
    # lost every two-word candidate to this and lived off bare-city
    # redirects)
    t = urllib.parse.quote(title.replace(" ", "_"), safe="")
    d = _get_json(SUMMARY.format(title=t))
    if not d or d.get("__404__") or d.get("type") != "standard":
        return None
    return d


def lead_image_name(title: str) -> str | None:
    d = _get_json(API, {"action": "query", "titles": title,
                        "prop": "pageimages", "piprop": "name",
                        "redirects": 1, "format": "json"})
    if not d:
        return None
    pages = d.get("query", {}).get("pages", {})
    for p in pages.values():
        if p.get("pageimage"):
            return p["pageimage"]
    return None


def imageinfo(file_name: str) -> dict | None:
    d = _get_json(API, {"action": "query", "titles": f"File:{file_name}",
                        "prop": "imageinfo",
                        "iiprop": "extmetadata|url|sha1|size|mime",
                        "iiurlwidth": THUMB_WIDTH, "format": "json"})
    if not d:
        return None
    pages = d.get("query", {}).get("pages", {})
    for p in pages.values():
        ii = (p.get("imageinfo") or [None])[0]
        if ii:
            return ii
    return None


def clear_licence(ii: dict) -> tuple[dict | None, str]:
    """(cleared metadata, reason-if-refused). Refusal reasons are the
    coverage report's vocabulary."""
    ext = ii.get("extmetadata", {})

    def field(k):
        return _strip_html(str(ext.get(k, {}).get("value", "")))

    lic = field("LicenseShortName")
    if not lic:
        return None, "no_readable_licence"
    if REFUSE.search(lic):
        return None, f"refused_terms:{lic}"
    if not ALLOW.match(lic):
        return None, f"not_cleared:{lic}"
    if ii.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
        return None, f"not_a_photograph:{ii.get('mime')}"
    author = field("Artist")
    needs_author = lic.lower().startswith("cc by") or "attribution" in lic.lower()
    if needs_author and not author:
        return None, f"attribution_unreadable:{lic}"
    return {
        "license": lic,
        "license_url": _strip_html(str(ext.get("LicenseUrl", {})
                                       .get("value", ""))) or None,
        "author": author or None,
        "description": field("ImageDescription"),
    }, ""


def download(url: str, dest: Path) -> str | None:
    """Fetch Wikimedia's own rendition; return sha256 or None. A file
    already on disk is reused (re-runs re-key manifests cheaply; the
    manifest hash still pins content)."""
    if dest.exists():
        return hashlib.sha256(dest.read_bytes()).hexdigest()
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=120)
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            time.sleep(0.2)
            return hashlib.sha256(r.content).hexdigest()
        except Exception:  # noqa: PERF203
            time.sleep(2.0 * (attempt + 1))
    return None


def source_one(candidates: list[str]) -> tuple[dict | None, str]:
    """Try article titles in order; return (record, refusal_reason)."""
    last_reason = "no_article"
    for title in candidates:
        s = summary(title)
        if not s:
            last_reason = "no_article"
            continue
        resolved = s.get("titles", {}).get("canonical", title)
        name = lead_image_name(resolved)
        if not name:
            last_reason = "no_lead_image"
            continue
        ii = imageinfo(name)
        if not ii:
            last_reason = "no_imageinfo"
            continue
        cleared, reason = clear_licence(ii)
        if not cleared:
            last_reason = reason
            continue
        # Wikimedia refuses UPSCALES: a 1600px thumb of a smaller original
        # 404s, so small originals ship at their own size (still their
        # rendition, still unmodified)
        use_thumb = (ii.get("width") or 0) > THUMB_WIDTH
        return {
            "page_title": resolved,
            "file_title": f"File:{name}",
            "source_url": ii.get("descriptionurl"),
            "image_url": (ii.get("thumburl") if use_thumb else None)
                         or ii.get("url"),
            "mime": ii.get("mime"),
            "commons_sha1": ii.get("sha1"),
            **cleared,
        }, ""
    return None, last_reason


def main() -> None:
    P2E.mkdir(parents=True, exist_ok=True)
    cm = pd.read_csv(RESULTS / "phase2c" / "city_meta.csv", dtype={"cbsa": str})
    retrieved = time.strftime("%Y-%m-%d")

    rows, render, reasons = [], {}, {}
    for n, (_, m) in enumerate(cm.iterrows()):
        city = m["display_name_full"].split(",")[0].strip()
        state = m["state_full"]
        rec, reason = source_one([f"{city}, {state}", city])
        if not rec:
            reasons[reason] = reasons.get(reason, 0) + 1
            rows.append({"cbsa": m["cbsa"], "slug": m["slug"],
                         "status": reason})
            continue
        ext = {"image/png": ".png", "image/webp": ".webp"}.get(
            rec["mime"], ".jpg")
        dest = WEB / "public" / "cities" / f"{m['slug']}{ext}"
        sha = download(rec["image_url"], dest)
        if not sha:
            reasons["download_failed"] = reasons.get("download_failed", 0) + 1
            rows.append({"cbsa": m["cbsa"], "slug": m["slug"],
                         "status": "download_failed"})
            continue
        alt = rec["description"][:160].rstrip() if rec["description"] else ""
        rows.append({"cbsa": m["cbsa"], "slug": m["slug"], "status": "ok",
                     "page_title": rec["page_title"],
                     "file_title": rec["file_title"],
                     "source_url": rec["source_url"],
                     "image_url": rec["image_url"],
                     "author": rec["author"], "license": rec["license"],
                     "license_url": rec["license_url"],
                     "retrieved": retrieved, "sha256": sha,
                     "file": dest.name})
        render[m["slug"]] = {
            "file": dest.name,
            "alt": alt or None,
            "author": rec["author"],
            "license": rec["license"],
            "license_url": rec["license_url"],
            "source_url": rec["source_url"],
        }
        if (n + 1) % 50 == 0:
            print(f"  {n + 1}/{len(cm)} metros")

    df = pd.DataFrame(rows)
    df.to_csv(P2E / "city_images.csv", index=False)
    (WEB / "src" / "data" / "city-images.json").write_text(
        json.dumps(render, indent=0, ensure_ascii=False, sort_keys=True) + "\n")

    # ---- stat-page images (item 6) --------------------------------------
    stat_rows, stat_render = [], {}
    for fid, cands in STAT_SUBJECTS.items():
        rec, reason = source_one(cands)
        if not rec:
            stat_rows.append({"stat": fid, "status": reason})
            continue
        ext = {"image/png": ".png", "image/webp": ".webp"}.get(
            rec["mime"], ".jpg")
        dest = WEB / "public" / "stats" / f"{fid}{ext}"
        sha = download(rec["image_url"], dest)
        if not sha:
            stat_rows.append({"stat": fid, "status": "download_failed"})
            continue
        stat_rows.append({"stat": fid, "status": "ok",
                          "page_title": rec["page_title"],
                          "file_title": rec["file_title"],
                          "source_url": rec["source_url"],
                          "image_url": rec["image_url"],
                          "author": rec["author"], "license": rec["license"],
                          "license_url": rec["license_url"],
                          "retrieved": retrieved, "sha256": sha,
                          "file": dest.name})
        stat_render[fid] = {
            "file": dest.name,
            "alt": (rec["description"][:160].rstrip()
                    if rec["description"] else None),
            "author": rec["author"], "license": rec["license"],
            "license_url": rec["license_url"],
            "source_url": rec["source_url"],
        }
    pd.DataFrame(stat_rows).to_csv(P2E / "stat_images.csv", index=False)
    (WEB / "src" / "data" / "stat-images.json").write_text(
        json.dumps(stat_render, indent=0, ensure_ascii=False, sort_keys=True) + "\n")

    ok = int((df["status"] == "ok").sum())
    print(json.dumps({"metros": len(df), "photos": ok,
                      "fallback_to_artwork": len(df) - ok,
                      "refusals": reasons,
                      "stat_pages_with_photo": sum(1 for r in stat_rows
                                                   if r["status"] == "ok")},
                     indent=1))
    lic_counts = df[df["status"] == "ok"]["license"].value_counts().to_dict()
    print("licences:", json.dumps(lic_counts, indent=1))


if __name__ == "__main__":
    main()
