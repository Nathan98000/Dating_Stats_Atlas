"""Context a metro's page shows and no ranking reads (Phase 4d, ADR 0019):
political lean — how the metro area voted in the 2024 presidential
election. Nathan's decision: context only — never scored, never a filter,
never a weight or importance control, never feeding the compatibility
figure, never asked of the visitor.

Pure, like the rest of the package: it reads the loaded Build and composes
every figure and word the pages show from the registry's strings. The
build carries each metro's votes (Democratic, Republican, every vote for a
candidate; NaN where the returns cannot cover the metro exactly); here they
become three shares, divided once, each shown as a whole percentage
through the registry's display spec. The order never changes: Democratic,
everyone else, Republican on the bar; Democratic before Republican in
words. No band word, no tone and no rank is attached. Nothing in
scoring, suppression or variants imports this module.
"""
from __future__ import annotations

import numpy as np

from atlas.model.explain import format_value
from atlas.model.loader import Build

# the bar's order, left to right (ADR 0019): the same everywhere
SEGMENTS = ("dem", "other", "rep")


def political_lean_block(build: Build, i: int) -> dict:
    """The political lean block of metro i — request-independent, made once
    per metro and kept (the crime block's pattern)."""
    key = ("political_lean", i)
    if key not in build.memo:
        build.memo[key] = _political_lean_made(build, i)
    return build.memo[key]


def _political_lean_made(build: Build, i: int) -> dict:
    strings = build.manifest["strings"]
    le = build.legend["political_lean"]
    dem, rep, votes = (float(build.political[k][i]) for k in ("dem", "rep", "votes"))
    if not (np.isfinite(dem) and np.isfinite(rep) and np.isfinite(votes) and votes > 0):
        return {"available": False, "note": strings["political_lean_missing"]}
    share = {"dem": dem / votes, "other": (votes - dem - rep) / votes, "rep": rep / votes}
    assert min(share.values()) >= 0, (build.metro_levels[i], share)
    shown = {k: format_value(v, le) + le["unit_short"] for k, v in share.items()}
    label = {"dem": strings["political_lean_dem"], "other": strings["political_lean_other"],
             "rep": strings["political_lean_rep"]}
    return {
        "available": True,
        # "56% Democratic · 42% Republican"
        "text": strings["political_lean_text"].format(
            dem=shown["dem"], dem_label=label["dem"], rep=shown["rep"], rep_label=label["rep"]),
        # the bar's spoken label: all three shares, in the bar's order
        "bar_label": strings["political_lean_bar_label"].format(
            **{f"{k}_label": label[k] for k in SEGMENTS}, **shown),
        # the bar, left to right; width is the share in percent, so the
        # browser sizes each segment without arithmetic
        "segments": [{"key": k, "label": label[k], "display": shown[k],
                      "width": round(share[k] * 100, 2)} for k in SEGMENTS],
        # what the stat page sorts on when the visitor asks it to
        "share": {"dem": round(share["dem"], 6), "rep": round(share["rep"], 6)},
    }


def political_lean_all(build: Build) -> dict[str, dict]:
    """Every metro's block, keyed by CBSA code."""
    return {c: political_lean_block(build, i) for i, c in enumerate(build.metro_levels)}
