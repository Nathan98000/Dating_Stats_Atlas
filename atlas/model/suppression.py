"""Suppression policy, m2.0.0 — the gate is sample size alone (ADR 0002),
and with the rival apparatus retired (ADR 0004) the reasons reduce to two:

    suppressed    min(n_alloc, kish) < 100, or an empty pool
    ranked        everything else in the ranked set

Dating pool balance carries its own separate gate (its two counts are
whole age-by-sex slices, so it usually survives even when the filtered
pool does not) — asserted per quantity in scoring, never wholesale.

Suppression is now the only VISIBLE expression of uncertainty (ADR 0004):
no margin, CV or interval renders anywhere, which is exactly why the gate
has to keep working. The interval machinery itself is untouched — the API
keeps returning pool_moe, Gate 0's calibrated bound stays in the manifest,
and the technical strings live under TECHNICAL_STRINGS (returned by the
API, never rendered by the site; the methodology page explains margins in
plain language instead).

POLICY_STRINGS are the rendered vocabulary, versioned with MODEL_VERSION.
The v3 boards' wording is approved copy — NarrowV3 and MetroV3 verbatim,
StatesV3's count sentence as a template — and it lives here so it stays
versioned (never improvised in a component). None of it states a count of
people or cities beyond the two counts StatesV3 itself shows, and nothing
in it ever says zero.
"""
from __future__ import annotations

import numpy as np

N_GATE_MIN = 100.0
PURITY_FLAG_BAR = 0.5
GQ_SHARE_FLAG_BAR = 0.15
FEW_METROS_NOTICE = 40


def tier_masks(universe: np.ndarray, est: np.ndarray,
               n_gate: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(suppressed, ranked). No middle tier; no rival condition (m2.0.0)."""
    suppressed = universe & ((n_gate < N_GATE_MIN) | (est <= 0))
    ranked = universe & ~suppressed
    return suppressed, ranked


def suppression_reason(est: float, n_gate: float) -> str:
    if est <= 0:
        return "empty_pool"
    return "n_below_100"


# ---------------------------------------------------------------------------
# Rendered strings (versioned, approved copy from the v3 boards).
# ---------------------------------------------------------------------------
POLICY_STRINGS = {
    # suppression reasons, spoken plainly
    "n_below_100": "Too few people in the survey match this search here for "
                   "an answer worth trusting.",
    "empty_pool": "The survey turns up nobody matching this search here — "
                  "which is about the survey's reach, not the city.",

    # StatesV3: the list heading's count sentence — shown ONLY when at
    # least one city is excluded, never with a zero (wording per Nathan's
    # Phase 2f review, item 4.6, verbatim)
    "excluded_count": "{n} cities don’t have enough people matching this "
                      "search to make a reliable estimate. Widen your "
                      "search to see more cities.",
    "list_heading": "Cities for you",
    "list_heading_count": "{n} cities for you",

    # NarrowV3, verbatim (approved): the all-suppressed state
    "narrow_title": "This one’s a tall order almost anywhere",
    "narrow_body": "{search} is a very small group in any city — small "
                   "enough that the Census survey doesn’t turn up sample "
                   "to say anything dependable about where they live. Rather "
                   "than dress up a guess, we’d rather point you back a "
                   "step. Loosen any one thing and the picture fills right "
                   "in.",
    "narrow_note": "This doesn’t mean nobody fits your description — "
                   "it means too few of them show up in the survey for us to "
                   "tell you where they are. The narrower the search, the "
                   "more often that happens.",

    # MetroV3, verbatim (approved): the city page's card when the pool has
    # nothing to say for this search
    "city_narrow_title": "A search this specific is hard to answer here",
    "city_narrow_body": "You’re looking for {search}. That’s a small "
                        "slice of any city, and {city} is on the smaller side "
                        "— too few people like that turn up in the Census "
                        "survey here for us to give you a figure we’d "
                        "stand behind. Loosen one thing and {city} may well "
                        "have an answer.",

    # HomeV3: the balance footnote — rewritten for the m2.0.0 definition
    # (the board's "like for like" caption described the superseded
    # like-for-like comparison; ADR 0004 records the supersession)
    "balance_caption": "Balance compares all single men with all single "
                       "women in the ages you picked — before any other "
                       "filter. Counts come from the Census Bureau’s "
                       "survey of 3.5 million households a year.",
    "balance_row_caption": "{ratio} {sought} per 100 {seekers}",
    "balance_unavailable": "Not enough survey sample here to compare the "
                           "two sides.",
    "balance_same_sex": "In a same-sex search everyone is on both sides of "
                        "the comparison, so balance doesn’t apply — "
                        "the other measures carry its weight.",

    # the m2.0.0 race-panel one-liner is GONE (m2.2.0/ADR 0006): the
    # panel stopped rendering it in Phase 2d, and its always-counted
    # claim stopped being true when the eight groups became equal

    # movers line pieces (HomeV3: "Biggest pluses: … · Rent counts against it")
    "pluses_lead": "Biggest pluses: ",
    "minus_tail": " counts against it",

    # flags, spoken plainly
    "low_allocation_purity": "Estimates here lean on survey areas this city "
                             "shares with its neighbours.",
    "gq_flag": "A notable share of adults here live in group housing such "
               "as dorms or barracks.",
    "missing_features": "One or two of the place stats aren’t available "
                        "here; the rest carry their weight.",
}

# Returned by the API for the record and the methodology page's
# plain-language account — never rendered on a product page (ADR 0004).
TECHNICAL_STRINGS = {
    "interval": "Every served margin is 'at least this wide': the true "
                "margin of error is at or below the served margin on at "
                "least 95% of held-out validation queries (measured: 97.5%), "
                "and the served margin overstates the true one by 23% at the "
                "median (gate: at most 25%). Margins are calibrated upper "
                "bounds.",
    "suppression_policy": "A city is left out when fewer than 100 effective "
                          "respondents (the smaller of the allocated count "
                          "and the Kish effective sample size) sit in the "
                          "queried range, or when its pool is empty. "
                          "Precision is expressed by leaving a city out, "
                          "never by publishing a number we cannot stand "
                          "behind (ADR 0002/0004).",
    "balance_gate": "Balance is gated separately from the pool: each of its "
                    "two whole age-by-sex counts must clear the same "
                    "100-effective-respondent bar.",
}
