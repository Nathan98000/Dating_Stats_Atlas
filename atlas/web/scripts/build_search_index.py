"""Generate src/data/search-index.json (§8.3): city display names, city
and state tokens from the pinned delineation, plus hand-written
colloquials. Shipped to the client and fuzzy-matched in the browser — no
server round-trip. m2.0.0: entries are keyed by SLUG and never carry a
CBSA code (no code reaches a page).

    python scripts/build_search_index.py [build_dir]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
DEFAULT_BUILD = WEB.parents[1] / "atlas" / "data" / "builds" / "2c8d7285c720"

COLLOQUIAL = {
    "new-york-new-york": ["NYC", "New York City", "Manhattan", "Brooklyn", "Queens", "the Bronx"],
    "san-francisco-california": ["the Bay Area", "SF", "San Francisco Bay", "East Bay", "Oakland"],
    "san-jose-california": ["Silicon Valley", "South Bay"],
    "dallas-texas": ["DFW", "the Metroplex", "Fort Worth"],
    "minneapolis-minnesota": ["Twin Cities", "MSP", "St. Paul"],
    "raleigh-north-carolina": ["the Triangle", "Raleigh-Durham"],
    "durham-north-carolina": ["the Triangle", "Raleigh-Durham"],
    "chicago-illinois": ["Chicagoland"],
    "los-angeles-california": ["LA"],
    "washington-district-of-columbia": ["DC", "the DMV", "Washington DC"],
    "seattle-washington": ["Puget Sound", "Tacoma"],
    "phoenix-arizona": ["Valley of the Sun", "Mesa", "Scottsdale"],
    "houston-texas": ["H-Town"],
    "atlanta-georgia": ["ATL"],
    "miami-florida": ["South Florida", "Fort Lauderdale"],
    "philadelphia-pennsylvania": ["Philly"],
    "riverside-california": ["the Inland Empire", "IE"],
    "las-vegas-nevada": ["Vegas"],
    "denver-colorado": ["the Front Range"],
    "portland-oregon": ["PDX"],
    "nashville-tennessee": ["Music City"],
    "st-louis-missouri": ["STL"],
    "kansas-city-missouri": ["KC"],
    "tampa-florida": ["Tampa Bay", "St. Petersburg"],
    "new-orleans-louisiana": ["NOLA", "the Big Easy"],
    "honolulu-hawaii": ["Oahu"],
    "austin-texas": ["ATX"],
    "cincinnati-ohio": ["Cincy"],
    "detroit-michigan": ["Motor City"],
    "indianapolis-indiana": ["Indy"],
    "sacramento-california": ["Sactown"],
    "salt-lake-city-utah": ["SLC"],
    "oklahoma-city-oklahoma": ["OKC"],
    "jacksonville-florida": ["Jax"],
    "albuquerque-new-mexico": ["ABQ"],
}


def tokens_from_title(title: str) -> tuple[list[str], list[str]]:
    """(city tokens, state tokens). Kept apart since Phase 2e item 5: a
    state token scoring like a city name is how 'new york' filled the
    compare picker with upstate metros — the shared scorer caps state
    tokens, so the split must survive into the index."""
    name, _, states = title.rpartition(", ")
    city = [re.sub(r"^Urban ", "", t.strip())
            for t in re.split(r"[-–—]", name) if t.strip()]
    st = [s.strip() for s in states.split("-") if s.strip()]
    return city, st


def main() -> None:
    build_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BUILD
    metros = json.loads((build_dir / "metros.json").read_text())
    # a colloquial keyed to a slug that no longer exists is silently dead
    # — DC's "DC"/"the DMV" entries were, from Phase 2c until the item-5
    # search matrix caught it
    slugs = {m["slug"] for m in metros}
    dead = sorted(set(COLLOQUIAL) - slugs)
    assert not dead, f"colloquial keys with no matching slug: {dead}"
    rows = []
    for m in metros:
        city_toks, st_toks = tokens_from_title(m["title"])
        toks = city_toks + COLLOQUIAL.get(m["slug"], [])
        # the full state name joins the STATE tokens (capped in scoring),
        # from the display name's own tail
        state_full = m["display_name_full"].rsplit(", ", 1)[-1]
        st = st_toks + [state_full]
        seen, keep = set(), []
        for t in toks:
            k = t.lower()
            if k not in seen:
                seen.add(k)
                keep.append(t)
        rows.append({"s": m["slug"], "f": m["display_name_full"],
                     "r": m["ranked_set"], "k": keep,
                     "st": list(dict.fromkeys(st))})
    out = WEB / "src" / "data" / "search-index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=False)
    out.write_text(payload + "\n", encoding="utf-8")
    print(f"{out}: {len(rows)} cities, {len(payload)/1024:.1f} KB")


if __name__ == "__main__":
    main()
