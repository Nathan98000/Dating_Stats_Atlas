"""Every "about you" variant of one search — m4.0.0 (ADR 0018).

The visitor's own sex, education and race never reach the server. A
request carries the partner filters, the sought sex and the visitor's own
age; the response carries every variant those three details could select
— own sex (2) x own education (not given, or one of 4) x own race (not
used, or one of 8), de-duplicated where a variant cannot differ (under
kernel_v3 a same-sex search uses no race at all, so its race variants are
one) — and the browser selects the one that applies. It never computes a
ranking number: every figure a selected row shows is in this response,
computed by the arithmetic rank() runs for that single variant. Selecting
a variant from this response and running rank() for it give the same
rows (test_variants checks every variant of several searches).

The response sends what no variant changes once:

  ranked      rows in the DEFAULT variant's order (own sex opposite the
              sought sex, education not given, race off), each without
              the parts a variant changes: rank, score, score_display,
              top_stats, summary_line and movers are absent; the match block keeps
              `available` and `unit_line`; the compatibility figure's stats
              entry keeps id, pillar and weight; the match pillar's
              contribution has value null. The balance block travels in
              variants.balance, column-wise (like values together
              compress well)
  suppressed  rows without their balance
  variants    default          the default variant's position in `list`
              sought_sex       the search's sought sex
              index            index[own sex][education or "none"]
                               [race or "off"] -> position in `list`
              same_sex_note    the sentence a same-sex figure's box carries
              match_bands      the five bands {key, label, tone} of the
                               figure's within-search standing
              explain          the distinct {top_stats, summary_line,
                               movers} entries the variants' rows point
                               at (movers since m4.2.1: [{key, sign}],
                               the pick the line names, as data)
              balance          balance_words (sought sex, other sex: the
                               key "seeker" names the other sex, the
                               seeker's own on an opposite-sex search)
                               and the balance block of every ranked row
                               (`ranked`, aligned to the rows) and
                               suppressed row — once: since m4.1.0 (ADR
                               0004 amended) balance does not depend on
                               the visitor
              list             per variant: key, sex, education,
                               race_ethnicity, match_inputs
              columns          field by field, per variant, the rows in
                               that variant's rank order: order (each row's
                               position in `ranked`), rank, score,
                               score_display, value, display, band,
                               standing, z, contribution, explain; capped
                               lists the positions whose display is capped

m4.0.0 sent the balance per own sex (variants.by_sex: balance_applies,
balance_words and every row's block, once for each sex); m4.1.0 sends it
once (variants.balance), and balance_applies is gone — balance applies to
every search.

The compatibility figure's margin (moe) is computed and returned by
rank() and never rendered (ADR 0004); the variant rows leave it out.
"""
from __future__ import annotations

from bisect import bisect_right

import numpy as np

from atlas.model.explain import (MAX_MINUSES, MAX_PLUSES, TOP_STATS_MAX, TOP_STATS_MIN_POINTS,
                                 mover_sides, mover_units, served_movers, summary_line)
from atlas.model.loader import Build
from atlas.model.preferences import EDU_LEVELS, SEX_LEVELS, SPEC_RACE, Request, seeker_weights
from atlas.model.scoring import (MATCH_COLUMN, _age_sums, _card_stats, _match_from, _match_parts,
                                 _pct_rank, balance_parts, feature_reference, match_inputs,
                                 match_normalised, match_scoring_spec, race_used, ranked_row,
                                 same_sex_note, score_components, score_from, search_frame,
                                 suppressed_row)

EDU_KEYS = ["none", *EDU_LEVELS]
RACE_KEYS = ["off", *SPEC_RACE]
# the fields of a ranked row that a variant sets (the selector's list);
# since m4.1.0 balance is not one of them (ADR 0004 amended) — it travels
# once, column-wise, in variants.balance
VARIANT_ROW_FIELDS = ("rank", "score", "score_display", "top_stats", "summary_line", "movers")
# the per-variant columns, field by field (variants.columns[name][variant]
# [position in that variant's rank order]) — field-major, so like values
# sit together and compress well
COLUMNS = ("order", "rank", "score", "score_display", "value", "display", "capped", "band",
           "standing", "z", "contribution", "explain")


def variant_key(sex: str, edu_key: str, race_key: str) -> str:
    return f"{sex}|{edu_key}|{race_key}"


