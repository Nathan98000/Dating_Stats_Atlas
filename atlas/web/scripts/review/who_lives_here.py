# The "Who lives here" card for all 387 metros, from POST /v1/profile on build 63c4e5fa51bf:
# the served value, its display, its unit line, how far the display sits from the value,
# and the adult share the two rounded figures imply.   python3 who_lives_here.py -> who_lives_here.json
import json, re, urllib.request
API = "http://127.0.0.1:8000"
meta = json.load(urllib.request.urlopen(API + "/v1/meta"))
def num(s):
    s = s.replace(",", ""); m = re.match(r"([\d.]+)\s*(million)?", s)
    return float(m.group(1)) * (1e6 if m.group(2) else 1)
rows = []
for m in meta["metros"]:
    req = urllib.request.Request(API + "/v1/profile", data=json.dumps({"cbsa": m["cbsa"]}).encode(), headers={"content-type": "application/json"})
    c = [c for c in json.load(urllib.request.urlopen(req))["cards"] if c["id"] == "who_lives_here"][0]
    shown = num(c["display"]); ad = re.search(r"of whom ([\d.,]+(?: million)?)", c["unit_line"])
    adults = num(ad.group(1)) if ad else None
    rows.append({"metro": m["display_name"], "ranked": m["ranked_set"], "value": round(c["value"]), "display": c["display"],
                 "unit_line": c["unit_line"], "description": m["description"],
                 "display_vs_value_pct": round((shown / c["value"] - 1) * 100, 1),
                 "implied_adult_share": round(adults / shown, 2) if adults else None})
json.dump(rows, open("who_lives_here.json", "w"), indent=1)
print(len(rows), "metros; display off by >=10%:", sum(abs(r["display_vs_value_pct"]) >= 10 for r in rows),
      "; implied adult share <0.6:", sum((r["implied_adult_share"] or 1) < 0.6 for r in rows))
