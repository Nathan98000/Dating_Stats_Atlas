"""Explanation layer (§9): deterministic templates over the exact
attribution vector, and the D10 comparator.

D10 — the comparator is the nearest metro by population that ranks
differently, with the population-distance metric and the minimum rank gap
as named constants here (not in the registry, per the decision record), so
they can be retuned against the face-validity panel without touching a
template. Comparisons to the #1 metro are never generated.

Build-time metro narratives are Phase 2b+; this module produces the
structured metric record they will consume (§9's JSON contract) and the
per-request explanation text from jinja templates. Suppression and
confidence strings come verbatim from suppression.POLICY_STRINGS.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# D10 named constants
MIN_RANK_GAP = 5
POPULATION_DISTANCE = "abs(ln(pop_a / pop_b))"

# magnitude buckets over |contribution| in score points
BUCKETS = [(8.0, "large"), (3.0, "moderate"), (0.0, "slight")]

_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                   undefined=StrictUndefined, trim_blocks=True,
                   lstrip_blocks=True)


def comparator(pops: dict[int, float], rank_of: dict[int, int]) -> dict[int, int | None]:
    """For each metro index: the nearest-by-population metro whose rank
    differs by at least MIN_RANK_GAP; never the #1 metro; None if no
    candidate exists."""
    out: dict[int, int | None] = {}
    idx = list(rank_of)
    for i in idx:
        best, best_d = None, None
        for j in idx:
            if j == i or rank_of[j] == 1:
                continue
            if abs(rank_of[i] - rank_of[j]) < MIN_RANK_GAP:
                continue
            d = abs(np.log(pops[i] / pops[j]))
            if best_d is None or d < best_d:
                best, best_d = j, d
        out[i] = best
    return out


def bucket(value: float) -> str:
    for cut, name in BUCKETS:
        if abs(value) >= cut:
            return name
    return "slight"


PILLAR_FACTS = {
    "pool": ("pool_ratio_vs_comparator", "compatible people"),
    "balance": ("partners_per_rival", "partners per rival"),
    "reach": ("resident_walkability_index", "walkability of where residents live"),
    "cost": ("median_gross_rent", "median rent"),
    "lifestyle": ("pleasant_days", "pleasant days a year"),
}


def metric_record(row: dict, comparator_row: dict | None,
                  statics: dict[str, float]) -> dict:
    """§9's structured record — the input the Phase 2b build-time narratives
    will consume, produced here so the contract is pinned now."""
    contribs = sorted(row["contributions"], key=lambda c: -c["value"])
    def fact_for(pillar: str) -> dict:
        fact, _ = PILLAR_FACTS[pillar]
        if pillar == "pool":
            val = (row["pool"] / comparator_row["pool"]
                   if comparator_row and comparator_row.get("pool") else None)
        elif pillar == "balance":
            val = row["ratio"]
        else:
            val = statics.get(PILLAR_FACTS[pillar][0])
        return {"fact": fact, "value": None if val is None else round(float(val), 3)}

    strengths = [{"pillar": c["pillar"], "contribution": c["value"],
                  **fact_for(c["pillar"])}
                 for c in contribs if c["value"] > 0][:2]
    weaknesses = [{"pillar": c["pillar"], "contribution": c["value"],
                   **fact_for(c["pillar"])}
                  for c in reversed(contribs) if c["value"] < 0][:2]
    caveats = list(row.get("flags", []))
    if row["cv"] > 0.15:
        caveats.append("cv_between_15_and_30")
    return {"metro": row["cbsa"], "rank": row["rank"], "pool": row["pool"],
            "pool_moe": row["pool_moe"], "tier": row["tier"],
            "strengths": strengths, "weaknesses": weaknesses,
            "comparator": row.get("comparator"), "caveats": caveats}


def render_explanation(record: dict, name: str, comparator_name: str | None) -> str:
    """Per-request 'why it ranks here for you' text (§9): top two positive
    and top two negative contributions, phrasing variant by magnitude
    bucket, real numbers, real comparator."""
    tpl = _env.get_template("ranked.jinja")
    return tpl.render(
        name=name, record=record, comparator_name=comparator_name,
        strengths=[{**s, "bucket": bucket(s["contribution"]),
                    "noun": PILLAR_FACTS[s["pillar"]][1]}
                   for s in record["strengths"]],
        weaknesses=[{**w, "bucket": bucket(w["contribution"]),
                     "noun": PILLAR_FACTS[w["pillar"]][1]}
                    for w in record["weaknesses"]],
    ).strip()
