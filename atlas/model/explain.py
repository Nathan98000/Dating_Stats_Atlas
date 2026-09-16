"""Explanation layer (§9, as amended by ADR 0003): deterministic templates
over the exact feature-level attribution. The D10 comparator is retired —
the ranking is the comparison, and a reader who wants a specific pair gets
the compare page.

Every label is rendered from the build's legend (registry -> manifest ->
Build.legend); no user-facing name lives here. Suppression and confidence
strings come verbatim from suppression.POLICY_STRINGS.

Build-time metro narratives are Phase 3; this module produces the
structured metric record they will consume (§9's JSON contract, feature-
level since ADR 0003) and the per-request explanation text from jinja
templates.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

# The lead sentence names the top stats by |contribution| in score points.
# TOP_STATS_MAX per ADR 0003 ("two or three"); a stat below
# TOP_STATS_MIN_POINTS is noise relative to a 0-100 score and is not
# presented as having moved anything.
TOP_STATS_MAX = 3
TOP_STATS_MIN_POINTS = 0.5

# magnitude buckets over |contribution| in score points (metric record only)
BUCKETS = [(8.0, "large"), (3.0, "moderate"), (0.0, "slight")]

_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                   undefined=StrictUndefined, trim_blocks=True,
                   lstrip_blocks=True)


def bucket(value: float) -> str:
    for cut, name in BUCKETS:
        if abs(value) >= cut:
            return name
    return "slight"


def format_value(value: float, legend_entry: dict) -> str:
    """Real-units display string per the registry's display spec. Computed
    server-side so the frontend never does arithmetic on a number."""
    scaled = value * float(legend_entry.get("display_scale", 1.0))
    nd = int(legend_entry.get("display_decimals", 1))
    return f"{scaled:,.{nd}f}"


def top_stats(stats: list[dict]) -> list[dict]:
    """The two or three stats that moved this metro's score for these
    weights: largest |contribution| first, floor at TOP_STATS_MIN_POINTS."""
    moved = [s for s in stats if s.get("contribution") is not None
             and abs(s["contribution"]) >= TOP_STATS_MIN_POINTS]
    moved.sort(key=lambda s: -abs(s["contribution"]))
    return moved[:TOP_STATS_MAX]


def metric_record(row: dict) -> dict:
    """§9's structured record — the input the Phase 3 build-time narratives
    will consume. Feature-level since ADR 0003; no comparator."""
    contribs = sorted((s for s in row["stats"]
                       if s.get("contribution") is not None),
                      key=lambda s: -s["contribution"])
    def entry(s: dict) -> dict:
        return {"feature": s["id"], "pillar": s["pillar"],
                "contribution": s["contribution"], "value": s["value"],
                "bucket": bucket(s["contribution"])}
    strengths = [entry(s) for s in contribs if s["contribution"] > 0][:2]
    weaknesses = [entry(s) for s in reversed(contribs)
                  if s["contribution"] < 0][:2]
    caveats = list(row.get("flags", []))
    if row["cv"] > 0.15:
        caveats.append("served_cv_above_15")
    return {"metro": row["cbsa"], "rank": row["rank"], "pool": row["pool"],
            "pool_moe": row["pool_moe"], "tier": row["tier"],
            "strengths": strengths, "weaknesses": weaknesses,
            "caveats": caveats}


def render_explanation(row: dict, legend: dict[str, dict]) -> str:
    """Per-request 'why it ranks here for you' text: the top stats by
    absolute contribution, each with its display name, its value in real
    units, and what it did to the score — so the text changes when the
    weights do, which is the point."""
    tpl = _env.get_template("ranked.jinja")
    movers = []
    for s in top_stats(row["stats"]):
        le = legend[s["id"]]
        short = le.get("unit_short", "")
        movers.append({
            "label": le["display_name"],
            "value": format_value(s["value"], le),
            "unit_suffix": f" {short}" if short else "",
            "points": f"{s['contribution']:+.1f}",
            "positive": s["contribution"] > 0,
        })
    return tpl.render(name=row["name"], rank=row["rank"],
                      movers=movers).strip()
