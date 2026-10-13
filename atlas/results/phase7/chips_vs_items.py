"""Phase 7 (R05): every lifestyle chip against its own item's served bar, for the
round-4 review's three searches (its measure/numbers_check.py), in the variant a
first-time visitor sees. A chip's item is the unit_contributions entry with the
chip's key (cost of living and social life by item; weather and student life are
one item each). Reads only served values. It measured Phase 7's build: the API stopped
serving unit_contributions on 13 October 2026 (Nathan), so it no longer runs against it.

    python3 results/phase7/chips_vs_items.py [api_base] > results/phase7/after/chips_vs_items.json
"""
import json
import sys
import urllib.request

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100"
BASE = {"self": {"age": 30}, "seeking": {"sex": "male", "age": [28, 40],
        "marital": ["never_married", "previously_married"]}, "pool_vs_match": 0.4545}
SEARCHES = {
    "default (woman 30, men 28-40)": ({**BASE, "importance": {"cost": "some", "reach": "some", "students": "some", "weather": "some"}}, "female"),
    "task 2 (cost, weather a lot; social not much)": ({**BASE, "importance": {"cost": "a_lot", "reach": "not_much", "students": "some", "weather": "a_lot"}}, "female"),
    "same-sex (man 33, men 28-38)": ({"self": {"age": 33}, "seeking": {"sex": "male", "age": [28, 38], "marital": ["never_married", "previously_married"]},
                                      "pool_vs_match": 0.4545, "importance": {"cost": "some", "reach": "some", "students": "some", "weather": "some"}}, "male"),
}
out = {}
for label, (body, own) in SEARCHES.items():
    req = urllib.request.Request(API + "/v1/rank", data=json.dumps(body).encode(), headers={"content-type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    V = d["variants"]
    vi = V["index"][own]["none"]["off"]
    chips = against = rows_against = missing = 0
    top20 = 0
    for pos, b in enumerate(V["columns"]["order"][vi]):
        row = d["ranked"][b]
        units = {u["key"]: u["value"] for u in row["unit_contributions"]}
        ex = V["explain"][V["columns"]["explain"][vi][pos]]
        bad = 0
        for m in ex["lifestyle_movers"]:
            chips += 1
            if m["key"] not in units:
                missing += 1
            elif m["sign"] * units[m["key"]] <= 0:
                bad += 1
        against += bad
        rows_against += bool(bad)
        top20 += bool(bad) and pos < 20
    out[label] = {"rows": len(V["columns"]["order"][vi]), "chips": chips, "chips_against_their_item_bar": against,
                  "rows_with_a_chip_against_its_item_bar": rows_against, "top_20": top20, "chips_without_an_item": missing}
print(json.dumps(out, indent=1))
