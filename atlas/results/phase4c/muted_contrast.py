"""Phase 4c: the WCAG contrast of the race field muted on a same-sex search,
computed from the design tokens in web/src/app/globals.css (the e2e test
reads the same colours off the rendered page and holds them to AA).

    python3 atlas/results/phase4c/muted_contrast.py -> results/phase4c/muted_contrast.json
"""
import json
import re
from pathlib import Path

ATLAS = Path(__file__).resolve().parents[2]
css = (ATLAS / "web" / "src" / "app" / "globals.css").read_text()
tok = {k: v for k, v in re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})", css)}


def lum(hexcol: str) -> float:
    def f(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((lum(tok[a]), lum(tok[b])), reverse=True)
    return round((hi + 0.05) / (lo + 0.05), 2)


out = {"tokens": {k: tok[k] for k in ("ink", "ink-2", "ink-3", "paper", "surface", "rule")},
       "muted": {"text ink-3 on its paper fill (4.5 needed)": ratio("ink-3", "paper"),
                 "label ink-3 on the white panel (4.5 needed)": ratio("ink-3", "surface"),
                 "dashed border ink-3 against the white panel (3 needed)": ratio("ink-3", "surface"),
                 "dashed border ink-3 against its paper fill (3 needed)": ratio("ink-3", "paper")},
       "plain": {"text ink on the white fill": ratio("ink", "surface"),
                 "label ink-2 on the white panel": ratio("ink-2", "surface"),
                 "border rule against the white panel (noticed, not changed)": ratio("rule", "surface")}}
(ATLAS / "results" / "phase4c" / "muted_contrast.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))
