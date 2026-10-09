"""Credit audit (after Phase 6 I): does each photograph's credit name the
photograph's own licence and author, as its Commons file page states them?

Why: city_images.clear_licence reads a Commons file's licence and author from
imageinfo extmetadata (LicenseShortName, Artist), and nearly every Commons
credit the site shows came that way — the pipeline's, the hero's, and the
photographs Phase 5 pinned (results/phase5/card_photos_apply.py ran
clear_licence on the cached imageinfo); Phase 6's eleven pins took theirs
from each page's licence section (picks.json; corrected after the run, which
first said Phase 6's pins came through clear_licence too). For a photograph
of an old artwork the file page carries
two licences — the artwork's ({{PD-old}}) and the photograph's
({{self|cc-by-sa-4.0}}) — and the metadata reported the artwork's:
File:Jackson_Square.jpg came back "Public domain", "Clark Mills" (the 1856
statue's sculptor) where the photograph is CC BY-SA 4.0 by Daniel Schwen.
Phase 6 corrected that one by hand (ADR 0012, Phase 6 amendment). This audit
reads every credited Commons file's own page.

Rules, committed before the measurement they decide:
  1. Scope: every entry of web/src/data/city-images.json, stat-images.json
     and hero.json. An entry whose source_url is not a Commons file page is
     listed, not audited (the photo review pins its credit with its own
     licence evidence).
  2. Fetch: the file page's current wikitext from commons.wikimedia.org
     (action=query, prop=revisions, rvprop=content|ids|timestamp,
     rvslots=main, redirects) through city_images._get_json — so cached
     under data/raw/wiki_images, with the pipeline's user agent (no email) —
     at least PAUSE seconds between uncached calls (Commons allows this
     machine about ten a minute). A call that still fails after the
     fetcher's own retries waits a minute and tries once more, then is
     listed as unfetched. A redirect is followed and recorded.
  3. Flag a file whose page uses an artwork description template
     ({{Artwork}}, {{Art Photo}}, {{Painting}}, {{Object photo}}) or grants
     more than one licence. Licences are counted after unwrapping {{self}},
     {{self2}}, {{Multi-license}}, {{Dual-license}} and {{Licensed-PD-Art}}
     (so {{self|GFDL|cc-by-sa-3.0}} grants two, a dual licence by one
     holder); {{PD-Art|...}} counts once. A licence tag is a template named
     cc-*, CC0, PD-*, GFDL*, FAL, Attribution* or Copyrighted free use*,
     anywhere on the page (the licence section, or a description
     template's permission field).
  4. Whose licence: a licence inside {{self}}/{{self2}}, an {{Art Photo}}
     |photo license=, or the last tag of {{Licensed-PD-Art}} is the
     photograph's; one inside |artwork license= or the earlier tags of
     {{Licensed-PD-Art}} is the artwork's. A free licence (cc-*, CC0, GFDL,
     FAL, Attribution, Copyrighted free use) and a PD tag about the file
     itself (PD-self, PD-user, PD-author, PD-ineligible, PD-shape,
     PD-textlogo, PD-simple, PD-because, PD-*Gov*) are the photograph's.
     {{PD-Art}} is the photograph's (a faithful reproduction of a
     public-domain flat work; the reproduction carries no new copyright).
     Any other PD tag (PD-old*, PD-US*, PD-1923, PD-anon*, PD-scan, ...)
     concerns an old work: it is the artwork's when the page also grants
     the photograph a licence, and the photograph's when it is all the page
     grants (an old photograph, or a reproduction).
  5. Whose author (the photograph's): an {{Art Photo}} |photographer=; else
     {{self}}'s |author=; else the attribution a photograph licence names
     ({{cc-by-sa-4.0|Name}}); else the description template's author —
     {{Information}} |author=, {{Photograph}} |photographer=, {{Artwork}}
     |photographer=, or {{Artwork}} |author= when it differs from |artist=;
     else a "Photo by Name" in the source field; else the uploader (the
     page's first revision's user, one more cached call). The artwork's
     creator is {{Artwork}}/{{Art Photo}} |artist= (or {{Artwork}} |author=
     with no |artist=).
  6. Compare (flagged files): the licence agrees when the manifest's
     licence is one the page grants the photograph (names normalised:
     "CC BY-SA 4.0" = {{cc-by-sa-4.0}}, "Public domain" = any PD tag,
     {{Cc-by-sa-3.0-migrated}} = CC BY-SA 3.0, {{cc-by-sa-all}} = its four
     versions). The author agrees when the manifest's author and the
     photograph's author share a name word of three or more letters
     (wiki markup stripped, accents folded, generic words such as "user",
     "photo", "own", "work", "unknown" dropped), or, having none, read the
     same ("Unknown" = "Unknown"); under {{PD-Art}} with a
     public-domain credit the artwork's creator is accepted too (a faithful
     reproduction's only author). A mismatch is a flagged file where either
     disagrees; its evidence is the licence section's text (categories and
     image notes removed) and the description template's fields, at the
     revision read.
  7. Unflagged files: the manifest's licence is checked against the page's
     one licence too, and any disagreement listed apart, outside the rule.

After the run (9 October 2026), changing no rule: READINGS records what each
file the rules listed shows on a closer look (the templates it uses, read
through the same cached call), with a verdict; every photograph credited
public domain is listed with its licence text, read for a second licence the
rules could not see; and each flagged file says whether the photograph's own
licence is on the site's list, the credit its page supports, and where a
correction would go.

Nothing here changes a manifest, the photo review or a photograph.

    PYTHONPATH=. .venv/bin/python atlas/results/phase6/credit_audit.py

writes results/phase6/credit_audit.json.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from atlas.pipeline.build import city_images as CI  # noqa: E402
from atlas.pipeline.build import photo_review as PR  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC_DATA = ROOT / "atlas" / "web" / "src" / "data"
OUT = HERE / "credit_audit.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PAUSE = 6.0

ARTWORK_TEMPLATES = {"artwork", "art photo", "painting", "object photo"}
DESCRIPTION_TEMPLATES = ARTWORK_TEMPLATES | {"information", "photograph"}
WRAPPERS = {"self", "self2", "multi-license", "dual-license"}
LICENCE = re.compile(r"^(cc-.+|cc0|pd-.+|gfdl(-.+)?|fal|free-art-licen[cs]e|attribution(-.+)?"
                     r"|copyrighted-free-use(-.+)?|licensed-pd-art(-two)?|self2?|multi-license"
                     r"|dual-license)$")
OWN_PD = re.compile(r"^pd-(self|user|author|ineligible|shape|textlogo|simple|because)|^pd-.*gov")
PD_ART = re.compile(r"^pd-art")
GENERIC = {"user", "users", "talk", "photo", "photos", "photograph", "photographer", "photographed",
           "picture", "image", "own", "work", "the", "and", "from", "with", "for", "flickr", "commons",
           "wikimedia", "wikipedia", "uploaded", "uploader", "author", "creator", "sculptor",
           "painter", "artist", "contribs", "contributions", "http", "https", "www", "com", "org",
           "net", "unknown", "anonymous", "taken", "by"}


# ---- fetching ---------------------------------------------------------------

def _key(params: dict) -> str:
    """city_images._get_json's cache key for a Commons call."""
    return hashlib.sha256((COMMONS_API + json.dumps(params, sort_keys=True)).encode()).hexdigest()[:20]


