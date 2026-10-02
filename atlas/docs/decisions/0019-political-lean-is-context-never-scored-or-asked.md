# ADR 0019 — Political lean is context, never scored or asked

Date: 2026-09-30 (Phase 4d)
Status: accepted. The decision and the neutrality rules are **Nathan's**
(the Phase 4d brief). The acceptance of the state-totals gaps is **Nathan's
call** after the phase halted on them, on 30 September 2026. The copy
marked as a draft waits for his approval (PHASE4D.md §6). Amended
2026-10-02, after the phase: every metro's city page shows its stat cards,
so the card shows on all 387 (the last section).

## Context

For many daters, politics is a dealbreaker. Nathan wants each metro's
political lean on the site. What a place's voters chose is a fact about
the place. It is not a fact about any visitor, and not about the people
who match a search. So the site describes it and never uses it.

## Decision

Show how each metro area voted in the 2024 presidential election, as
**context only**:

- **never scored**;
- **never a filter**;
- **never a weight or importance control**;
- **never feeding the compatibility figure**;
- **never asked of the visitor**. The site does not ask anyone their own
  politics.

The feature has the same status as crime and "Who lives here":
`status: context_only`, `weight_in_pillar: 0.0`, pillar `context`,
`computed: static`. The registry loader refuses anything else. The build's
loader refuses a political lean that is scored. No request field names
it, and /v1/rank neither carries it nor accepts it.

## The measure

- **Source** (ADR 0012, amended): MIT Election Data and Science Lab,
  *County Presidential Election Returns 2000–2024*, Harvard Dataverse,
  doi:10.7910/DVN/VOQCHQ, version 20, CC0 1.0.
- **The shares.** The Democratic share, the Republican share and everyone
  else's, each out of every vote cast for a presidential candidate.
  Write-ins count. Blank, spoiled, over- and undervotes do not.
- **Adding up to metros.** A metro's figure comes from the build's own
  county-to-metro crosswalk (the OMB Bulletin 23-01 delineation): votes
  are summed across its counties and divided once. County percentages are
  never averaged.
- **The rules**, committed before the measurement ran
  (`build/political_lean.py`):
  - a reporting unit's TOTAL rows where it has them, and the sum of its
    voting modes otherwise, never both;
  - the file's rows that count no vote for anyone never count, whatever
    their party;
  - a county missing from the returns makes its metro **"Not
    available"**, never an undercount.
- **Where the returns aren't counties:**
  - **Connecticut** reports by its eight former counties, which its
    planning regions don't nest in. Its five metros are Not available.
  - **Alaska** reports by state house district. A metro is built only
    from whole districts that lie inside it. Districts cross both
    Anchorage's edge and Fairbanks's, so both are Not available.
  - **Kansas City, Missouri** reports apart from its four counties, all of
    which lie in its metro, so its votes join that metro.
  - **Kalawao County, Hawaii** is counted with Maui County, in the same
    metro.
- **Coverage.** 380 of 387 metros and 187 of the 193 ranked have a figure.
- **2020** is computed the same way, for validation and the record only.
  The site shows 2024.

## The state totals, accepted (Nathan's call after the halt)

The brief held each state's summed county totals to the lab's own state
totals (its *U.S. President 1976–2024* file, read as a check only) within
0.1%. Six states fell outside in 2024:

- **Maine and Rhode Island** are short of ballots the states count only
  statewide, which no metro can be given. Maine's Democratic count is
  1.22% short and Rhode Island's 0.49%.
