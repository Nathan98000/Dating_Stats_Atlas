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


def format_pop(pop: float) -> str:
    """Spoken population figures for the who-lives-here card: 717,200
    reads as 700,000 and 1,281,004 as 1.3 million — precision to the
    person would claim more than a survey knows."""
    if pop >= 950_000:
        m = round(pop / 100_000) / 10
        m_txt = f"{m:.0f}" if float(m).is_integer() else f"{m:.1f}"
        return f"{m_txt} million"
    if pop >= 95_000:
        return f"{round(pop / 50_000) * 50_000:,.0f}"
    return f"{round(pop / 10_000) * 10_000:,.0f}"


def format_value(value: float, legend_entry: dict) -> str:
    """Real-units display string per the registry's display spec. Computed
    server-side so the frontend never does arithmetic on a number."""
    scaled = value * float(legend_entry.get("display_scale", 1.0))
    nd = int(legend_entry.get("display_decimals", 1))
    return f"{scaled:,.{nd}f}"


def mover_phrase(legend_entry: dict) -> str:
    return legend_entry.get("mover_phrase") or legend_entry["display_name"].lower()


def mover_units(ids: list[str], legend: dict[str, dict]) -> list[dict]:
    """The movers line's items, in the stats' order: one per mover phrase,
    with the stats that share it. m4.1.1: the two BEA price levels share
    "everyday prices" — the card that shows them both — so they move a city
    as one item, their contributions added. Before, each was an item of
    its own, and a line could name "everyday prices" twice, or as a plus
    and the minus at once."""
    units: dict[str, dict] = {}
    for j, fid in enumerate(ids):
        p = mover_phrase(legend[fid])
        units.setdefault(p, {"phrase": p, "ids": [], "cols": []})
        units[p]["ids"].append(fid)
        units[p]["cols"].append(j)
    for u in units.values():
        assert len({int(legend[i]["direction"]) for i in u["ids"]}) == 1, (
            f"the stats sharing {u['phrase']!r} must share a direction")
    return list(units.values())


def mover_sides(units: list[dict], legend: dict[str, dict], cards: list[dict],
                band_keys: list[str]) -> list[int]:
    """Per item, the side of the middle that the city's card puts it on,
    in the score's direction: +1 where the card says it is better than
    most cities, -1 worse than most, 0 about average or no card. The card
    is the one showing the item's own stat, or else the one named by its
    phrase (everyday prices). Cards compare every city of the build; the
    score compares the cities ranked for the search."""
    mid = (len(band_keys) - 1) / 2
    position = {k: (i > mid) - (i < mid) for i, k in enumerate(band_keys)}
    by_id = {c["id"]: c for c in cards}
    sides = []
    for u in units:
        card = next((by_id[i] for i in u["ids"] if i in by_id), None) or next(
            (c for c in cards if mover_phrase(legend[c["id"]]) == u["phrase"]), None)
        band = (card or {}).get("band")
        sides.append(int(legend[u["ids"][0]]["direction"]) * position[band["key"]] if band else 0)
    return sides


def unit_contributions(contribs: list[float | None], units: list[dict]) -> list[float | None]:
    """Each item's contribution: its stats' rounded contributions added in
    the stats' order (None where all are missing)."""
    out = []
    for u in units:
        c = None
        for j in u["cols"]:
            if contribs[j] is not None:
                c = contribs[j] if c is None else c + contribs[j]
        out.append(c)
    return out


def pick_movers(contribs: list[float | None], sides: list[int]) -> list[int]:
    """The items that moved this metro's score for these weights, as item
    positions: |contribution| at least TOP_STATS_MIN_POINTS, largest first,
    ties in item order, at most TOP_STATS_MAX. m4.1.1: an item whose sign
    contradicts its card is left out — the line never calls a stat a minus
    where the city's card says better than most, nor a plus where it says
    worse than most. (The score measures a stat against the middle of the
    cities ranked for the search; for Austin, walkable "more than most"
    cities, that middle could sit above it.)"""
    moved = [u for u, c in enumerate(contribs)
             if c is not None and abs(c) >= TOP_STATS_MIN_POINTS and not c * sides[u] < 0]
    moved.sort(key=lambda u: -abs(contribs[u]))
    return moved[:TOP_STATS_MAX]


def movers(row: dict, legend: dict[str, dict], band_keys: list[str]) -> list[dict]:
    """A row's movers: {phrase, ids, contribution} per item, in order."""
    units = mover_units([s["id"] for s in row["stats"]], legend)
    contribs = unit_contributions([s.get("contribution") for s in row["stats"]], units)
    sides = mover_sides(units, legend, row.get("cards", []), band_keys)
    return [{"phrase": units[u]["phrase"], "ids": units[u]["ids"], "contribution": contribs[u]}
            for u in pick_movers(contribs, sides)]


def summary_line(moved: list[dict]) -> str:
    """The v3 row line from the movers, in order: pluses named by their
    registry mover phrases, the single biggest minus appended as '· X
    counts against it' (HomeV3's exact shape). Position-unique lead by
    construction; the validation suite still asserts it, because the last
    renderer that looked obviously correct wasn't."""
    from atlas.model.suppression import POLICY_STRINGS
    pluses = [m for m in moved if m["contribution"] > 0]
    minuses = [m for m in moved if m["contribution"] < 0]
    parts = []
    if pluses:
        parts.append(POLICY_STRINGS["pluses_lead"]
                     + ", ".join(m["phrase"] for m in pluses))
    if minuses:
        p = minuses[0]["phrase"]          # the biggest: movers come largest first
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
