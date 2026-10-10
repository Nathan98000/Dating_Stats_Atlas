"""A Commons file page, read for the photograph's own licence and author
(after the credit audit; Nathan, 10 October 2026).

imageinfo's extmetadata reduces a page's licences to one, ranking public
domain above any Creative Commons licence (CommonsMetadata's
LicenseParser::getLicensePriority), and takes its Artist from the
description template's author row, which {{Artwork}} fills with the artist.
So a photograph of an old artwork — {{PD-old}} for the statue beside
{{self|cc-by-sa-4.0}} for the photograph — comes back "Public domain" by the
sculptor (File:Jackson_Square.jpg; results/phase6/credit_audit.json).
city_images.clear_licence reads the page itself through
`photograph_credit`, narrowly: only a page that pairs an old work's
public-domain tag (or an artwork template) with a licence of the
photograph's own changes the answer; every other page keeps the metadata's,
which the audit found right for every other credit.

Reading the wikitext (the audit's rules, results/phase6/credit_audit.py,
with what its run showed): a licence is a template named cc-*, CC0, PD-*,
GFDL*, FAL, Attribution* or Copyrighted free use*, anywhere on the page;
{{self}}, {{self2}}, {{Multi-license}} and {{Dual-license}} grant the
licences they wrap; {{Licensed-PD-Art|PD tag|licence}} grants the artwork
the first and the photograph the last; {{Art Photo}} names them in
|artwork license= and |photo license=. A GFDL tag (or its {{self}}) with
migration=relicense also grants CC BY-SA 3.0 (Wikimedia's 2009 licence
migration), and {{cc-by-all}} / {{cc-by-sa-all}} now stand for 4.0, 3.0,
2.5, 2.0 and 1.0 (both redirect there, read 2026-10-09/10).
"""
from __future__ import annotations

import html
import re
import unicodedata

ARTWORK_TEMPLATES = {"artwork", "art photo", "painting", "object photo"}
DESCRIPTION_TEMPLATES = ARTWORK_TEMPLATES | {"information", "photograph"}
WRAPPERS = {"self", "self2", "multi-license", "dual-license"}
LICENCE = re.compile(r"^(cc-.+|cc0|pd-.+|gfdl(-.+)?|fal|free-art-licen[cs]e|attribution(-.+)?"
                     r"|copyrighted-free-use(-.+)?|licensed-pd-art(-two)?|self2?|multi-license"
                     r"|dual-license)$")
# a public-domain tag about the file itself, not about an old work it shows
OWN_PD = re.compile(r"^pd-(self|user|author|ineligible|shape|textlogo|simple|because)|^pd-.*gov")
PD_ART = re.compile(r"^pd-art")
ALL_VERSIONS = ["4.0", "3.0", "2.5", "2.0", "1.0"]


# ---- wikitext templates -------------------------------------------------------

def _scan(text: str):
    """(index, token, template depth, link depth) for each {{ }} [[ ]] | and =."""
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


def _top_templates(text: str) -> list[tuple[int, int]]:
    spans, start = [], None
    for i, tok, t, _ in _scan(text):
        if tok == "{{" and t == 0:
            start = i
        elif tok == "}}" and t == 0 and start is not None:
            spans.append((start, i + 2))
            start = None
    return spans


def _parse(raw: str) -> dict:
    """{{name|a|k=v}} -> name, key (lower case), params (positional "1", "2", ...)."""
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
    return {"name": name, "key": name.lower(), "params": params}


def templates(text: str, parent: str | None = None, field: str | None = None) -> list[dict]:
    """Every template on the page, outermost first, with the template and
    field each sits in."""
    out = []
    for a, b in _top_templates(text):
        tp = _parse(text[a:b])
        tp["parent"], tp["field"] = parent, field
        out.append(tp)
        for k, v in tp["params"].items():
            out.extend(templates(v, tp["key"], k))
    return out


# ---- licences ----------------------------------------------------------------

def tag_key(name: str) -> str:
    return unicodedata.normalize("NFKC", name).strip().lower().replace("_", "-").replace(" ", "-")