_last_call = [0.0]


def commons(params: dict) -> dict | None:
    """One Commons API answer through the pipeline's cache; an uncached call
    keeps PAUSE seconds from the previous one."""
    if (CI.CACHE / f"{_key(params)}.json").exists():
        return CI._get_json(COMMONS_API, params)
    for attempt in range(2):
        time.sleep(max(0.0, PAUSE - (time.monotonic() - _last_call[0])))
        d = CI._get_json(COMMONS_API, params)
        _last_call[0] = time.monotonic()
        if d is not None:
            return d
        if attempt == 0:
            time.sleep(60)
    return None


def wikitext_params(title: str) -> dict:
    return {"action": "query", "titles": title, "prop": "revisions",
            "rvprop": "content|ids|timestamp", "rvslots": "main",
            "redirects": 1, "format": "json", "formatversion": 2}


def uploader_params(title: str) -> dict:
    return {"action": "query", "titles": title, "prop": "revisions",
            "rvprop": "user|timestamp|ids", "rvlimit": 1, "rvdir": "newer",
            "format": "json", "formatversion": 2}


def page_of(d: dict | None) -> dict | None:
    pages = ((d or {}).get("query") or {}).get("pages") or []
    return pages[0] if pages else None


# ---- wikitext ---------------------------------------------------------------

def _scan(text: str):
    """(index, token, template depth, link depth) for each {{ }} [[ ]] and |,
    with the depths before the token."""
    t = l = 0
    i = 0
    while i < len(text):
        two = text[i:i + 2]
        if two == "{{":
            yield i, two, t, l
            t += 1
            i += 2
        elif two == "}}" and t:
            t -= 1
            yield i, two, t, l
            i += 2
        elif two == "[[":
            yield i, two, t, l
            l += 1
            i += 2
        elif two == "]]" and l:
            l -= 1
            yield i, two, t, l
            i += 2
        else:
            if text[i] in "|=":
                yield i, text[i], t, l
            i += 1


def top_templates(text: str) -> list[tuple[int, int]]:
    """Spans of the outermost {{...}} in text."""
    spans, start = [], None
    for i, tok, t, _ in _scan(text):
        if tok == "{{" and t == 0:
            start = i
        elif tok == "}}" and t == 0 and start is not None:
            spans.append((start, i + 2))
            start = None
    return spans


def parse_template(raw: str) -> dict:
    """{{name|a|k=v}} -> {"name", "params" (positional keys "1", "2", ...), "raw"}."""
    inner = raw[2:-2]
    cuts = [i for i, tok, t, l in _scan(inner) if tok == "|" and t == 0 and l == 0]
    parts, prev = [], 0
    for c in cuts + [len(inner)]:
        parts.append(inner[prev:c])
        prev = c + 1
    name = re.sub(r"\s+", " ", parts[0].replace("_", " ")).strip()
    name = re.sub(r"^template:", "", name, flags=re.IGNORECASE)
    params, pos = {}, 0
    for p in parts[1:]:
        eq = next((i for i, tok, t, l in _scan(p) if tok == "=" and t == 0 and l == 0), None)
        if eq is None:
            pos += 1
            params[str(pos)] = p.strip()
        else:
            params[re.sub(r"\s+", " ", p[:eq].replace("_", " ")).strip().lower()] = p[eq + 1:].strip()
    return {"name": name, "key": name.lower(), "params": params, "raw": raw}


