# Phase 4d deviations

One line each; PHASE4D.md's list is kept identical.

- The county file has no state rows, so the check's state totals come from the lab's companion state-level file (doi:10.7910/DVN/42MVDX, CC0 1.0), read as a check only; Nathan approved the download.
- The dataset is behind a guestbook, so Nathan downloaded it by hand and the adapter pins that copy (the pinned sha256 and Dataverse's MD5) instead of fetching it; its manifest entry says it was obtained by hand.
- The state totals are compared like with like (the Democratic count, the Republican count and the votes for a candidate, each file's non-vote rows dropped), a definition written after a first look at both files; on the state file's reported totals, which in some states count blank and spoiled ballots, 13 states would fall outside instead of 6.
- The citation is the dataset page's string with a full stop added, the house rule for citations.
- Alaska is decided from the Census Bureau's 2024 district-to-tract relationship file and 2020 Census tract populations (Nathan approved the download); the district-to-county file fetched beside it is on the manifest but unused.
- The 2020 Alaska metros are Not available without a check, since the 2020 returns use the districts drawn after 2010.
- Kalawao County is counted with Maui, and Kansas City's own returns join the Kansas City metro; both are asserted to lie in one metro.
- The state-gap reading (the gap spread like the counted votes, and all of it in one metro) was added after the first run, to size the finding; it decides nothing.