def norm_licence(s: str | None) -> list[str]:
    """The licence keys a Commons tag or a credit's licence stands for:
    "CC BY-SA 4.0" and {{cc-by-sa-4.0}} -> cc-by-sa-4.0, any PD tag and
    "Public domain" -> pd, {{Cc-by-sa-3.0-migrated}} -> cc-by-sa-3.0."""
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
        versions = ALL_VERSIONS if vers == "all" else [v for v in vers.split(",") if v]
        return [f"cc-{kind}-{v}{rest}" for v in versions]
    return [t]


def display_licence(key: str) -> str:
    """A licence key as the manifests write a licence: "CC BY-SA 4.0"."""
    m = re.match(r"^cc-(by(?:-sa)?)-([\d.]+)(?:-(\w+))?$", key)
    if m:
        kind, v, port = m.groups()
        return f"CC {kind.upper()} {v}" + (f" {port}" if port else "")
    return {"pd": "Public domain", "cc0": "CC0", "fal": "Free Art License", "gfdl": "GFDL"}.get(key, key)


def licence_link(key: str) -> str | None:
    m = re.match(r"^cc-(by(?:-sa)?)-([\d.]+)(?:-(\w+))?$", key)
    if m:
        kind, v, port = m.groups()
        return f"https://creativecommons.org/licenses/{kind}/{v}" + (f"/{port}" if port else "")
    return {"cc0": "https://creativecommons.org/publicdomain/zero/1.0/"}.get(key)


def _keys(tag: str, migration: str | None) -> list[str]:
    keys = norm_licence(tag)
    if keys == ["gfdl"] and (migration or "").strip().lower() == "relicense":
        keys.append("cc-by-sa-3.0")
    return keys


def licences(tps: list[dict]) -> list[dict]:
    """The licences the page grants, unwrapped, each with whose it is:
    "photograph", "artwork", or (an old work's public-domain tag) the
    photograph's when it is all the page grants and the artwork's beside a
    licence of the photograph's own."""
    out = []
    for tp in tps:
        k = tag_key(tp["name"])
        if not LICENCE.match(k):
            continue
        if tp["parent"] in WRAPPERS or (tp["parent"] or "").startswith("licensed-pd-art"):
            continue  # the wrapper counts it
        field = (tp["field"] or "").lower()
        role = ("artwork" if "artwork licen" in field else
                "photograph" if "photo licen" in field else None)
        pos = [v.strip() for kk, v in tp["params"].items() if kk.isdigit() and v.strip()]
        if k in WRAPPERS:
            for v in pos:
                out.append({"tag": f"{tp['name']}|{v}", "keys": _keys(v, tp["params"].get("migration")),
                            "role": "photograph", "holder": tp["params"].get("author"),
                            "attribution": tp["params"].get("attribution")})
            continue
        if k.startswith("licensed-pd-art"):
            for i, v in enumerate(pos):
                out.append({"tag": f"{tp['name']}|{v}", "keys": norm_licence(v),
                            "role": "photograph" if i == len(pos) - 1 else "artwork",
                            "holder": None, "attribution": None})
            continue
        attribution = None
        if k.startswith("cc-by") or k.startswith("attribution"):
            attribution = tp["params"].get("attribution") or tp["params"].get("1")
        if role is None and (not k.startswith("pd-") or OWN_PD.match(k) or PD_ART.match(k)):
            role = "photograph"
        out.append({"tag": tp["name"], "keys": _keys(tp["name"], tp["params"].get("migration")),
                    "role": role, "holder": None, "attribution": attribution})
    photo_granted = any(x["role"] == "photograph" for x in out)
    for x in out:
        if x["role"] is None:
            x["role"] = "artwork" if photo_granted else "photograph"
    return out


# ---- names --------------------------------------------------------------------