def all_templates(text: str, parent: str | None = None, field: str | None = None) -> list[dict]:
    """Every template on the page, outermost first, each with the template
    and field it sits in."""
    out = []
    for a, b in top_templates(text):
        tp = parse_template(text[a:b])
        tp["parent"], tp["field"] = parent, field
        out.append(tp)
        for k, v in tp["params"].items():
            out.extend(all_templates(v, tp["key"], k))
    return out


def tag_key(name: str) -> str:
    return unicodedata.normalize("NFKC", name).strip().lower().replace("_", "-").replace(" ", "-")


def is_licence(name: str) -> bool:
    return bool(LICENCE.match(tag_key(name)))


def norm_licence(s: str | None) -> list[str]:
    """The licence keys a Commons tag ("Cc-by-sa-3.0,2.5,2.0,1.0",
    "Cc-by-sa-3.0-migrated", "PD-old-70") or a manifest's licence ("CC BY-SA
    4.0", "Public domain", "CC BY 3.0 us") stands for."""
    t = tag_key(s or "")
    if not t:
        return []
    if t in ("public-domain", "pd", "public-domain-mark") or t.startswith("pd-"):
        return ["pd"]
    if t in ("cc0", "cc-zero", "cc0-1.0", "cc-0"):
        return ["cc0"]
    if t in ("fal", "free-art-license", "free-art-licence"):
        return ["fal"]
    for fam in ("gfdl", "attribution", "copyrighted-free-use"):
        if t.startswith(fam):
            return [fam]
    m = re.match(r"^cc-(by(?:-sa)?)-(all|[\d.,]+)(.*)$", t)
    if m:
        kind, vers, rest = m.groups()
        rest = re.sub(r"-migrated.*$|-with-disclaimers$", "", rest)
        versions = ["1.0", "2.0", "2.5", "3.0"] if vers == "all" else [v for v in vers.split(",") if v]
        return [f"cc-{kind}-{v}{rest}" for v in versions]
    return [t]


