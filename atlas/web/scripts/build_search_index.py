"""Generate src/data/search-index.json (§8.3): CBSA names, principal-city
and state tokens parsed from the pinned delineation titles, plus
hand-written colloquials. Shipped to the client and fuzzy-matched in the
browser — no server round-trip, no search infrastructure.

    python scripts/build_search_index.py [build_dir]

The index derives from the build's metros.json (the pinned delineation),
never a hand-typed metro list. Committed because CI has no build artifact;
regenerate whenever the delineation vintage changes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
DEFAULT_BUILD = WEB.parents[1] / "atlas" / "data" / "builds" / "dc23609755ad"

# Hand-written colloquials (§8.3 names these examples explicitly).
COLLOQUIAL = {
    "35620": ["NYC", "New York City", "Manhattan", "Brooklyn", "Queens", "the Bronx"],
    "41860": ["the Bay Area", "SF", "San Francisco Bay", "East Bay", "Oakland"],
    "41940": ["Silicon Valley", "South Bay"],
    "19100": ["DFW", "the Metroplex"],
    "33460": ["Twin Cities", "MSP"],
    "39580": ["the Triangle", "Raleigh-Durham"],
    "20500": ["the Triangle", "Raleigh-Durham"],
    "16980": ["Chicagoland"],
    "31080": ["LA", "Los Angeles"],
    "47900": ["DC", "the DMV", "Washington DC"],
    "14460": ["Boston"],
    "42660": ["Seattle", "Puget Sound"],
    "38060": ["Phoenix", "Valley of the Sun"],
    "26420": ["Houston", "H-Town"],
    "12060": ["Atlanta", "ATL"],
    "33100": ["Miami", "South Florida"],
    "37980": ["Philadelphia", "Philly"],
    "40140": ["the Inland Empire", "IE"],
    "29820": ["Las Vegas", "Vegas"],
    "19740": ["Denver", "the Front Range"],
    "38900": ["Portland", "PDX"],
    "34980": ["Nashville", "Music City"],
    "41180": ["St. Louis", "STL"],
    "28140": ["Kansas City", "KC"],
    "45300": ["Tampa Bay"],
    "35380": ["New Orleans", "NOLA", "the Big Easy"],
    "46520": ["Honolulu", "Oahu"],
    "12420": ["Austin", "ATX"],
    "17140": ["Cincinnati", "Cincy"],
    "38300": ["Pittsburgh"],
    "19820": ["Detroit", "Motor City"],
    "26900": ["Indianapolis", "Indy"],
    "40900": ["Sacramento", "Sactown"],
    "41620": ["Salt Lake City", "SLC"],
    "36420": ["Oklahoma City", "OKC"],
    "27260": ["Jacksonville", "Jax"],
    "10740": ["Albuquerque", "ABQ"],
}


def tokens_from_title(title: str) -> list[str]:
    name, _, states = title.rpartition(", ")
    toks = [t.strip() for t in re.split(r"[-–—]", name) if t.strip()]
    toks += [s.strip() for s in states.split("-") if s.strip()]
    return toks


def main() -> None:
    build_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BUILD
    metros = json.loads((build_dir / "metros.json").read_text())
    rows = []
    for m in metros:
        toks = tokens_from_title(m["title"]) + COLLOQUIAL.get(m["cbsa"], [])
        seen, keep = set(), []
        for t in toks:
            k = t.lower()
            if k not in seen:
                seen.add(k)
                keep.append(t)
        rows.append({"c": m["cbsa"], "t": m["title"], "r": m["ranked_set"],
                     "k": keep})
    out = WEB / "src" / "data" / "search-index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=False)
    out.write_text(payload + "\n", encoding="utf-8")
    print(f"{out}: {len(rows)} metros, {len(payload)/1024:.1f} KB")


if __name__ == "__main__":
    main()