def variant_list(build: Build, sought_sex: str) -> tuple[list[tuple[str, str, str]], dict]:
    """The distinct variants of a search and the full index onto them."""
    variants: list[tuple[str, str, str]] = []
    seen: dict[tuple[str, str, str], int] = {}
    index: dict = {}
    for sex in SEX_LEVELS:
        use_race = race_used(build, sex == sought_sex)
        index[sex] = {}
        for ek in EDU_KEYS:
            index[sex][ek] = {}
            for rk in RACE_KEYS:
                canon = (sex, ek, rk if use_race else "off")
                if canon not in seen:
                    seen[canon] = len(variants)
                    variants.append(canon)
                index[sex][ek][rk] = seen[canon]
    return variants, index


def default_variant(sought_sex: str) -> tuple[str, str, str]:
    """What a visitor who has told the site nothing sees: own sex opposite
    the sought sex, education not given, race off."""
    return (SEX_LEVELS[1 - SEX_LEVELS.index(sought_sex)], "none", "off")


def _display_fn(build: Build):
    """match_display (scoring) for many values: the same arithmetic —
    format_value's scaling and format, the registry ceiling and token."""
    le = build.legend["match_propensity"]
    strings = build.manifest["strings"]
    cap = float(strings["match_display_cap"])
    scale = float(le.get("display_scale", 1.0))
    nd = int(le.get("display_decimals", 1))
    capped_text = f"{cap * scale:,.{nd}f}" + strings["match_display_cap_token"]

    def display(value: float) -> tuple[str, bool]:
        shown = f"{value * scale:,.{nd}f}"
        if float(shown.replace(",", "")) > cap:
            return capped_text, True
        return shown, False
    return display


def _round_list(x: np.ndarray, nd: int) -> list[float]:
    """[round(v, nd) for v in x], vectorised. Python's round picks the
    integer k nearest the EXACT value x * 10**nd (ties to even) and returns
    the double nearest k / 10**nd; numpy's rint of the computed product
    picks the same k unless the product lies within a rounding error of a
    half — those few values go through Python's round — and k / 10**nd is
    the same correctly rounded division. So the lists are equal."""
    scale = 10.0 ** nd
    y = x * scale
    k = np.rint(y)
    out = (k / scale).tolist()
    for i in np.nonzero(np.abs(np.abs(y - np.floor(y)) - 0.5) < 1e-6)[0].tolist():
        out[i] = round(float(x[i]), nd)
    return out


def _unit_sums(C: np.ndarray, units: list[dict]) -> np.ndarray:
    """explain.unit_contributions for every row at once: each item's stats'
    rounded contributions C (n, F; NaN where missing) added in the stats'
    order — the same float additions — NaN where all of them are missing."""
    out = np.full((C.shape[0], len(units)), np.nan)
    for u, unit in enumerate(units):
        acc = np.full(C.shape[0], np.nan)
        for j in unit["cols"]:
            col = C[:, j]
            acc = np.where(np.isnan(acc), col, np.where(np.isnan(col), acc, acc + col))
        out[:, u] = acc
    return out


def _explain_codes(Cu: np.ndarray, S: np.ndarray) -> np.ndarray:
    """The movers of every row from its items' contributions Cu (n, U; NaN
    where an item's stats are all missing) and its cards' sides S (n, U):
    explain.pick_movers' rule — an item whose sign contradicts its card is
    left out; of the rest with |contribution| at least
    TOP_STATS_MIN_POINTS, taken largest first (ties in item order), at most
    MAX_PLUSES pluses and then the biggest minus (m4.2.1) — as codes
    (item + 1) * 2 + (1 if a plus), in that order, 0 where there are fewer
    movers (TOP_STATS_MAX columns)."""
    n, U = Cu.shape
    absC = np.abs(Cu)
    eligible = (absC >= TOP_STATS_MIN_POINTS) & ~(Cu * S < 0)    # NaN -> False
    key = np.where(eligible, -absC, np.inf)
    order = np.argsort(key, axis=1, kind="stable")              # largest first
    rows = np.arange(n)[:, None]
    ok = eligible[rows, order]
    plus = ok & (Cu[rows, order] > 0)
    minus = ok & (Cu[rows, order] < 0)
    # each item's place among its own sign, in that order
    take_plus = plus & (np.cumsum(plus, axis=1) <= MAX_PLUSES)
    take_minus = minus & (np.cumsum(minus, axis=1) <= MAX_MINUSES)
    codes = np.zeros((n, TOP_STATS_MAX), dtype=np.int64)
    filled = np.zeros(n, dtype=np.int64)
    for take, is_plus in ((take_plus, 1), (take_minus, 0)):
        for p in range(U):
            hit = take[:, p]
            r = np.nonzero(hit)[0]
            codes[r, filled[r]] = (order[r, p] + 1) * 2 + is_plus
            filled[r] += 1
    return codes