- **Arizona, Delaware, Nebraska and Virginia** match on the two parties
  (Virginia to 0.07%). Their count for everyone else differs by 0.24–0.53%
  (Arizona's is 0.34% higher).

Nathan accepted the gaps and chose to record them: the figures stand as
the county returns give them. Suppose the gap votes were spread like the
counted ones. Then 16 of the 28 metros in those states would show one of
their three whole numbers a point differently, and never more than a
point. The record is `results/phase4d/validation.json`, with the phase
halt in PHASE4D.md.

## Neutrality rules

- **Neutral wording.** Only the parties' names and the numbers. No
  evaluative word ("liberal haven", "red", "blue", "friendly", and the
  like) appears beside the figure. The registry loader refuses such words
  in the feature's name, unit, definition and strings, and the e2e sweep
  reads the card, the compare row and the stat page.
- **Colours.** The conventional blue for Democratic and red for
  Republican, muted to sit with the palette (`--dem` #33609E, `--rep`
  #A63A3A), with a neutral grey for everyone else (`--lean-other`). They
  are kept apart from the site's good and poor tones, its sex colours and
  its accent.
  - Every segment also carries its party's name in text, so colour is
    never the only cue.
  - The bar is announced with all three shares.
  - Contrast meets WCAG AA: each party colour is at least 4.5:1 on the
    white card and the paper page, and the grey at least 3:1, a graphic's
    bar (the vitest contrast test reads the tokens).
- **Order.** Democratic, everyone else, Republican on the bar. Democratic
  before Republican in every sentence, column and sort control. No list
  defaults to either party's top:
  - the stat page lists the cities by name;
  - the visitor may sort by either party's share;
  - the stat page carries no position numbers and no distribution strip,
    since either would line the cities up by one party.
- **No band words and no judgement.** The numbers only, as Nathan removed
  band words from the compatibility figure. The compare table gives this
  row no difference: a difference would set one party's share against the
  other city's. This departs from ADR 0007's rule that every compare row
  gets one.
- **Refresh.** After each presidential election; the next refresh is 2028.

## Where it appears

- **The city page:** a card beside "Who lives here", with the two main
  shares as text ("56% Democratic · 42% Republican"), the caption "2024
  presidential vote, whole metro area", the split bar and its key. It
  shows with the metro's other stat cards, which the page shows for the
  ranked set. *[Amended after Phase 4d: the page shows them for every
  metro now, so the card shows on all 387 — the last section.]*
- **Compare:** one row with both cities' shares.
- **What we measure:** an entry in the context group, with the definition.
- **A stat page** (`/stats/political_lean`), as above.
- **Not** on the home rows, and **not** in the side panel.

The figures reach the city and compare pages through their own read-only
endpoint, `GET /v1/political_lean`, which takes no input. The engine
composes every figure and word there (`model/context.py`), and the stat
page's build JSON runs through the same code. The rank response is left
byte for byte as it was: a search never carries or changes political
lean.

## Consequences

- `features.parquet` gains three vote columns, so the build has a new id,
  **2dbd9ebfa7ff**. Its cubes, kernel and metros are byte-identical to
  5b780e4f2444's.
- No golden moves: the vectors are identical and only `goldens.json`'s
  `fixture_of` line names the new build. So MODEL_VERSION stays
  **m4.1.0**, since `versions.py` asks for a bump only when a golden moves.
- Every rank response and every single-seeker ranking over the 518 ADR
  0011 test searches is identical to 5b780e4f2444's, the build id apart,
  and the stability gate reads 1.0 against the reference
  (`results/phase4d/served_numbers_check.json`, the build's validation
  report).
- The Connecticut and Alaska metros stay Not available unless a source
  that reports them exactly is added, which would need its own licence
  entry and an amendment here.

## Amended after Phase 4d (2026-10-02): every city page shows its profile

The card was to show "with the metro's other stat cards", and the city
page showed those for the 193 ranked-set metros only. It read a metro's
stat cards and crime from the /v1/rank response, which covers the ranked
set and nothing else, so the 194 metros below its population floor showed
no stat cards under the sentence "its profile is below". Compare said "Not
enough reliable data available." for each of their seven figures, which
was not so: every one of them has all seven. The gap dates from the site's
first metro pages (Phase 2b); PHASE4D.md flagged it.

Nathan approved the fix on 2 October 2026 and left its decisions to
judgment ("proceed with decisions that fit your best judgment"). What
shipped:

- **Every metro has its profile.** `POST /v1/profile` serves one metro's
  stat cards and crime block for any of the 387 (`scoring.metro_profile`):
  the very blocks a ranked or suppressed row carries, which no request
  changes, banded among all 387 metros as before. The city page and
  compare read it for every city; /v1/rank is untouched.
- **The metro travels in the body**, as a search does, and the body may
  name nothing else (any other field is refused). The API's access lines
  read `POST /v1/profile`, so no log says which city a page showed.
- **Political lean follows its rule.** It still shows with the metro's
  other stat cards, which every city page now has: 193 of the 194 metros
  below the floor show a figure, and Fairbanks shows "Not available". The
  compare row already showed every metro.
- **No new words.** The floor sentence stays as it is, now true. Each card
  keeps its stat-page link, though the stat pages list the ranked cities
  and so leave these cities off.

Nothing ranked moved. On build 2dbd9ebfa7ff, all 518 ADR 0011 test
searches return /v1/rank responses of the same bytes before and after the
change, and all 1,036 single-seeker rankings are identical; /v1/meta is
unchanged; for the 193 ranked-set metros the profile equals the search
row's blocks (`results/city_profile/served_numbers_check.json`). The
build, its manifest and MODEL_VERSION are unchanged.
