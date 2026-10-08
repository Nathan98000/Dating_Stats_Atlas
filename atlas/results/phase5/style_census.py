"""Phase 5: how many distinct font sizes, corner radii and control heights
web/src uses, and how many arbitrary Tailwind values (text-[..], rounded-[..],
min-h-[..]) remain.

Counted from the source, class by class: a font size is a Tailwind text
size (named, theme token or arbitrary px/rem) or a CSS font-size; a radius
is a rounded-* class or a CSS border-radius; a control height is an
h-/min-h- class inside the opening tag of a control (<button, <select,
<input, <summary, or a tag with role="radio"/"checkbox"/"switch", read up
to its first " =>" or ">"), or a CSS height/min-height in a rule for .ctl,
a button, .seg or .chip. Responsive and state prefixes are stripped, so
`sm:text-sm` and `text-sm` are one size.

    python3 atlas/results/phase5/style_census.py <label>
        -> atlas/results/phase5/style_census_<label>.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "web" / "src"
NAMED_TEXT = {"xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl", "5xl", "6xl", "7xl", "8xl", "9xl"}
TOKEN_TEXT = {"display-1", "display-2", "h2", "h3", "title", "body-lg", "body", "body-sm", "caption",
              "overline", "data-xl", "data-l", "data-m"}
CLASS = re.compile(r"(?<![\w-])(?:[a-z0-9]+:)*(text|rounded(?:-[trbl]{1,2})?|min-h|h)-(\[[^\]]+\]|[\w./-]+)")
TAG = re.compile(r"<(button|select|input|summary|div|span|label|a|Link)\b((?:(?!=>)[^>])*)>")
ROLE = re.compile(r'role="(radio|checkbox|switch)"')


def census() -> dict:
    sizes, radii, heights = set(), set(), set()
    arbitrary = {"text": 0, "rounded": 0, "min-h": 0}
    for f in sorted(SRC.rglob("*.tsx")) + sorted(SRC.rglob("*.ts")):
        text = f.read_text()
        for tag in TAG.finditer(text):
            if tag.group(1) in ("button", "select", "input", "summary") or ROLE.search(tag.group(2)):
                for kind, val in CLASS.findall(tag.group(2)):
                    if kind in ("h", "min-h"):
                        heights.add(f"{kind}-{val}")
        for line in text.splitlines():
            for kind, val in CLASS.findall(line):
                if kind == "text":
                    if val.startswith("["):
                        if re.match(r"\[\d", val):
                            sizes.add(val)
                            arbitrary["text"] += 1
                    elif val in NAMED_TEXT or val in TOKEN_TEXT:
                        sizes.add(val)
                elif kind.startswith("rounded"):
                    radii.add(val)
                    if val.startswith("["):
                        arbitrary["rounded"] += 1
                else:
                    if kind == "min-h" and val.startswith("["):
                        arbitrary["min-h"] += 1
    css = (SRC / "app" / "globals.css").read_text()
    for m in re.finditer(r"font-size:\s*([^;]+);", css):
        sizes.add("css:" + m.group(1).strip())
    for m in re.finditer(r"border-radius:\s*([^;]+);", css):
        radii.add("css:" + m.group(1).strip())
    for block in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        sel, body = block.group(1), block.group(2)
        if re.search(r"\.ctl|button|\.seg|\.chip", sel):
            for m in re.finditer(r"(?<![-\w])(min-height|height):\s*([^;]+);", body):
                heights.add(f"css:{m.group(1)}:{m.group(2).strip()}")
    return {"font_sizes": len(sizes), "radii": len(radii), "control_heights": len(heights),
            "arbitrary_values": arbitrary, "arbitrary_total": sum(arbitrary.values()),
            "detail": {"font_sizes": sorted(sizes), "radii": sorted(radii),
                       "control_heights": sorted(heights)}}


if __name__ == "__main__":
    label = sys.argv[1]
    out = census()
    (HERE / f"style_census_{label}.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "detail"}))