def strip_markup(s: str | None) -> str:
    """Wiki markup to a name: [[User:X|Y]] -> Y, [url Y] -> Y, {{Creator:Y}}
    -> Y, {{U|Y}} / {{user at project|Y|...}} -> Y, other templates dropped."""
    s = re.sub(r"<!--.*?-->", "", s or "", flags=re.S)
    for _ in range(4):
        s = re.sub(r"\{\{\s*[Cc]reator\s*:\s*([^{}|]+)\}\}", r"\1", s)
        s = re.sub(r"\{\{\s*(?:[Uu]ser at project|[Uu]ser|[Uu]|[Uu]ser link)\s*\|\s*([^{}|]+)[^{}]*\}\}",
                   r"\1", s)
        s = re.sub(r"\{\{\s*[a-z]{2,3}(?:-[a-z]+)?\s*\|\s*(?:1\s*=\s*)?([^{}]*)\}\}", r"\1", s)
        s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[(?:https?:)?//\S+\s+([^\]]*)\]", r"\1", s)
    s = re.sub(r"\[(?:https?:)?//\S+\]", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip(" ,;:-")


def _words(s: str | None) -> set[str]:
    t = unicodedata.normalize("NFKD", strip_markup(s)).encode("ascii", "ignore").decode().lower()
    return {w for w in re.findall(r"[a-z0-9]+", t) if len(w) >= 3}


def photographer(desc: dict | None, lic: list[dict]) -> str | None:
    """The photograph's author as the page names it: {{Art Photo}}
    |photographer=, {{self}} |author=, a photograph licence's attribution,
    the description's author ({{Artwork}}: its |photographer=, or |author=
    beside a different |artist=), a "Photo by" source; else None (the
    caller asks for the uploader)."""
    p = (desc or {}).get("params", {})
    k = (desc or {}).get("key")
    cands = []
    if k == "art photo":
        cands.append(p.get("photographer"))
    cands += [x["holder"] for x in lic if x["role"] == "photograph"]
    cands += [x["attribution"] for x in lic if x["role"] == "photograph"]
    if k == "information":
        cands.append(p.get("author"))
    elif k == "photograph":
        cands.append(p.get("photographer") or p.get("author"))
    elif k in ARTWORK_TEMPLATES:
        cands.append(p.get("photographer"))
        if p.get("author") and p.get("artist") and _words(p["author"]) != _words(p["artist"]):
            cands.append(p["author"])
    for c in cands:
        if strip_markup(c):
            return strip_markup(c)
    m = re.search(r"(?i)\bphoto(?:graph)?(?:ed)?\s*(?:by|:)\s*([^,;(\n]+)", strip_markup(p.get("source")))
    return m.group(1).strip() if m and _words(m.group(1)) else None


def _licence_section(text: str) -> str:
    heads = list(re.finditer(r"^(=+)\s*(.*?)\s*\1\s*$", text, flags=re.M))
    for n, h in enumerate(heads):
        if re.search(r"licen[cs]|license-header", h.group(2), flags=re.IGNORECASE):
            end = next((x.start() for x in heads[n + 1:] if len(x.group(1)) <= len(h.group(1))),
                       len(text))
            return text[h.start():end]
    return ""


# ---- the decision ---------------------------------------------------------------

def photograph_credit(wikitext: str) -> dict | None:
    """None when the page's metadata answer stands. Otherwise the
    photograph's own credit — {"licences": its licence keys in the page's
    order, "author": the photographer as named, or None} — when the page
    pairs an old work's public-domain tag with a licence of the
    photograph's own, or is an artwork page whose photograph carries a
    licence other than public domain (a faithful {{PD-Art}} copy keeps the
    metadata's answer: the painter, public domain); or {"unreadable": why}
    when an old work's tag sits beside a user's own licence template, which
    this reading cannot open."""
    clean = re.sub(r"<!--.*?-->", "", wikitext or "", flags=re.S)
    tps = templates(clean)
    desc = next((tp for tp in tps if tp["parent"] is None and tp["key"] in DESCRIPTION_TEMPLATES),
                None)
    lic = licences(tps)
    photo = [x for x in lic if x["role"] == "photograph"]
    art = [x for x in lic if x["role"] == "artwork"]
    old_pd_alone = (photo and not art and all(
        x["keys"] == ["pd"] and not OWN_PD.match(tag_key(x["tag"].split("|")[-1]))
        and not PD_ART.match(tag_key(x["tag"].split("|")[-1])) for x in photo))
    if old_pd_alone and any(tp["key"].startswith("user:")
                            for tp in templates(_licence_section(clean))):
        return {"unreadable": "an old work's public-domain tag beside a user's licence template"}
    artwork_page = bool(desc) and desc["key"] in ARTWORK_TEMPLATES
    pd_art = any(PD_ART.match(tag_key(x["tag"].split("|")[-1])) for x in photo)
    own_licence = any(k != "pd" for x in photo for k in x["keys"])
    if not photo or not (art or (artwork_page and own_licence and not pd_art)):
        return None
    keys = list(dict.fromkeys(k for x in photo for k in x["keys"]))
    return {"licences": keys, "author": photographer(desc, lic)}
