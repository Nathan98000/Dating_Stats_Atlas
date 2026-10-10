"""Source real photographs for city pages and stat pages (Phase 2e items
4 and 6), with the licence recorded or the image refused.

Pipeline per metro (and per configured stat page): the principal city's
Wikipedia article via the REST summary endpoint -> the article's lead
image name via the MediaWiki pageimages API -> that file's licence,
author, links and hashes via imageinfo/extmetadata -> after the credit
audit (Nathan, 2026-10-10), the file's own Commons page: where it pairs an
old artwork's public-domain tag (or an artwork template) with a licence of
the photograph's own, the photograph's licence and photographer are what
clears and is credited, never the artwork's (commons_page.py). An image
ships only when the licence is readable and on Nathan's cleared list
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

from atlas.pipeline.build import commons_page as CP
from atlas.pipeline.build.photo_review import (CROPPED, external_files, pinned_alts,
                                               pinned_files, refused_files,
                                               title_of)
from atlas.pipeline.fetch import DATA, RESULTS

WEB = RESULTS.parents[0] / "web"
P2E = RESULTS / "phase2e"
CACHE = DATA / "raw" / "wiki_images"
UA = {"User-Agent": "DatingStatsAtlas/0.1 (research build; contact via repo)"}

SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Commons allows this machine's user agent about ten requests a minute
COMMONS_PAUSE = 6.0
THUMB_WIDTH = 1600

# Phase 4 (ADR 0012): files the photo review removed are refused on sight
REVIEW_REFUSED = refused_files()
# after Phase 4c (Nathan's calls): pages whose photograph the review
# replaced take exactly the Commons file it names
REVIEW_PINNED = pinned_files()
REVIEW_ALTS = pinned_alts()
# 2026-10-07 (Nathan's pick): photographs from outside Commons, pinned by hash
REVIEW_EXTERNAL = external_files()

# licences Nathan cleared: PD, CC0, CC-BY, CC-BY-SA — nothing NC or ND,
# nothing unreadable
ALLOW = re.compile(r"^(public domain|pd\b|cc0|cc[ -]by(\b|[ -]sa\b))", re.IGNORECASE)
REFUSE = re.compile(r"\b(nc|nd)\b", re.IGNORECASE)

# stat-page subjects (item 6): hand-chosen article per page, few enough
# to review by hand; the lead image rides the same licensing pipeline
STAT_SUBJECTS = {
    "rent_1br": ["Apartment"],
    "everyday_prices": ["Supermarket", "Grocery store"],
    "venues_per_100k": ["Nightlife", "Restaurant", "Coffeehouse"],
    "resident_walkability_index": ["Sidewalk", "Pedestrian"],
    "pleasant_days": ["Picnic", "Park"],
    "students_per_1k_adults": ["College town", "Campus"],
    # Phase 4e (Nathan): a residential neighbourhood, not a crowd — a crowd
    # risks an identifiable person as the subject ("Crowd"'s candidate also
    # failed the licence check, KOGL Type 1)
    "who_lives_here": ["Row house", "Suburb", "Neighbourhood"],
    # Phase 4e (Nathan): a neutral voting image — no party symbols,
    # candidates, campaign signs or slogans (the review checks each pick)
    "political_lean": ["Ballot box", "Polling place", "Voting booth"],
}


def _cache_file(url: str, params: dict | None = None) -> Path:
    key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True))
                         .encode()).hexdigest()[:20]
    return CACHE / f"{key}.json"


def _get_json(url: str, params: dict | None = None) -> dict | None:
    cache = _cache_file(url, params)
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


_last_commons = [0.0]


def _commons_json(params: dict) -> dict | None:
    """A Commons API answer through the cache; an uncached call keeps
    COMMONS_PAUSE seconds from the previous one."""
    if not _cache_file(COMMONS_API, params).exists():
        time.sleep(max(0.0, COMMONS_PAUSE - (time.monotonic() - _last_commons[0])))
        d = _get_json(COMMONS_API, params)
        _last_commons[0] = time.monotonic()
        return d
    return _get_json(COMMONS_API, params)


def file_page(file_name: str) -> str | None:
    """The file's Commons description page (its current wikitext), or None
    when it cannot be read. The parameters are the credit audit's, so its
    cache serves the pipeline."""
    d = _commons_json({"action": "query", "titles": f"File:{file_name}", "prop": "revisions",
                       "rvprop": "content|ids|timestamp", "rvslots": "main", "redirects": 1,
                       "format": "json", "formatversion": 2})
    pages = ((d or {}).get("query") or {}).get("pages") or []
    rv = (pages[0].get("revisions") or [None])[0] if pages else None
    return rv["slots"]["main"].get("content") if rv else None


def uploader_of(file_name: str) -> str | None:
    """Who uploaded the file (its page's first revision): the holder a
    {{self}} licence names when the page names no author."""
    d = _commons_json({"action": "query", "titles": f"File:{file_name}", "prop": "revisions",
                       "rvprop": "user|timestamp|ids", "rvlimit": 1, "rvdir": "newer",
                       "redirects": 1, "format": "json", "formatversion": 2})
    pages = ((d or {}).get("query") or {}).get("pages") or []
    rv = (pages[0].get("revisions") or [None])[0] if pages else None
    return (rv or {}).get("user")


def clear_licence(ii: dict, page: str | None = None,
                  uploader=None) -> tuple[dict | None, str]:
    """(cleared metadata, reason-if-refused). Refusal reasons are the
    coverage report's vocabulary.

    After the credit audit (Nathan, 2026-10-10): with the file's page
    (`page`, its wikitext; `uploader`, a call that names who uploaded it),
    a page that pairs an old artwork's public-domain tag (or an artwork
    template) with a licence of the photograph's own clears on that
    licence, credited to the photographer, never the artwork's licence or
    creator (commons_page.photograph_credit). Without a page, or for any
    other page, the metadata's answer stands, as before."""
    ext = ii.get("extmetadata", {})

    def field(k):
        return _strip_html(str(ext.get(k, {}).get("value", "")))

    lic = field("LicenseShortName")
    own = CP.photograph_credit(page) if page else None
    if own and own.get("unreadable"):
        return None, f"photo_licence_unreadable:{own['unreadable']}"
    if own:
        keys = own["licences"]
        listed = [k for k in keys if ALLOW.match(k) and not REFUSE.search(k)]
        if not listed:
            return None, f"photo_licence_not_cleared:{CP.display_licence(keys[0])}"
        # a licence the metadata named among the photograph's own stays
        key = next((k for k in CP.norm_licence(lic) if k in listed), listed[0])
        lic = CP.display_licence(key)
        license_url = CP.licence_link(key)
        author = own["author"] or (uploader() if uploader else None)
    else:
        if not lic:
            return None, "no_readable_licence"
        if REFUSE.search(lic):
            return None, f"refused_terms:{lic}"
        if not ALLOW.match(lic):
            return None, f"not_cleared:{lic}"
        license_url = _strip_html(str(ext.get("LicenseUrl", {}).get("value", ""))) or None
        author = field("Artist")
    if ii.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
        return None, f"not_a_photograph:{ii.get('mime')}"
    needs_author = lic.lower().startswith("cc by") or "attribution" in lic.lower()
    if needs_author and not author:
        return None, f"attribution_unreadable:{lic}"
    return {
        "license": lic,
        "license_url": license_url,
        "author": author or None,
        "description": field("ImageDescription"),
    }, ""


