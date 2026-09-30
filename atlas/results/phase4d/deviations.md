# Phase 4d deviations

One line each; PHASE4D.md's list is kept identical.

- The county file has no state rows, so the check's state totals come from the lab's companion state-level file (doi:10.7910/DVN/42MVDX, CC0 1.0), read as a check only; Nathan approved the download.
- The dataset is behind a guestbook, so Nathan downloaded it by hand and the adapter pins that copy (the pinned sha256 and Dataverse's MD5) instead of fetching it; its manifest entry says it was obtained by hand.
- The state totals are compared like with like (the Democratic count, the Republican count and the votes for a candidate, each file's non-vote rows dropped), a definition written after a first look at both files; on the state file's reported totals, which in some states count blank and spoiled ballots, 13 states would fall outside instead of 6.
- The state-totals stop condition fired (six states); the phase halted, and Nathan accepted the gaps and chose to record them in ADR 0019, after which the brief ran on as written.
- The citation is the dataset page's string with a full stop added, the house rule for citations.
- Alaska is decided from the Census Bureau's 2024 district-to-tract relationship file and 2020 Census tract populations (Nathan approved the download); the district-to-county file fetched beside it is on the manifest but unused.
- The 2020 Alaska metros are Not available without a check, since the 2020 returns use the districts drawn after 2010.
- Kalawao County is counted with Maui, and Kansas City's own returns join the Kansas City metro; both are asserted to lie in one metro.
- The state-gap reading (the gap spread like the counted votes, and all of it in one metro) was added after the first run, to size the finding; it decides nothing.
- The figure reaches the city and compare pages through its own endpoint (GET /v1/political_lean), not the rank response: the home page never shows it, and every search's response stays byte for byte as it was, the build id apart.
- MODEL_VERSION stays m4.1.0 though the build id changes (2dbd9ebfa7ff): no golden moves (goldens.json differs only in fixture_of), and versions.py asks for a bump only when one does; versions.py records the build.
- The compare row has no difference, against ADR 0007's every-row rule: a difference would set one party's share against the other city's; its cell is empty and carries no data-diff-for.
- The stat page has no distribution strip and no position numbers, and lists by name: either would line the cities up by one party.
- The stat page keeps the source line every stat page carries (the registry loader requires it), naming the lab; the citation itself is only in Sources and credits.
- The city card shows with the metro's other stat cards, which the city page shows for the 193 ranked-set metros only; the other 194 pages show no stat cards at all, an existing gap flagged for a separate task.
- The shares' text has a no-break space before its middle dot, so a narrow card breaks the line after the dot.
- Registry strings beyond the brief's words: the three segment names, the text and spoken-label templates, the sort control and the stat page's source name (drafts, §6), since no user-facing string lives in code.
- "Not available" is tested in the engine, the API and a vitest render, not in Playwright: no metro of the pinned 12-metro fixture lacks a figure, and adding one would change the golden fixture.
- The first full Playwright run failed one test: its sweep read the stat page's whole text and matched "left" in the note every stat page shares ("left off this list", approved copy); the sweep now reads political lean's own words.
- The web pages skip the figure when the API answers 404 (an API from before the feature), so a dev stack still serving 5b780e4f2444 keeps working.
- vitest compiles JSX with React's automatic runtime (vitest.config.ts) so the unit tests can render the card; tsconfig keeps JSX as it is for Next.