EXPLAIN_BASE = 64      # codes (item + 1) * 2 + sign stay below this


def _explain_key(codes: np.ndarray) -> np.ndarray:
    """A row's movers codes as one integer (base EXPLAIN_BASE digits)."""
    key = np.zeros(codes.shape[0], dtype=np.int64)
    for p in range(codes.shape[1]):
        key = key * EXPLAIN_BASE + codes[:, p]
    return key


def _explain_of_key(key: int, width: int) -> tuple[int, ...]:
    digits = []
    for _ in range(width):
        key, d = divmod(key, EXPLAIN_BASE)
        digits.append(d)
    return tuple(reversed(digits))


def _explain_entry(code: tuple[int, ...], units: list[dict]) -> dict:
    """top_stats, summary_line and movers for one movers code, through the
    same functions rank() uses: the movers go in with their order and signs
    (summary_line reads nothing else — pluses in order, the first minus)."""
    moved = []
    for p, c in enumerate(x for x in code if x):
        u, is_plus = c // 2 - 1, bool(c % 2)
        moved.append({"phrase": units[u]["phrase"], "ids": units[u]["ids"],
                      "contribution": (1.0 if is_plus else -1.0) * (TOP_STATS_MAX - p)})
    return {"top_stats": [fid for m in moved for fid in m["ids"]], "summary_line": summary_line(moved),
            "movers": served_movers(moved)}


def _strip_row(row: dict) -> dict:
    """A default-variant row without the parts a variant changes, and
    without its balance (sent once, in variants.balance)."""
    out = {k: v for k, v in row.items() if k not in VARIANT_ROW_FIELDS and k != "balance"}
    out["match"] = {"available": row["match"]["available"], "unit_line": row["match"]["unit_line"]}
    stats = list(row["stats"])
    m = stats[MATCH_COLUMN]
    assert m["id"] == "match_propensity"
    if not m.get("missing"):
        stats[MATCH_COLUMN] = {"id": m["id"], "pillar": m["pillar"], "weight": m["weight"]}
    out["stats"] = stats
    out["contributions"] = [({"pillar": "match", "value": None} if c["pillar"] == "match" else c)
                            for c in row["contributions"]]
    return out