def clear_file(file_name: str, ii: dict) -> tuple[dict | None, str]:
    """clear_licence with the file's own page, as every photograph the
    pipeline sources is cleared since the credit audit; a page that cannot
    be read refuses (nothing unreadable ships)."""
    page = file_page(file_name)
    if page is None:
        return None, "no_readable_page"
    return clear_licence(ii, page=page, uploader=lambda: uploader_of(file_name))


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
        if f"File:{name}" in REVIEW_REFUSED:
            # Phase 4 (ADR 0012): the photo review removed this file
            last_reason = REVIEW_REFUSED[f"File:{name}"]
            continue
        ii = imageinfo(name)
        if not ii:
            last_reason = "no_imageinfo"
            continue
        cleared, reason = clear_file(name, ii)
        if not cleared:
            last_reason = reason
            continue
        return _record(resolved, name, ii, cleared), ""
    return None, last_reason


def _record(page_title: str | None, name: str, ii: dict, cleared: dict) -> dict:
    # Wikimedia refuses UPSCALES: a 1600px thumb of a smaller original
    # 404s, so small originals ship at their own size (still their
    # rendition, still unmodified)
    use_thumb = (ii.get("width") or 0) > THUMB_WIDTH
    return {
        "page_title": page_title,
        "file_title": f"File:{name}",
        "source_url": ii.get("descriptionurl"),
        "image_url": (ii.get("thumburl") if use_thumb else None)
                     or ii.get("url"),
        "mime": ii.get("mime"),
        "commons_sha1": ii.get("sha1"),
        **cleared,
    }


