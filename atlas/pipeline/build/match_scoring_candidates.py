"""Phase 3d B2 (ADR 0013): measure the four match-scoring candidates on
one build — the rule is committed before this runs and nothing here is
tuned to its results.

For each of N0, V1, V2 and V3 (the build's manifest switched in memory,
nothing on disk changes):

- the ADR 0011 gate's verdict and ratio against the m3.2.0 reference (a
  scoring-only change touches no index, so the totals run over every
  search, as the rule says);
- total wobble over the gate's own set and over the MATCH-END set (every
  ADR 0011 test search without explicit weights, re-sent with
  pool_vs_match = 1.0);
- the outlier condition: on every search of both sets the middle 80% of
  ranked cities keep at least OUTLIER_MIN_SPREAD points of match-score
  spread (10th to 90th percentile of the feature's normalised value);
  the worst searches are named;
- how much matching still steers: Kendall's tau between each search's
  ranking and its match-index order, at the searches' own slider
  positions and at the match end (reported, not gated);
- the disclosed reference searches' top city and top five.

Then the selection rule, ADR 0013 as amended after Phase 3d (`select`, a
pure function of the candidates' records, which main calls): a difference
in match-end wobble smaller than MATCH_END_MARGIN (5%) of N0's total is no
difference. A candidate qualifies if it passes the gate, meets the outlier
condition and its match-end total is at least 5% of N0's total below
N0's; of the qualifying, the lowest match-end total and every candidate
within 5% of N0's total of it are tied for first, and of those the lower
total wobble over the gate's own set ships, an exact tie to the earlier
candidate in the table; none qualifying ships nothing. B2 ran (after
4bab576) under the rule as drafted — below N0's total qualifies, the
lowest ships — because the margin reached the repo only after the
measurement; results/phase3d/b2_selection_with_margin.py reads the stored
B2 records under this function, the drafted reading beside it.

    python -m atlas.pipeline.build.match_scoring_candidates <build_dir> [--rules N0,V1,V2,V3] [--out results/phase3d]
        -> <out>/b2_candidates.json, <out>/b2_gate_<rule>.json, <out>/b2_matchend_<rule>.json
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from atlas import model as engine
from atlas.pipeline.build import stability_gate as SG
from atlas.pipeline.build.phase3b_snapshot import DEFAULT, REFERENCE
from atlas.pipeline.fetch import RESULTS

RULES = ("N0", "V1", "V2", "V3")
OUTLIER_MIN_SPREAD = 40.0          # points of match-score spread, p10 to p90, half of what a percentile rank gives
# ADR 0013, amended after Phase 3d: a difference in match-end wobble smaller
# than this share of N0's match-end total is no difference — well above
# what changes that leave the scoring alone moved (1% or less), half the
# gate's 10% line, about a third of the match-end rise Part B answers.
# Nathan set it before any candidate was measured; the brief that reached
# the repo lacked it, so it is committed after B2, and the amendment says so.
MATCH_END_MARGIN = 0.05
WORST_N = 5
DISCLOSED = ("grad_asian_woman_30", "grad_asian_man_34", "black_woman_30", "nhpi_man_35", "nhpi_woman_35")


def with_rule(build, rule: str):
    m = json.loads(json.dumps(build.manifest))
    block = dict(m.get("normalization") or {})
    assert block, "the build must carry the registry's normalization block (ADR 0013)"
    block["match_scoring"] = rule
    m["normalization"] = block
    return replace(build, manifest=m)


def match_end_searches() -> list[tuple[str, dict]]:
    """Every ADR 0011 test search that does not send explicit weights,
    re-sent with pool_vs_match = 1.0 (the deprecated pool_vs_balance alias
    is replaced, since the two controls cannot both be sent)."""
    out = []
    for name, body in SG.test_searches():
        if "weights" in body:
            continue
        b = {k: v for k, v in body.items() if k != "pool_vs_balance"}
        b["pool_vs_match"] = 1.0
        out.append((name, b))
    return out


def outlier_reading(rec: dict) -> dict:
    live = {n: r for n, r in rec["searches"].items() if "skipped" not in r and r.get("match_score_spread_p10_p90") is not None}
    worst = sorted(live.items(), key=lambda kv: kv[1]["match_score_spread_p10_p90"])[:WORST_N]
    fails = [n for n, r in live.items() if r["match_score_spread_p10_p90"] < OUTLIER_MIN_SPREAD]
    return {"searches": len(live), "min_spread": min(r["match_score_spread_p10_p90"] for r in live.values()),
            "median_spread": float(np.median([r["match_score_spread_p10_p90"] for r in live.values()])),
            "searches_below_min": len(fails), "passes": len(fails) == 0,
            "worst": [{"search": n, "spread": r["match_score_spread_p10_p90"]} for n, r in worst]}


def steering(rec: dict) -> dict:
    taus = [r["steering_tau"] for r in rec["searches"].values() if "skipped" not in r and r.get("steering_tau") is not None]
    return {"searches": len(taus), "tau_median": float(np.median(taus)), "tau_p10": float(np.percentile(taus, 10)),
            "tau_p90": float(np.percentile(taus, 90)), "tau_min": float(min(taus))}


def tops(build, rule: str) -> dict:
    out = {}
    for name in DISCLOSED:
        body = REFERENCE[name]
        res = engine.rank(with_rule(build, rule), engine.parse_request(body))
        end = engine.rank(with_rule(build, rule), engine.parse_request({**body, "pool_vs_match": 1.0}))
        out[name] = {"top": res["ranked"][0]["display_name"],
                     "top5": [r["display_name"] for r in res["ranked"][:5]],
                     "top5_index": [r["match"]["display"] for r in res["ranked"][:5]],
                     "match_end_top": end["ranked"][0]["display_name"],
                     "match_end_top5": [r["display_name"] for r in end["ranked"][:5]]}
    return out


def select(records: dict[str, dict], margin: float = MATCH_END_MARGIN) -> dict:
    """ADR 0013's selection, as amended after Phase 3d — a pure function of
    the candidates' records, which main calls after measuring and
    results/phase3d/b2_selection_with_margin.py calls on the stored B2
    records. `records` maps each rule measured to its record as main writes
    it (gate.pass, outlier_condition.passes, match_end_wobble_total,
    gate_set_wobble_total); N0, the control, must be among them or nothing
    can qualify.

    A difference in match-end wobble smaller than `margin` x N0's total is
    no difference. A candidate qualifies if it passes the ADR 0011 gate,
    meets the outlier condition and its match-end total is at least
    `margin` x N0's total below N0's; N0 never qualifies. Of the qualifying
    candidates the lowest match-end total is found, and it and every
    qualifying candidate less than `margin` x N0's total above it are tied
    for first (a difference of exactly the margin is a difference, as at
    qualification); of those, the lower total wobble over the gate's own
    set ships, an exact tie to the earlier candidate in ADR 0013's table
    (RULES). None qualifying ships nothing."""
    n0 = records.get("N0")
    n0_total = float(n0["match_end_wobble_total"]) if n0 else None
    margin_places = margin * n0_total if n0 else None
    order = sorted(records, key=RULES.index)
    reading = {}
    for rule in order:
        r = records[rule]
        total = float(r["match_end_wobble_total"])
        below = n0_total - total if n0 else None
        c = {"match_end_wobble_total": total, "gate_set_wobble_total": float(r["gate_set_wobble_total"]),
             "gate_pass": bool(r["gate"]["pass"]), "outlier_condition_passes": bool(r["outlier_condition"]["passes"]),
             "match_end_reduction_vs_N0_places": below,
             "match_end_reduction_vs_N0_fraction": below / n0_total if n0 else None,
             "at_least_margin_below_N0": bool(n0 and below >= margin_places), "tied_for_first": False}
        c["qualifies"] = bool(rule != "N0" and c["gate_pass"] and c["outlier_condition_passes"]
                              and c["at_least_margin_below_N0"])
        reading[rule] = c
    qualifying = [rule for rule in order if reading[rule]["qualifies"]]
    out = {"margin_fraction": margin, "margin_places": margin_places, "N0_match_end_total": n0_total,
           "candidates": reading, "qualifying": qualifying, "lowest_match_end": None, "tie_band": None,
           "tied_for_first": [], "ships": None, "settled_by": None}
    if not qualifying:
        out["settled_by"] = "no candidate qualifies: nothing ships"
        return out
    first = min(qualifying, key=lambda rule: reading[rule]["match_end_wobble_total"])    # exact ties in table order
    lowest = reading[first]["match_end_wobble_total"]
    tied = [rule for rule in qualifying
            if rule == first or reading[rule]["match_end_wobble_total"] - lowest < margin_places]
    for rule in tied:
        reading[rule]["tied_for_first"] = True
    fewest = min(reading[rule]["gate_set_wobble_total"] for rule in tied)
    steadiest = [rule for rule in tied if reading[rule]["gate_set_wobble_total"] == fewest]
    out.update(lowest_match_end=first, tied_for_first=tied, ships=steadiest[0],
               tie_band={"from": lowest, "below": lowest + margin_places})
    out["settled_by"] = ("one candidate qualifies" if len(qualifying) == 1
                         else "the lowest match-end total: no other qualifying candidate within the margin" if len(tied) == 1
                         else "the lower gate-set total among those tied for first" if len(steadiest) == 1
                         else "an exact tie on the gate-set total: the earlier candidate in the table")
    return out


def main(argv: list[str]) -> int:
    from atlas.pipeline.build.pool import open_pool
    build_dir = argv[0]
    opt = {argv[i]: argv[i + 1] for i in range(1, len(argv) - 1, 2) if argv[i].startswith("--")}
    rules = tuple(opt.get("--rules", ",".join(RULES)).split(","))
    out_dir = Path(opt.get("--out", RESULTS / "phase3d"))
    out_dir.mkdir(parents=True, exist_ok=True)
    build = engine.load_build(build_dir, allow_model_mismatch=True)
    ref = SG.load_reference()
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    end_set = match_end_searches()
    t0 = time.time()
    out = {"build": build.manifest["data_version"], "model_version": engine.MODEL_VERSION,
           "kernel": (build.kernel.meta or {}).get("generated_at"),
           "reference_build": ref["build"], "rules": {}, "outlier_min_spread": OUTLIER_MIN_SPREAD,
           "match_end_set": {"searches": len(end_set),
                             "definition": "every ADR 0011 test search without explicit weights, pool_vs_match = 1.0"},
           "match_end_margin": MATCH_END_MARGIN,
           "selection_rule": f"ADR 0013 as amended after Phase 3d: a difference in match-end wobble smaller than "
                             f"{MATCH_END_MARGIN:.0%} of N0's total is no difference. Qualifies if: gate pass; outlier "
                             f"condition on both sets; match-end total at least {MATCH_END_MARGIN:.0%} of N0's total "
                             f"below N0's (N0 never qualifies). The lowest qualifying match-end total and every "
                             f"qualifier within {MATCH_END_MARGIN:.0%} of N0's total of it tie for first; of those the "
                             f"lower gate-set total ships; an exact tie to the earlier candidate in the table; "
                             f"none -> nothing ships."}
    try:
        for rule in rules:
            b = with_rule(build, rule)
            gate = SG.gate_record(b, con, name=f"b2:{rule}", verbose=False)
            gate["verdict"] = SG.verdict(gate, ref)
            SG._write(out_dir / f"b2_gate_{rule}.json", gate)
            end = SG.gate_record(b, con, name=f"b2:{rule}:match_end", searches=end_set, verbose=False)
            SG._write(out_dir / f"b2_matchend_{rule}.json", end)
            v = gate["verdict"]
            out["rules"][rule] = {
                "gate": {k: v[k] for k in ("pass", "ratio", "basis", "searches_touched", "wobble_candidate",
                                           "wobble_reference", "ratio_over_all_searches")},
                "gate_old_rule_min_share_personas": v["old_rule"]["min_share_personas"],
                "gate_set_wobble_total": gate["totals"]["wobble_sum"],
                "gate_set_wobble_median": gate["totals"]["wobble_median"],
                "match_end_wobble_total": end["totals"]["wobble_sum"],
                "match_end_wobble_median": end["totals"]["wobble_median"],
                "match_end_wobble_max": end["totals"]["wobble_max"],
                "outlier_condition": {"own_slider": outlier_reading(gate), "match_end": outlier_reading(end)},
                "steering_tau": {"own_slider": steering(gate), "match_end": steering(end)},
                "disclosed_searches": tops(build, rule),
                "seconds": round(time.time() - t0, 1)}
            r = out["rules"][rule]
            r["outlier_condition"]["passes"] = bool(r["outlier_condition"]["own_slider"]["passes"]
                                                    and r["outlier_condition"]["match_end"]["passes"])
            print(json.dumps({"rule": rule, "gate": r["gate"]["pass"], "ratio": r["gate"]["ratio"],
                              "match_end": r["match_end_wobble_total"], "gate_set": r["gate_set_wobble_total"],
                              "outlier": r["outlier_condition"]["passes"],
                              "min_spread": [r["outlier_condition"]["own_slider"]["min_spread"],
                                             r["outlier_condition"]["match_end"]["min_spread"]],
                              "tau_median": [r["steering_tau"]["own_slider"]["tau_median"],
                                             r["steering_tau"]["match_end"]["tau_median"]]}), flush=True)
    finally:
        con.close()
    sel = select(out["rules"])
    for rule, r in out["rules"].items():
        c = sel["candidates"][rule]
        r.update({k: c[k] for k in ("match_end_reduction_vs_N0_fraction", "at_least_margin_below_N0",
                                    "tied_for_first", "qualifies")})
    out["selection"] = {k: v for k, v in sel.items() if k != "candidates"}
    qual, winner = sel["qualifying"], sel["ships"]
    out["qualifying"] = qual
    out["ships"] = winner
    out["seconds"] = round(time.time() - t0, 1)
    (out_dir / "b2_candidates.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    print(json.dumps({"qualifying": qual, "ships": winner, "seconds": out["seconds"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