def rank_variants(build: Build, req: Request) -> dict:
    """Every variant of the search `req` describes (its own-sex, education
    and race fields are ignored; its own age is used)."""
    fr = search_frame(build, req)
    sought = req.seeking.sex
    variants, index = variant_list(build, sought)
    d = variants.index(default_variant(sought))
    universe, ranked, suppressed, ridx = fr["universe"], fr["ranked"], fr["suppressed"], fr["ridx"]
    # m4.1.0: one balance for the search, whoever is searching
    bal = balance_parts(build, req, fr)

    # the compatibility figure for every variant: the search's side once,
    # each distinct age curve's sums once, each variant's own mixture
    parts = _match_parts(build, req)
    cache: dict = {}
    sums_by_curve: dict[int, tuple[np.ndarray, dict]] = {}
    mts = []
    for sex, ek, rk in variants:
        age_vec, W = seeker_weights(build.kernel, sex, req.self_age,
                                    None if ek == "none" else ek,
                                    None if rk == "off" else SPEC_RACE[rk],
                                    same_sex=(sex == sought), cache=cache)
        hit = sums_by_curve.get(id(age_vec))
        if hit is None or hit[0] is not age_vec:
            hit = sums_by_curve[id(age_vec)] = (age_vec, _age_sums(parts, age_vec))
        mts.append(_match_from(parts, hit[1], W))

    listed = []
    for v, (sex, ek, rk) in enumerate(variants):
        same = sex == sought
        listed.append({"key": variant_key(sex, ek, rk), "sex": sex,
                       "education": None if ek == "none" else ek,
                       "race_ethnicity": None if rk == "off" else rk,
                       "match_inputs": match_inputs(build, None if ek == "none" else ek,
                                                    None if rk == "off" else SPEC_RACE[rk],
                                                    mts[v]["national_rate"], same)})
    le = build.legend["match_propensity"]
    bands = build.manifest["standing_bands"]
    out = {"counts": {"universe": int(universe.sum()),
                      "ranked": int(ranked.sum()),
                      "shown_unranked": 0,
                      "suppressed": int(suppressed.sum()),
                      "suppressed_by_reason": fr["reasons"]},
           "weights": fr["weights"],
           "few_metros_notice": bool(ranked.sum() < 40),
           "ranked": [], "shown_unranked": [], "suppressed": [],
           "variants": {"default": d, "sought_sex": sought, "index": index,
                        "same_sex_note": same_sex_note(build),
                        "match_bands": [{"key": bands["keys"][b], "label": le["band_labels"][b],
                                         "tone": le["band_tones"][b]}
                                        for b in range(len(bands["keys"]))],
                        "explain": [],
                        "balance": {"balance_words": {"sought": bal["sought_word"],
                                                      "seeker": bal["seeker_word"]},
                                    "ranked": [], "suppressed": []},
                        "list": listed,
                        "columns": {name: [] for name in COLUMNS}}}

    if len(ridx):
        # the default variant's rows, built by rank()'s own row builder;
        # their order is the order every variant's columns follow
        mt_d = mts[d]
        sc_d = score_components(build, ridx, fr["est"][ridx], mt_d["index"][ridx], fr["weights"])
        feats, z0, raw0, w_eff0, contrib0 = sc_d["feats"], sc_d["z"], sc_d["raw"], sc_d["w_eff"], sc_d["contrib"]
        jm = MATCH_COLUMN
        assert [f["id"] for f in feats if f["pillar"] == "match"] == ["match_propensity"], \
            "the match pillar's contribution is the compatibility figure's"
        standing_d = np.column_stack([_pct_rank(raw0[:, j]) for j in range(raw0.shape[1])])
        base = np.argsort(-sc_d["score"], kind="stable")          # positions in ridx
        dsex = variants[d][0]
        for pos, k in enumerate(base):
            row = ranked_row(build, fr, bal, mt_d, sc_d, standing_d, int(ridx[k]), int(k), pos,
                             dsex == sought)
            out["variants"]["balance"]["ranked"].append(row["balance"])
            out["ranked"].append(_strip_row(row))

        others = np.array([j for j in range(len(feats)) if j != jm])
        C0 = np.full(contrib0.shape, np.nan)
        avail0 = ~np.isnan(z0)
        for j in others:
            C0[:, j] = np.where(avail0[:, j], _round_list(contrib0[:, j], 2), np.nan)
        # m4.1.1: the movers line's items (explain.mover_units) and each
        # ranked metro's cards' sides (no request changes them), by position
        # in ridx like C0
        units = mover_units([f["id"] for f in feats], build.legend)
        assert 2 * (len(units) + 1) <= EXPLAIN_BASE
        side_memo = build.memo.setdefault(("mover_sides", tuple(u["phrase"] for u in units)), {})
        for i in ridx.tolist():
            if i not in side_memo:
                side_memo[i] = mover_sides(units, build.legend, _card_stats(build, i), bands["keys"])
        S0 = np.array([side_memo[i] for i in ridx.tolist()], dtype=float).reshape(len(ridx), len(units))
        rule, spec = match_scoring_spec(build)
        ref0 = sc_d["ref"]
        display = _display_fn(build)
        edges = bands["edges"]
        explain_ix: dict[int, int] = {}
        explain_memo = build.memo.setdefault(("explain_units", tuple(u["phrase"] for u in units)), {})
        n = len(ridx)
        base_pos = np.empty(n, dtype=int)
        base_pos[base] = np.arange(n)
        cols = out["variants"]["columns"]
        for v, mt in enumerate(mts):
            m = mt["index"][ridx]
            z = z0.copy()
            z[:, jm] = match_normalised(m, rule, spec)
            # the figure's availability is the same in every variant (the
            # pool's denominator decides it), and the effective weights read
            # nothing else of z: they are the default variant's
            assert np.array_equal(np.isnan(z[:, jm]), np.isnan(z0[:, jm]))
            w_eff = w_eff0
            ref = ref0.copy()
            ref[jm] = feature_reference(z, jm)
            sc = score_from(z, w_eff, ref)
            assert np.array_equal(sc["contrib"][:, others], contrib0[:, others], equal_nan=True)
            st = _pct_rank(m)
            # this variant's rows in its own rank order (the columns below
            # follow it; `order` names each row's position in `ranked`)
            order = np.argsort(-sc["score"], kind="stable")          # positions in ridx
            score_o = sc["score"][order]
            okp = np.nonzero(~np.isnan(z[order, jm]))[0]
            cols["order"].append(base_pos[order].tolist())
            cols["rank"].append(list(range(1, n + 1)))
            cols["score"].append(_round_list(score_o, 1))
            # round(x) to a whole number reads x exactly, as rint does
            cols["score_display"].append([str(int(x)) for x in np.rint(score_o).tolist()])
            per = {name: [None] * n for name in ("value", "display", "band", "standing", "z",
                                                 "contribution")}
            capped = []
            if len(okp):
                mo, sto = m[order][okp], st[order][okp]
                for name, vals in (("value", _round_list(mo, 2)),
                                   ("standing", _round_list(sto, 1)),
                                   ("z", _round_list(z[order, jm][okp], 2)),
                                   ("contribution", _round_list(sc["contrib"][order, jm][okp], 2))):
                    col = per[name]
                    for p, x in zip(okp.tolist(), vals):
                        col[p] = x
                for p, x, s_ in zip(okp.tolist(), mo.tolist(), sto.tolist()):
                    txt, cap = display(x)
                    per["display"][p] = txt
                    if cap:
                        capped.append(p)
                    per["band"][p] = bisect_right(edges, s_)
            for name, vals in per.items():
                cols[name].append(vals)
            cols["capped"].append(capped)
            # the explanation: the rounded contributions, this variant's
            # figure in its column, through explain.pick_movers' rule
            C = C0[order].copy()
            C[:, jm] = [np.nan if c is None else c for c in per["contribution"]]
            keys = _explain_key(_explain_codes(_unit_sums(C, units), S0[order]))
            uniq, inverse = np.unique(keys, return_inverse=True)
            slots = []
            for key in uniq.tolist():
                if key not in explain_ix:
                    if key not in explain_memo:
                        explain_memo[key] = _explain_entry(_explain_of_key(key, TOP_STATS_MAX), units)
                    explain_ix[key] = len(out["variants"]["explain"])
                    out["variants"]["explain"].append(explain_memo[key])
                slots.append(explain_ix[key])
            cols["explain"].append([slots[i] for i in np.asarray(inverse).reshape(-1).tolist()])

    for i in np.where(suppressed)[0]:
        row = suppressed_row(build, fr, bal, int(i))
        out["variants"]["balance"]["suppressed"].append(row.pop("balance"))
        out["suppressed"].append(row)
    return out