def source_file(file_title: str) -> tuple[dict | None, str]:
    """One named Commons file (the photo review's replacements), cleared
    exactly as source_one clears an article's lead image; no article, so
    no page title."""
    name = file_title.split("File:", 1)[-1]
    if file_title in REVIEW_REFUSED:
        return None, REVIEW_REFUSED[file_title]
    ii = imageinfo(name)
    if not ii:
        return None, "no_imageinfo"
    cleared, reason = clear_file(name, ii)
    if not cleared:
        return None, reason
    return _record(None, name, ii, cleared), ""


def source_stat(fid: str, cands: list[str], retrieved: str) -> tuple[dict, dict | None]:
    """One stat page's photograph: (manifest row, render entry or None).
    A page the review pins takes its named file; otherwise the subjects'
    articles are tried in order, each lead image through the licence rule
    and past the files the review refused."""
    ext = REVIEW_EXTERNAL.get(("stat", fid))
    if ext:
        return source_external(fid, ext, retrieved)
    pin = REVIEW_PINNED.get(("stat", fid))
    rec, reason = source_file(pin) if pin else source_one(cands)
    if not rec:
        return {"stat": fid, "status": reason}, None
    ext = {"image/png": ".png", "image/webp": ".webp"}.get(rec["mime"], ".jpg")
    dest = WEB / "public" / "stats" / f"{fid}{ext}"
    sha = download(rec["image_url"], dest)
    if not sha:
        return {"stat": fid, "status": "download_failed"}, None
    row = {"stat": fid, "status": "ok", "page_title": rec["page_title"],
           "file_title": rec["file_title"], "source_url": rec["source_url"],
           "image_url": rec["image_url"], "author": rec["author"],
           "license": rec["license"], "license_url": rec["license_url"],
           "retrieved": retrieved, "sha256": sha, "file": dest.name}
    entry = {
        "file": dest.name,
        # Phase 4e: a review alt text (photo_review.json) wins over the
        # Commons description, as it does for the city photographs
        "alt": REVIEW_ALTS.get(("stat", fid)) or (
            rec["description"][:160].rstrip() if rec["description"] else None),
        "author": rec["author"], "license": rec["license"],
        "license_url": rec["license_url"],
        "source_url": rec["source_url"],
        "title": title_of(rec["source_url"]),
        "cropped": CROPPED["stat"],
    }
    return row, entry


def external_suffix(image_url: str) -> str:
    """The file extension a pinned outside photograph is saved under."""
    suffix = "." + image_url.split("?")[0].rsplit(".", 1)[-1].lower()
    suffix = {".jpeg": ".jpg"}.get(suffix, suffix)
    return suffix if suffix in (".jpg", ".png", ".webp") else ".jpg"


