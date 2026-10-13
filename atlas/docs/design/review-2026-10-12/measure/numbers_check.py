"""Round 4 (12 October 2026): how the served numbers read side by side.

For three searches, over every ranked city, in the variant a first-time visitor sees
(own sex from the default, no education, race off), this reads only served values:

1. The "What moved the score" bars against the "median N" tick. The bars are measured
   from a reference built from each stat's median (ADR 0003, decision 1), not from the
   median city's score. What a visitor gets by adding the bars to the tick
   (median display + sum of displayed bars) is compared with the score shown.
2. The lifestyle chips against the bars: a chip whose sign is the opposite of its
   pillar's bar (e.g. "▼ Rent" over "Cost of living · everyday prices, rent +2.0").
3. Balance: how many ranked cities share one displayed figure.

Nothing here computes a figure for display; it only compares served ones.
Run: python3 numbers_check.py [api_base]  -> numbers_check.json
"""
import collections
import json
import sys
import urllib.request

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100"
SEARCHES = {
    "default (woman 30, men 28-40)": (
        {"self": {"age": 30}, "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married", "previously_married"]},
         "pool_vs_match": 0.4545, "importance": {"cost": "some", "reach": "some", "students": "some", "weather": "some"}},
        "female"),
    "task 2 (cost, weather a lot; social not much)": (
        {"self": {"age": 30}, "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married", "previously_married"]},
         "pool_vs_match": 0.4545, "importance": {"cost": "a_lot", "reach": "not_much", "students": "some", "weather": "a_lot"}},
        "female"),
    "same-sex (man 33, men 28-38)": (
        {"self": {"age": 33}, "seeking": {"sex": "male", "age": [28, 38], "marital": ["never_married", "previously_married"]},
         "pool_vs_match": 0.4545, "importance": {"cost": "some", "reach": "some", "students": "some", "weather": "some"}},
        "male"),
}


def post(body):
    req = urllib.request.Request(API + "/v1/rank", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=60))


out = {}
for label, (body, own_sex) in SEARCHES.items():
    d = post(body)
    V = d["variants"]
    vi = V["index"][own_sex]["none"]["off"]
    c = V["columns"]
    med = V["list"][vi]["score_median"]
    rows = []
    for p, b in enumerate(c["order"][vi]):
        base = d["ranked"][b]
        pillar_of = {s["id"]: s["pillar"] for s in base["stats"]}
        contrib = {x["pillar"]: x["value"] for x in base["contributions"]}
        contrib["match"] = c["contribution"][vi][p]
        shown_bars = {k: round(v, 1) for k, v in contrib.items() if v is not None}
        bar_sum = round(sum(shown_bars.values()), 1)
        score = c["score"][vi][p]
        score_shown = int(c["score_display"][vi][p])
        ex = V["explain"][c["explain"][vi][p]]
        # the price pair is one chip (everyday prices) under the cost pillar
        chips = [(m["key"], m["sign"], pillar_of.get(m["key"], "cost")) for m in ex["lifestyle_movers"]]
        against = [f'{"▲" if s > 0 else "▼"} {k} vs {p_} bar {shown_bars.get(p_)}'
                   for k, s, p_ in chips if shown_bars.get(p_) is not None and shown_bars[p_] * s < 0]
        rows.append({
            "rank": c["rank"][vi][p], "city": base["display_name"], "score_shown": score_shown,
            "bars": shown_bars, "bar_sum": bar_sum,
            "reference_implied": round(score - sum(v for v in contrib.values() if v is not None), 2),
            "median_plus_bars": int(med["display"]) + bar_sum,
            "gap_vs_shown": round(int(med["display"]) + bar_sum - score_shown, 1),
            "chips_against_bars": against,
            "balance": V["balance"]["ranked"][b]["display"] if V["balance"]["ranked"][b].get("available") else None,
        })
    gaps = [abs(r["gap_vs_shown"]) for r in rows]
    bal = collections.Counter(r["balance"] for r in rows)
    out[label] = {
        "variant": V["list"][vi]["key"],
        "score_median": med,
        "reference_implied_range": [min(r["reference_implied"] for r in rows), max(r["reference_implied"] for r in rows)],
        "median_plus_bars_vs_score": {
            "max_abs_gap": max(gaps), "rows_off_by_1_or_more": sum(g >= 1 for g in gaps),
            "rows_off_by_2_or_more": sum(g >= 2 for g in gaps), "rows": len(rows)},
        "chips_against_their_bar": {"rows": sum(bool(r["chips_against_bars"]) for r in rows),
                                    "top_20": sum(bool(r["chips_against_bars"]) for r in rows[:20]),
                                    "examples": [(r["rank"], r["city"], r["chips_against_bars"]) for r in rows if r["chips_against_bars"]][:12]},
        "balance_most_shared": bal.most_common(5),
        "top_10": [{k: r[k] for k in ("rank", "city", "score_shown", "bar_sum", "gap_vs_shown", "chips_against_bars", "balance")} for r in rows[:10]],
        "cities": {r["city"]: r for r in rows if r["city"] in ("Austin, TX", "Denver, CO", "San Francisco, CA", "Houston, TX")},
    }
    print(label, json.dumps({k: out[label][k] for k in ("score_median", "reference_implied_range", "median_plus_bars_vs_score", "balance_most_shared")}))
    print("  chips against bar:", out[label]["chips_against_their_bar"]["rows"], "of", len(rows), "| top 20:", out[label]["chips_against_their_bar"]["top_20"])

json.dump(out, open("numbers_check.json", "w"), indent=1, ensure_ascii=False)
