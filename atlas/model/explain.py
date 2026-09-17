"""Explanation layer, m2.0.0: the movers line and the display-string
helpers. The v3 boards replace per-row sentences with one plain line —
"Biggest pluses: the size of the pool, the balance, walkable
neighbourhoods · Rent counts against it" — composed HERE, server-side,
from registry mover phrases, so the frontend never selects or words what
moved a city. The jinja template and its renderer left with the old row
copy; the §9 metric record stays for the deferred build-time narratives.

Every label is rendered from the build's legend (registry -> manifest ->
Build.legend); no user-facing name lives here.
"""
from __future__ import annotations

# The movers line names the top stats by |contribution| in score points.
# TOP_STATS_MAX per ADR 0003 ("two or three"); a stat below
# TOP_STATS_MIN_POINTS is noise relative to a 0-100 score and is not
# presented as having moved anything.
TOP_STATS_MAX = 3
TOP_STATS_MIN_POINTS = 0.5

# magnitude buckets over |contribution| in score points (metric record only)
BUCKETS = [(8.0, "large"), (3.0, "moderate"), (0.0, "slight")]


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


def summary_line(row: dict, legend: dict[str, dict]) -> str:
    """The v3 row line: pluses named by their registry mover phrases, the
    single biggest minus appended as '· X counts against it' (HomeV3's
    exact shape). Position-unique lead by construction; the validation
    suite still asserts it, because the last renderer that looked obviously
    correct wasn't."""
    from atlas.model.suppression import POLICY_STRINGS
    movers = top_stats(row["stats"])
    pluses = [s for s in movers if s["contribution"] > 0]
    minuses = [s for s in movers if s["contribution"] < 0]

    def phrase(s: dict) -> str:
        le = legend[s["id"]]
        return le.get("mover_phrase") or le["display_name"].lower()

    parts = []
    if pluses:
        parts.append(POLICY_STRINGS["pluses_lead"]
                     + ", ".join(phrase(s) for s in pluses))
    if minuses:
        worst = min(minuses, key=lambda s: s["contribution"])
        p = phrase(worst)
        parts.append(p[0].upper() + p[1:] + POLICY_STRINGS["minus_tail"])
    if not parts:
        return "Close to the middle of the pack on everything you weighted"
    return " · ".join(parts)


def metric_record(row: dict) -> dict:
    """§9's structured record — the input the deferred build-time
    narratives will consume. Feature-level since ADR 0003."""
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
