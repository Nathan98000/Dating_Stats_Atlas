"""Phase 8 (the round-4 review's R18): the site's Fraunces, trimmed to what
the site uses.

The site sets Fraunces only at weights 600 and 700 (globals.css's type
scale and the rank medallions), always with SOFT 30, at every optical size.
next/font/google can only load the whole variable font for that (its axes
option needs the full weight range), 120.7 KB for the Latin file. This
takes Google's own Latin file (the one next/font fetched), pins SOFT at 30
and limits the weight axis to 600-700 with fontTools' instancer, keeping
the optical-size axis, and writes src/app/fonts/fraunces-latin.woff2
(58.3 KB), which app/layout.tsx loads with next/font/local. It draws the
same letters at the same weight: the instancer only drops the variation
data outside those values. Phase 8 compared screenshots of the headings,
names, scores and rank medallions before and after: they look the same,
while anti-aliasing at letter edges differs on 1.5-6% of pixels and a
line can set up to about 0.2% narrower (the instancer re-expresses the
outlines, and a few points round differently). The font is under the SIL
Open Font License 1.1, kept beside it (src/app/fonts/OFL.txt).

Needs fontTools and brotli, which the project's environment does not hold;
in a throwaway one:

    python3 -m venv /tmp/fontenv && /tmp/fontenv/bin/pip install fonttools brotli
    /tmp/fontenv/bin/python atlas/web/scripts/fraunces_trim.py
"""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

WEB = Path(__file__).resolve().parents[1]
OUT = WEB / "src" / "app" / "fonts" / "fraunces-latin.woff2"
CSS = ("https://fonts.googleapis.com/css2?family=Fraunces:opsz,SOFT,wght@9..144,0..100,100..900"
       "&display=swap")
# Google serves woff2 to a current browser
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/141.0.0.0 Safari/537.36")
LIMITS = {"SOFT": 30, "wght": (600, 700)}


def latin_url() -> str:
    css = urllib.request.urlopen(urllib.request.Request(CSS, headers={"User-Agent": UA})).read().decode()
    # the @font-face whose unicode-range starts with U+0000-00FF: the latin subset
    for face in re.findall(r"@font-face\s*\{[^}]*\}", css):
        if "U+0000-00FF" in face:
            return re.search(r"url\((https://[^)]+\.woff2)\)", face).group(1)
    raise SystemExit("no latin face in Google's CSS")


def main() -> None:
    url = latin_url()
    src = OUT.parent / "_fraunces-latin-full.woff2"
    src.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})).read())
    font = TTFont(src)
    axes = {a.axisTag for a in font["fvar"].axes}
    assert {"opsz", "wght", "SOFT"} <= axes, axes
    trimmed = instancer.instantiateVariableFont(font, LIMITS)
    trimmed.flavor = "woff2"
    trimmed.save(OUT)
    src.unlink()
    left = [(a.axisTag, a.minValue, a.maxValue) for a in trimmed["fvar"].axes]
    print(f"{url}\n-> {OUT} ({OUT.stat().st_size:,} bytes; axes {left})")


if __name__ == "__main__":
    sys.exit(main())
