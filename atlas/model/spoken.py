"""Spoken population figures — one rule for every place the site says how
many people live in a metro (Phase 6, m4.3.0, F09): the who-lives-here card
(scoring._card_stats_made, its population and its adults), the city
description (pipeline/build/descriptions.py) and the population stat page
(web/scripts/build_stat_pages.py). Before, the card rounded to steps of
50,000 above 95,000 and the description its own way, so Mansfield (125,160)
read "150,000" and Abilene "200,000 people, of whom 100,000 are adults".

Below 950,000 a figure is rounded to 2 significant figures (183,310 ->
"180,000", 125,160 -> "130,000", 80,123 -> "80,000"); at 950,000 and above
it reads "N.N million" as before. Precision to the person would claim more
than a survey knows.

The floor guard: a metro outside the ranked set never reads at or above
the population floor the ranked set is cut at (the registry's
population_floor, 250,000) — a figure that would round up to it rounds down
to the next 2-figure step instead (Daphne 246,979 -> "240,000"), so no page
says "about 250,000" over a note that the metro is too small to rank.
"""
from __future__ import annotations

import math


def _step(pop: float) -> int:
    """The 2-significant-figure step of a positive figure: 10,000 for
    183,310, 1,000 for 80,123 ... 1 below 100."""
    digits = int(math.floor(math.log10(pop))) + 1 if pop >= 1 else 1
    return 10 ** max(digits - 2, 0)


def spoken_pop(pop: float, ceiling: float | None = None) -> str:
    """The spoken figure for `pop`. `ceiling`, when given (the population
    floor, for a metro outside the ranked set), is a figure the result must
    stay below."""
    if pop >= 950_000:
        m = round(pop / 100_000) / 10
        m_txt = f"{m:.0f}" if float(m).is_integer() else f"{m:.1f}"
        return f"{m_txt} million"
    step = _step(pop)
    value = int(math.floor(pop / step + 0.5)) * step          # half up
    if ceiling is not None and value >= ceiling:
        value = int(math.floor(pop / step)) * step
        while value >= ceiling:
            value -= step
    return f"{value:,.0f}"