def source_external(fid: str, ext: dict, retrieved: str,
                    page: str = "stat") -> tuple[dict, dict | None]:
    """A photograph from outside Commons, as the review records it — a stat
    page's (2026-10-07) or, after the Phase 5 report (Nathan, 2026-10-08:
    the most representative photograph of each city, from any source), a
    city's: the file on disk must be exactly the recorded bytes (sha256) —
    a file already there under the page's name is replaced unless it is —
    fetched from the record's image link, or its archived copy."""
    suffix = external_suffix(ext["image_url"])
    dest = WEB / "public" / ("stats" if page == "stat" else "cities") / f"{fid}{suffix}"
    if not (dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == ext["sha256"]):
        for url in (ext["image_url"], ext.get("fallback_image_url")):
            if not url:
                continue
            try:
                r = requests.get(url, headers=UA, timeout=120)
                r.raise_for_status()
            except Exception:  # noqa: PERF203
                continue
            if hashlib.sha256(r.content).hexdigest() == ext["sha256"]:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)
                break
        else:
            return {page: fid, "status": "external_file_unavailable"}, None
    row = {page: fid, "status": "ok", "page_title": None, "file_title": None,
           "source_url": ext["source_url"], "image_url": ext["image_url"],
           "author": ext["author"], "license": ext["license"],
           "license_url": ext.get("license_url"), "retrieved": retrieved,
           "sha256": ext["sha256"], "file": dest.name}
    entry = {"file": dest.name, "alt": ext["alt"], "author": ext["author"],
             "license": ext["license"], "license_url": ext.get("license_url"),
             "source_url": ext["source_url"], "title": ext["title"],
             "cropped": CROPPED[page]}
    return row, entry


def stats_only(fids: list[str]) -> None:
    """Phase 4e: re-source the named stat pages only — their manifest rows
    and render entries are rewritten, every other row and entry (the 387
    city photographs, the other stat pages) is left exactly as committed.
    A page new to STAT_SUBJECTS gains a row."""
    retrieved = time.strftime("%Y-%m-%d")
    csv_path = P2E / "stat_images.csv"
    json_path = WEB / "src" / "data" / "stat-images.json"
    rows = pd.read_csv(csv_path, dtype=str, keep_default_na=False).to_dict("records")
    render = json.loads(json_path.read_text())
    for fid in fids:
        row, entry = source_stat(fid, STAT_SUBJECTS[fid], retrieved)
        old = next((r for r in rows if r["stat"] == fid), None)
        if old is not None and old.get("status") == "ok" and old.get("file") \
                and old["file"] != row.get("file"):
            stale = WEB / "public" / "stats" / old["file"]
            if stale.exists():
                stale.unlink()
        cols = list(rows[0])
        full = {c: row.get(c, "") if row.get(c) is not None else "" for c in cols}
        if old is None:
            rows.append(full)
        else:
            rows[rows.index(old)] = full
        render.pop(fid, None)
        if entry:
            render[fid] = entry
        print(f"{fid}: {row['status']} {row.get('file_title', '')}")
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(render, indent=0, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    P2E.mkdir(parents=True, exist_ok=True)
    cm = pd.read_csv(RESULTS / "phase2c" / "city_meta.csv", dtype={"cbsa": str})
    retrieved = time.strftime("%Y-%m-%d")

    rows, render, reasons = [], {}, {}
    for n, (_, m) in enumerate(cm.iterrows()):
        city = m["display_name_full"].split(",")[0].strip()
        state = m["state_full"]
        # after the Phase 5 report: a city photograph from outside Commons,
        # pinned by its bytes in the review
        ext = REVIEW_EXTERNAL.get(("city", m["slug"]))
        if ext:
            row, entry = source_external(m["slug"], ext, retrieved, page="city")
            rows.append({"cbsa": m["cbsa"], "slug": m["slug"], **{k: v for k, v in row.items() if k != "city"}})
            if entry:
                render[m["slug"]] = entry
            else:
                reasons[row["status"]] = reasons.get(row["status"], 0) + 1
            continue
        pin = REVIEW_PINNED.get(("city", m["slug"]))
        rec, reason = source_file(pin) if pin else source_one([f"{city}, {state}", city])
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
        alt = REVIEW_ALTS.get(("city", m["slug"])) or (
            rec["description"][:160].rstrip() if rec["description"] else "")
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
            # Phase 4 (ADR 0012): the credit's title, and whether the
            # layout crops it (city photographs scale, never crop)
            "title": title_of(rec["source_url"]),
            "cropped": CROPPED["city"],
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
        row, entry = source_stat(fid, cands, retrieved)
        stat_rows.append(row)
        if entry:
            stat_render[fid] = entry
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
    import sys
    if sys.argv[1:2] == ["--stats"]:
        stats_only(sys.argv[2:])
    else:
        main()
