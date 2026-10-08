"""Phase 5: the movers line before (m4.2.0) and after (m4.2.1) for the two
reference searches — the top 5, 5 from the middle and the bottom 5 of the
default variant — read from the served-numbers records.

    python3 atlas/results/phase5/movers_examples.py <before.json> <after.json>
        -> atlas/results/phase5/movers_examples.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
a, b = (json.loads(Path(p).read_text()) for p in sys.argv[1:3])
out = {"before": a["model_version"], "after": b["model_version"], "searches": {}}
for name in ("default", "same_sex_reference"):
    ra, rb = a["reference"][name]["rows"], b["reference"][name]["rows"]
    assert [r["cbsa"] for r in ra] == [r["cbsa"] for r in rb]
    n = len(rb)
    mid = n // 2 - 2
    picks = list(range(5)) + list(range(mid, mid + 5)) + list(range(n - 5, n))
    out["searches"][name] = {
        "body": b["reference"][name]["body"], "ranked": n,
        "rows": [{"rank": rb[i]["rank"], "metro": rb[i]["metro"], "score": rb[i]["score"],
                  "before": ra[i]["summary_line"], "after": rb[i]["summary_line"]} for i in picks],
        "top10_after": [rb[i]["summary_line"] for i in range(10)],
    }
(HERE / "movers_examples.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
for name, s in out["searches"].items():
    print(f"## {name} ({s['ranked']} ranked)")
    for r in s["rows"]:
        print(f"{r['rank']:>3} {r['metro']:<24} | {r['before']}  ->  {r['after']}")
    print("top 10 identical lines:", len(set(s["top10_after"])), set(s["top10_after"]))