def strip_markup(s: str | None) -> str:
    """Wiki markup to plain text, for names: [[User:X|Y]] -> Y, [url Y] -> Y,
    {{Creator:Y}} -> Y, {{U|Y}} -> Y, other templates dropped."""
    s = re.sub(r"<!--.*?-->", "", s or "", flags=re.S)
    for _ in range(4):
        s = re.sub(r"\{\{\s*[Cc]reator\s*:\s*([^{}|]+)\}\}", r"\1", s)
        s = re.sub(r"\{\{\s*(?:[Uu]ser|[Uu]|[Uu]ser link)\s*\|\s*([^{}|]+)[^{}]*\}\}", r"\1", s)
        s = re.sub(r"\{\{\s*[a-z]{2,3}(?:-[a-z]+)?\s*\|\s*(?:1\s*=\s*)?([^{}]*)\}\}", r"\1", s)
        s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[(?:https?:)?//\S+\s+([^\]]*)\]", r"\1", s)
    s = re.sub(r"\[(?:https?:)?//\S+\]", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip(" ,;:-")


def name_words(s: str | None) -> set[str]:
    t = unicodedata.normalize("NFKD", strip_markup(s)).encode("ascii", "ignore").decode().lower()
    return {w for w in re.findall(r"[a-z0-9]+", t) if len(w) >= 3 and w not in GENERIC}


def licence_section(text: str) -> str:
    """The licence section's text: from its heading to the next heading,
    without categories or image notes."""
    heads = list(re.finditer(r"^(=+)\s*(.*?)\s*\1\s*$", text, flags=re.M))
    for n, h in enumerate(heads):
        if re.search(r"licen[cs]|license-header", h.group(2), flags=re.IGNORECASE):
            end = next((x.start() for x in heads[n + 1:] if len(x.group(1)) <= len(h.group(1))),
                       len(text))
            body = text[h.start():end]
            body = re.sub(r"\{\{\s*ImageNote\s*\|.*?\{\{\s*ImageNoteEnd[^}]*\}\}", "", body,
                          flags=re.S | re.IGNORECASE)
            body = re.sub(r"\[\[\s*Category\s*:[^\]]*\]\]", "", body, flags=re.IGNORECASE)
            return re.sub(r"\n{3,}", "\n\n", body).strip()
    return ""


def licences_of(tps: list[dict]) -> list[dict]:
    """The licences the page grants, unwrapped, each with whose it is when
    the tag says (role "photograph"/"artwork") or None."""
    out = []
    for tp in tps:
        k = tag_key(tp["name"])
        if not is_licence(tp["name"]):
            continue
        if tp["parent"] in WRAPPERS or tp["parent"] in ("licensed-pd-art", "licensed-pd-art-two"):
            continue  # a tag written as a template inside a wrapper: the wrapper counts it
        field = (tp["field"] or "").lower()
        role = ("artwork" if "artwork licen" in field else
                "photograph" if "photo licen" in field else None)
        if k in WRAPPERS:
            pos = [v for kk, v in tp["params"].items() if kk.isdigit() and v.strip()]
            for v in pos:
                out.append({"tag": tp["name"] + "|" + v.strip(), "keys": norm_licence(v),
                            "role": "photograph", "holder": tp["params"].get("author"),
                            "attribution": None, "raw": tp["raw"]})
            continue
        if k.startswith("licensed-pd-art"):
            pos = [v for kk, v in tp["params"].items() if kk.isdigit() and v.strip()]
            for i, v in enumerate(pos):
                out.append({"tag": tp["name"] + "|" + v.strip(), "keys": norm_licence(v),
                            "role": "photograph" if i == len(pos) - 1 else "artwork",
                            "holder": None, "attribution": None, "raw": tp["raw"]})
            continue
        attribution = None
        if k.startswith("cc-by") or k.startswith("attribution"):
            attribution = tp["params"].get("attribution") or tp["params"].get("1")
        if role is None:
            if not k.startswith("pd-") or OWN_PD.match(k) or PD_ART.match(k):
                role = "photograph"
        out.append({"tag": tp["name"], "keys": norm_licence(tp["name"]), "role": role,
                    "holder": None, "attribution": attribution, "raw": tp["raw"]})
    granted_to_photo = any(x["role"] == "photograph" for x in out)
    for x in out:
        if x["role"] is None:  # an old work's PD tag (rule 4)
            x["role"] = "artwork" if granted_to_photo else "photograph"
    return out


def describe(tps: list[dict]) -> dict | None:
    """The page's description template (the first outermost one)."""
    return next((tp for tp in tps if tp["parent"] is None and tp["key"] in DESCRIPTION_TEMPLATES),
                None)


def photographer(desc: dict | None, lic: list[dict], tps: list[dict]) -> tuple[str | None, str]:
    """(the photograph's author as the page names it, where it says so)
    — rule 5, without the uploader step."""
    p = (desc or {}).get("params", {})
    k = (desc or {}).get("key")
    if k == "art photo" and strip_markup(p.get("photographer")):
        return p["photographer"], "{{Art Photo}} |photographer="
    for x in lic:
        if x["role"] == "photograph" and x["holder"] and strip_markup(x["holder"]):
            return x["holder"], "{{self}} |author="
    for x in lic:
        if x["role"] == "photograph" and x["attribution"] and strip_markup(x["attribution"]):
            return x["attribution"], f"the attribution in {{{{{x['tag']}}}}}"
    if k in ("information",) and strip_markup(p.get("author")):
        return p["author"], "{{Information}} |author="
    if k == "photograph" and strip_markup(p.get("photographer") or p.get("author")):
        return p.get("photographer") or p.get("author"), "{{Photograph}} |photographer="
    if k in ARTWORK_TEMPLATES:
        if strip_markup(p.get("photographer")):
            return p["photographer"], f"{{{{{desc['name']}}}}} |photographer="
        if strip_markup(p.get("author")) and p.get("artist") and \
                name_words(p.get("author")) != name_words(p.get("artist")):
            return p["author"], f"{{{{{desc['name']}}}}} |author= (beside |artist=)"
    src = strip_markup(p.get("source"))
    m = re.search(r"(?i)\bphoto(?:graph)?(?:ed)?\s*(?:by|:)\s*([^,;(\n]+)", src or "")
    if m and name_words(m.group(1)):
        return m.group(1).strip(), "the source field (\"Photo by …\")"
    return None, ""


def artwork_creator(desc: dict | None) -> str | None:
    if not desc or desc["key"] not in ARTWORK_TEMPLATES:
        return None
    p = desc["params"]
    return p.get("artist") or p.get("author") or None


# ---- for Nathan's decision (reported, not rules) -------------------------------

def display_licence(k: str) -> str:
    """A licence key in the manifests' own style: "CC BY-SA 4.0", "CC BY 3.0 us"."""
    m = re.match(r"^cc-(by(?:-sa)?)-([\d.]+)(?:-(\w+))?$", k)
    if m:
        kind, v, port = m.groups()
        return f"CC {kind.upper()} {v}" + (f" {port}" if port else "")
    return {"pd": "Public domain", "cc0": "CC0", "fal": "Free Art License", "gfdl": "GFDL"}.get(k, k)


def licence_link(k: str) -> str | None:
    m = re.match(r"^cc-(by(?:-sa)?)-([\d.]+)(?:-(\w+))?$", k)
    if m:
        kind, v, port = m.groups()
        return f"https://creativecommons.org/licenses/{kind}/{v}" + (f"/{port}" if port else "")
    return {"cc0": "https://creativecommons.org/publicdomain/zero/1.0/"}.get(k)


def on_the_list(k: str) -> bool:
    """Public domain, CC0, CC BY or CC BY-SA, nothing NC or ND — the rule
    clear_licence applies (city_images.ALLOW / REFUSE)."""
    return bool(CI.ALLOW.match(k)) and not CI.REFUSE.search(k)


def where_to_correct(row: dict, pinned: dict) -> str:
    if (row["page"], row["key"]) in pinned:
        return ("its pinned record in results/phase4/photo_review.json external_files "
                "(author, license, license_url), then the review's apply step — the way "
                "Phase 6 corrected New Orleans; a clear_licence change never reaches a pin")
    if row["page"] == "hero":
        return "hero_image.py, re-run after a clear_licence that prefers the photograph's licence"
    if row["page"] == "stat":
        return (f"city_images.py --stats {row['key']}, re-run after a clear_licence that prefers "
                "the photograph's licence (or a pin with the page's credit)")
    return ("the photo pipeline (city_images.py, then the photo review's apply step), re-run "
            "after a clear_licence that prefers the photograph's licence (or a pin with the "
            "page's credit)")


# Readings after the run (not rules, which stand as committed): what each file
# the rules listed shows on a closer look, by its title. The templates they
# cite were read on 9 October 2026 through the same cached call.
WRONG = "credit wrong"
FALSE_ALARM = "credit right (a false alarm of the rules)"
UNNAMED_TAG = "credit right (a licence tag the rules do not name)"
_UNSPLASH = ("{{Unsplash}} transcludes {{Cc-zero}}: CC0, as credited (the photograph dates from "
             "2016, before Unsplash's own licence replaced CC0 in June 2017). Rule 3's tag list "
             "does not name {{Unsplash}}.")
_BARERA = ("{{User:Michael Barera/license}} ('/License' redirects to it) is {{self|cc-by-sa-4.0|"
           "attribution=Michael Barera}}, with CC BY-SA 3.0 and GFDL offered too: CC BY-SA 4.0 by "
           "Michael Barera, as credited. Rule 3 does not read inside a user's licence template.")
_MIGRATION = ("migration=relicense on the GFDL tag: under Wikimedia's 2009 licence migration the "
              "page also grants CC BY-SA 3.0, the credit's licence. Rule 6 does not expand the "
              "migration parameter.")
READINGS: dict[str, dict] = {
    "File:Thomas_Cole's_\"The_Picnic\",_Brooklyn_Museum_IMG_3787.JPG": {
        "verdict": WRONG,
        "note": ("The page licenses the 1846 painting public domain ({{PD-old-100-1923}}) and the "
                 "photograph CC BY 3.0 by its photographer ({{self|cc-by-3.0}}; source 'Photo by "
                 "Billy Hathorn, 7-23-2011'); the credit took the painting's licence and its "
                 "painter. The photograph is a tight, frameless shot of a flat painting, and in "
                 "the US a faithful copy of a public-domain flat work carries no new copyright "
                 "(the position behind Commons' {{PD-Art}}), so 'Public domain' is defensible "
                 "there; but the page claims no {{PD-Art}}: it grants CC BY 3.0, a licence on "
                 "the site's list, and that credit is the page's own. As CC BY 3.0 it would join "
                 "the photographs under a Creative Commons licence before 4.0 "
                 "(photo_credits.json cc_before_4_0).")},
    "File:Bienvenidos,_Eagle_Pass,_TX_IMG_0442.JPG": {
        "verdict": FALSE_ALARM,
        "note": "{{Self|GFDL|Cc-by-sa-2.5,2.0,1.0|migration=relicense|...}}: " + _MIGRATION},
    "File:Punta_Gorda_City_Hall.jpg": {
        "verdict": FALSE_ALARM,
        "note": "{{GFDL|migration=relicense}} and {{GFDL-self|migration=relicense}}: " + _MIGRATION},
    "File:Goingtovic.jpg": {
        "verdict": FALSE_ALARM,
        "note": ("The photographer is named by {{user at project|Justin65656|wikipedia|en}} "
                 "({{self}} |author= and the description), which rule 5's markup stripping drops, "
                 "so it fell back to the uploader, the transfer bot. The page's photographer, "
                 "Justin65656 at English Wikipedia, is the credit's author; the licence (CC BY-SA "
                 "3.0, offered beside GFDL and 2.5 to 1.0) agrees.")},
    "File:1_times_square_night_2013.jpg": {
        "verdict": FALSE_ALARM,
        "note": ("{{self|GFDL|cc-by-sa-all|migration=redundant}}: Template:Cc-by-sa-all now "
                 "redirects to {{Cc-by-sa-4.0,3.0,2.5,2.0,1.0}}, so the page grants CC BY-SA 4.0, "
                 "the credit's licence; rule 6 took 'all' as the four versions before 4.0. The "
                 "photographer chose 'all versions' in April 2013, before 4.0 was published "
                 "(November 2013): 3.0 is the version certainly chosen then, and the page as it "
                 "stands offers 4.0 too.")},
    "File:Boulder,_United_States_(Unsplash_IPvSZvM5Elg).jpg": {"verdict": UNNAMED_TAG,
                                                               "note": _UNSPLASH},
    "File:Honolulu_cityscape.jpg": {"verdict": UNNAMED_TAG, "note": _UNSPLASH},
    "File:Vineyard_and_hills_(Unsplash).jpg": {"verdict": UNNAMED_TAG, "note": _UNSPLASH},
    "File:Crew_2016-01-10_(Unsplash_xCmvrpzctaQ).jpg": {"verdict": UNNAMED_TAG, "note": _UNSPLASH},
    "File:University_of_Arkansas_May_2017_07_(Old_Main).jpg": {"verdict": UNNAMED_TAG,
                                                               "note": _BARERA},
    "File:Janesville_June_2024_105_(Town_Square).jpg": {"verdict": UNNAMED_TAG, "note": _BARERA},
    "File:San_Angelo_September_2019_03_(San_Angelo_City_Hall).jpg": {"verdict": UNNAMED_TAG,
                                                                     "note": _BARERA},
    "File:Texarkana_April_2016_002_(Texarkana_Texas_City_Hall).jpg": {"verdict": UNNAMED_TAG,
                                                                      "note": _BARERA},
    "File:Tyler_May_2016_42_(People's_Petroleum_Building_and_Plaza_Tower).jpg": {
        "verdict": UNNAMED_TAG, "note": _BARERA},
    "File:Greenville,_North_Carolina_-_2026_9.jpg": {
        "verdict": UNNAMED_TAG,
        "note": ("{{PDAF}} redirects to {{PD-author-FlickrPDM}}: the author marked the photograph "
                 "public domain on Flickr (FlickreviewR: Public Domain Mark), as credited. Rule "
                 "3's tag list does not name PDAF.")},
    "File:Gfp-florida-daytona-beach-building-on-the-ocean.jpg": {
        "verdict": UNNAMED_TAG,
        "note": ("{{cc-pd}} (in the description's permission field) is Creative Commons' retired "
                 "Public Domain Dedication; its short name is 'Public Domain', as credited. Rule "
                 "6 does not count it a public-domain tag.")},
    "File:Drake_Park,_Mirror_Pond,_Bend_-_DPLA_-_abff0ea08438d6effa849247b6bbdfeb.jpg": {
        "verdict": UNNAMED_TAG,
        "note": ("{{DPLA metadata}} renders the file's structured data, which the wikitext does "
                 "not hold: copyright licence (P275) Q20007257, CC BY 4.0; creator 'Gary "
                 "Halvorson, Oregon State Archives' (read through wbgetentities) — as credited.")},
}


# ---- the audit ---------------------------------------------------------------

def credited() -> list[dict]:
    city = json.loads((SRC_DATA / "city-images.json").read_text())
    stat = json.loads((SRC_DATA / "stat-images.json").read_text())
    hero = json.loads((SRC_DATA / "hero.json").read_text())
    rows = [{"page": "city", "key": k, **v} for k, v in sorted(city.items())]
    rows += [{"page": "stat", "key": k, **v} for k, v in sorted(stat.items())]
    rows += [{"page": "hero", "key": "hero", **hero}]
    return rows


def file_title(source_url: str | None) -> str | None:
    u = urllib.parse.urlparse(source_url or "")
    if u.netloc != "commons.wikimedia.org" or not u.path.startswith("/wiki/"):
        return None
    t = urllib.parse.unquote(u.path[len("/wiki/"):])
    return t if t.startswith("File:") else None


def credit_from(row: dict, pinned: dict) -> str:
    """Where the credit was written (where a correction would go)."""
    ext = pinned.get((row["page"], row["key"]))
    if ext:
        return f"pinned in results/phase4/photo_review.json external_files ({ext.get('date')})"
    if row["page"] == "hero":
        return "hero_image.py through clear_licence"
    return "city_images.py through clear_licence (the last pipeline run)"


def agrees_author(manifest_author: str | None, accepted: list[str | None]) -> bool:
    """Rule 6; two credits with no name word ("Unknown") agree when they
    read the same."""
    mine = name_words(manifest_author)
    plain = strip_markup(manifest_author).lower()
    return any((mine & name_words(a)) or (plain and plain == strip_markup(a).lower())
               for a in accepted if a)


def audit_one(row: dict, title: str, pinned: dict) -> dict:
    d = commons(wikitext_params(title))
    pg = page_of(d)
    if not pg or pg.get("missing") or not pg.get("revisions"):
        return {"file": title, "status": "unfetched" if d is None else "missing"}
    rv = pg["revisions"][0]
    text = rv["slots"]["main"].get("content", "")
    clean = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    tps = all_templates(clean)
    desc = describe(tps)
    lic = licences_of(tps)
    artwork_tpl = sorted({tp["name"] for tp in tps if tp["key"] in ARTWORK_TEMPLATES})
    flagged = bool(artwork_tpl) or len(lic) > 1
    photo_keys = sorted({k for x in lic if x["role"] == "photograph" for k in x["keys"]})
    art_keys = sorted({k for x in lic if x["role"] == "artwork" for k in x["keys"]})
    manifest_keys = norm_licence(row.get("license"))
    rec = {
        "file": title,
        "page": row["page"], "key": row["key"],
        "redirected_to": ((d["query"].get("redirects") or [{}])[0]).get("to"),
        "credit_from": credit_from(row, pinned),
        "manifest": {"license": row.get("license"), "author": row.get("author"),
                     "license_url": row.get("license_url")},
        "flagged": flagged,
        "why_flagged": ([f"{{{{{n}}}}}" for n in artwork_tpl] +
                        ([f"{len(lic)} licences: " + ", ".join("{{" + x["tag"] + "}}" for x in lic)]
                         if len(lic) > 1 else [])),
        "licences": [{"tag": x["tag"], "whose": x["role"]} for x in lic],
        "photograph_licences": photo_keys,
        "artwork_licences": art_keys,
        "licence_agrees": bool(set(manifest_keys) & set(photo_keys)),
        "revision": {"revid": rv.get("revid"), "timestamp": rv.get("timestamp")},
    }
    fields = {}
    if desc:
        for f in ("artist", "author", "photographer", "source", "permission", "date",
                  "artwork license", "photo license"):
            if desc["params"].get(f):
                fields[f] = desc["params"][f][:400]
    rec["evidence"] = {
        "licence_section": licence_section(clean)[:4000],
        "description_template": "{{" + desc["name"] + "}}" if desc else None,
        "description_fields": fields,
    }
    rec["reading"] = READINGS.get(title)
    if not flagged:
        return rec
    who, said = photographer(desc, lic, tps)
    if not who:
        up = page_of(commons(uploader_params(pg["title"])))
        first = ((up or {}).get("revisions") or [{}])[0]
        who, said = first.get("user"), "the uploader (the page's first revision)"
    creator = artwork_creator(desc)
    accepted = [who]
    if any(PD_ART.match(tag_key(x["tag"].split("|")[-1])) for x in lic) and manifest_keys == ["pd"]:
        accepted.append(creator)
    in_order = [k for x in lic if x["role"] == "photograph" for k in x["keys"]]
    listed = [k for k in dict.fromkeys(in_order) if on_the_list(k)]
    listed = [k for k in manifest_keys if k in listed] + [k for k in listed if k not in manifest_keys]
    rec.update({
        "photograph_author": strip_markup(who) or None,
        "photograph_author_from": said,
        "artwork_creator": strip_markup(creator) or None,
        "author_agrees": agrees_author(row.get("author"), accepted),
    })
    # for Nathan's decision — not where a reading found the credit right (the
    # rules' own reading of such a page is what went wrong)
    if (READINGS.get(title) or {}).get("verdict") not in (FALSE_ALARM, UNNAMED_TAG):
        rec.update({
            "photograph_licence_on_the_list": bool(listed),
            "credit_the_page_supports": ({"author": strip_markup(who) or None,
                                          "license": display_licence(listed[0]),
                                          "license_url": licence_link(listed[0])}
                                         if listed else None),
            "where_to_correct": where_to_correct(row, pinned),
        })
    rec["reading"] = rec.pop("reading")
    rec["evidence"] = rec.pop("evidence")
    return rec


def main() -> None:
    rows = credited()
    pinned = PR.external_files()
    t0 = time.time()
    results, outside = [], []
    for n, row in enumerate(rows):
        title = file_title(row.get("source_url"))
        if not title:
            outside.append({"page": row["page"], "key": row["key"], "source_url": row.get("source_url"),
                            "license": row.get("license"), "author": row.get("author"),
                            "credit_from": credit_from(row, pinned)})
            continue
        results.append(audit_one(row, title, pinned))
        if (n + 1) % 25 == 0:
            print(f"  {n + 1}/{len(rows)} ({time.time() - t0:.0f} s)", flush=True)

    read = [r for r in results if "flagged" in r]
    flagged = [r for r in read if r["flagged"]]
    mismatches = [r for r in flagged if not (r["licence_agrees"] and r["author_agrees"])]
    agreeing = [{k: r[k] for k in ("file", "page", "key", "credit_from", "why_flagged", "manifest",
                                   "photograph_licences", "photograph_author",
                                   "photograph_author_from", "artwork_creator")}
                for r in flagged if r not in mismatches]
    unflagged = [r for r in read if not r["flagged"]]
    disagree = [r for r in unflagged if not r["licence_agrees"]]
    verdicts: dict[str, list[str]] = {}
    for r in mismatches + disagree:
        v = (r.get("reading") or {}).get("verdict", "not read")
        verdicts.setdefault(v, []).append(f"{r['page']}:{r['key']}")
    # after the run: every photograph credited public domain, for a second
    # licence the rules could not see (an old work's tag beside a licence of
    # the photograph's own in a form rule 3 does not name)
    pd_credits = [r for r in read if norm_licence(r["manifest"]["license"]) == ["pd"]]
    pd_layered = [f"{r['page']}:{r['key']}" for r in pd_credits if r["artwork_licences"]]
    wrong = verdicts.get(WRONG, [])
    finding = (
        f"{len(read)} Commons pages read, {len(flagged)} flagged; the rules found "
        f"{len(mismatches)} mismatches and {len(disagree)} unflagged licence disagreements. Read "
        f"closely, {len(wrong)} {'credit is' if len(wrong) == 1 else 'credits are'} wrong "
        f"({', '.join(wrong) or 'none'}): the photograph's own licence and photographer lost to "
        f"the depicted work's public-domain tag and its creator. "
        f"{len(verdicts.get(FALSE_ALARM, []))} are false alarms of the rules "
        f"({', '.join(verdicts.get(FALSE_ALARM, []))}) and "
        f"{len(verdicts.get(UNNAMED_TAG, []))} are licence tags the rules do not name, each "
        f"matching its credit. New Orleans, corrected by hand in Phase 6, agrees. Of the "
        f"{len(pd_credits)} photographs credited public domain, every page grants public domain "
        f"about the file itself except {', '.join(pd_layered) or 'none'}.")
    out = {
        "date": time.strftime("%Y-%m-%d"),
        "what": ("Each credited photograph's licence and author against its Commons file page "
                 "(after Phase 6 I). Rules: this script's docstring, committed before the run "
                 "(the commit 'Credit audit, the rules before the run'); the readings, the "
                 "public-domain check and the fields for Nathan's decision were added after it "
                 "and change no rule."),
        "finding": finding,
        "fetch": {"api": COMMONS_API, "params": wikitext_params("File:…"),
                  "user_agent": CI.UA["User-Agent"], "pause_s": PAUSE,
                  "cache": "data/raw/wiki_images (city_images._get_json)"},
        "why_the_metadata_disagrees": (
            "imageinfo's extmetadata comes from Commons' CommonsMetadata extension, which reduces "
            "a page's licences to one by priority — public domain 2000; a CC licence 1000, plus "
            "100 for BY over BY-SA, plus 10 x its version (LicenseParser::getLicensePriority, "
            "highest first) — and reads Artist from the description template's author row, which "
            "{{Artwork}} fills with the artist. A page that tags the depicted work public domain "
            "and the photograph CC so reports public domain and the artist, whatever licence the "
            "photograph carries: the photograph's licence is gone before clear_licence sees it."),
        "clear_licence": {
            "does_the_fix_belong_there": (
                "Yes: the preference (the photograph's licence over an old work's PD tag) belongs "
                "in clear_licence, the gate Commons credits pass — city_images source_one and "
                "source_file, hero_image.py and Phase 5's pinning script "
                "(results/phase5/card_photos_apply.py) all call it; Phase 6's pins took their "
                "credits from each page's licence section instead (picks.json), which is how New "
                "Orleans came out right. But extmetadata cannot carry what the preference needs, "
                "so clear_licence needs a second input: the file page's licence tags (this "
                "audit's cached wikitext call, one per file)."),
            "the_rule": (
                "Narrow, because the metadata read every other credit right: act only when the "
                "page pairs an old work's PD tag (PD-old*, PD-US*, PD-1923, ...) or an artwork "
                "template with a licence it grants the photograph itself ({{self}}, a CC or other "
                "free tag, {{Art Photo}} |photo license=, {{Licensed-PD-Art}}'s last tag). Then "
                "clear on the photograph's licence — refusing it when that licence is not on the "
                "list (GFDL alone, NC, ND) — and credit the photographer ({{self}} |author=, the "
                "description template's author beside |artist=, a 'Photo by' source, else the "
                "uploader), never the artwork's creator; otherwise keep the metadata's answer. A "
                "dual licence by one holder may keep the metadata's pick (each is the holder's "
                "offer)."),
            "the_care_it_needs": (
                "A broader rewrite from wikitext would have to model what this audit's rules "
                "tripped on, where the metadata already reads the rendered page correctly: the "
                "2009 licence migration (migration=relicense adds CC BY-SA 3.0), redirected tags "
                "({{cc-by-sa-all}} now includes 4.0), authors written as templates ({{user at "
                "project}}), users' own licence templates, {{Unsplash}}, {{PDAF}}, {{cc-pd}}, and "
                "pages whose licence lives only in structured data (DPLA)."),
            "the_hero_gate": (
                "hero_image.STRICT_PD (public domain or CC0 only, because the band crops) trusts "
                "clear_licence's answer; the same fix stops a CC BY-SA photograph of an old statue "
                "from passing it as public domain."),
            "what_it_does_not_reach": (
                "Credits already written. A pinned photograph (photo_review.json external_files) "
                "keeps its pin's credit on every re-run, so a mismatch there needs its record "
                "corrected, as New Orleans's was; a pipeline credit changes only when its page "
                "is re-sourced. Running this audit as a check after each photo change would "
                "catch the next one either way."),
        },
        "counts": {
            "credited_photographs": len(rows),
            "commons_files": len(results),
            "not_commons": len(outside),
            "read": len(read),
            "unfetched_or_missing": len(results) - len(read),
            "flagged": len(flagged),
            "flagged_artwork_template": sum(1 for r in flagged
                                            if any(w.startswith("{{") for w in r["why_flagged"])),
            "flagged_several_licences": sum(1 for r in flagged
                                            if any(w[0].isdigit() for w in r["why_flagged"])),
            "mismatches": len(mismatches),
            "mismatched_licence": sum(1 for r in mismatches if not r["licence_agrees"]),
            "mismatched_author": sum(1 for r in mismatches if not r["author_agrees"]),
            "unflagged_licence_disagrees": len(disagree),
            "read_after_the_run": {v: len(ks) for v, ks in sorted(verdicts.items())},
            "credited_public_domain": len(pd_credits),
        },
        "mismatches": mismatches,
        "flagged_agreeing": agreeing,
        "unflagged_licence_disagrees": [
            {k: r[k] for k in ("file", "page", "key", "credit_from", "manifest", "licences",
                               "photograph_licences", "revision", "reading", "evidence")}
            for r in disagree],
        "public_domain_credits": {
            "reading": (
                "Read after the run for a second licence the rules could not see (an old work's "
                "tag beside a licence of the photograph's own in a form rule 3 does not name): "
                "each page grants public domain about the file itself — the author's own release "
                "(PD-self, PD-user, PD-author, a Flickr public-domain mark, cc-pd), a US or "
                "California government work, or Carol M. Highsmith's gift to the Library of "
                "Congress (Indianapolis adds {{Pixabay}}, the re-poster's own 2017 terms, which "
                "ask nothing) — except " + (", ".join(pd_layered) or "none") + "."),
            "files": [{"file": r["file"], "page": r["page"], "key": r["key"],
                       "author": r["manifest"]["author"],
                       "licence_tags": [x["tag"] for x in r["licences"]],
                       "licence_text": (r["evidence"]["licence_section"]
                                        or r["evidence"]["description_fields"].get("permission")
                                        or "")[:300]}
                      for r in pd_credits],
        },
        "not_commons": outside,
        "unfetched_or_missing": [r for r in results if "flagged" not in r],
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["counts"], indent=1))


if __name__ == "__main__":
    main()