def select_variant(resp: dict, sex: str | None = None, education: str | None = None,
                   race: str | None = None) -> dict:
    """The browser's selector, in Python (the reference the web's
    lib/variants.ts is tested against, and what test_variants compares with
    rank()): one variant's rows, copied — never computed — from the
    response. `sex` None is the sought sex's opposite; `race` is a spec id
    and None means race off."""
    V = resp["variants"]
    sought = V["sought_sex"]
    sex = sex or SEX_LEVELS[1 - SEX_LEVELS.index(sought)]
    vi = V["index"][sex][education or "none"][race or "off"]
    v = V["list"][vi]
    col = {name: V["columns"][name][vi] for name in COLUMNS} if resp["ranked"] else {}
    same = sex == sought
    bal = V["balance"]          # the search's, whoever is searching (m4.1.0)
    rows = []
    for p, b in enumerate(col.get("order", [])):
        base = resp["ranked"][b]
        row = dict(base)
        row["rank"] = col["rank"][p]
        row["score"] = col["score"][p]
        row["score_display"] = col["score_display"][p]
        row["balance"] = bal["ranked"][b]
        match = {"available": base["match"]["available"], "value": col["value"][p],
                 "display": col["display"][p], "capped": p in col["capped"],
                 "unit_line": base["match"]["unit_line"]}
        if same:
            match["note"] = V["same_sex_note"]
        stats = list(base["stats"])
        if col["band"][p] is not None:
            bd = V["match_bands"][col["band"][p]]
            band = {"key": bd["key"], "standing_all": col["standing"][p], "label": bd["label"],
                    "tone": bd["tone"]}
            match["band"] = band
        if not stats[MATCH_COLUMN].get("missing"):
            entry = {**stats[MATCH_COLUMN], "value": col["value"][p], "display": col["display"][p],
                     "standing": col["standing"][p], "z": col["z"][p],
                     "contribution": col["contribution"][p]}
            if col["band"][p] is not None:
                entry["band"] = band
            stats[MATCH_COLUMN] = entry
        row["match"] = match
        row["stats"] = stats
        row["contributions"] = [({"pillar": "match", "value": col["contribution"][p]}
                                 if c["pillar"] == "match" else c) for c in base["contributions"]]
        ex = V["explain"][col["explain"][p]]
        row["top_stats"] = ex["top_stats"]
        row["summary_line"] = ex["summary_line"]
        row["movers"] = ex["movers"]
        rows.append(row)
    if resp.get("sort") == "worst_first":
        rows.reverse()
    out = {k: val for k, val in resp.items() if k not in ("ranked", "suppressed", "variants")}
    out.update({"balance_words": bal["balance_words"],
                "match_inputs": v["match_inputs"], "ranked": rows,
                "suppressed": [{**row, "balance": bal["suppressed"][j]}
                               for j, row in enumerate(resp["suppressed"])]})
    return out
