# Cold read notes (as they happened)

## 390 phone, fresh context
- First screen: H1 + subhead + quick search (sex/age/looking for/their age). #1 card photo starts at fold (y≈657 css). Score/name of #1 below the fold. Clear what the site does in 5s.
- No way to weight anything on first screen; "Adjust your search" bar only appears after scrolling (not at scrollY 0).
- Card: "266,309 matches"; rows: "783,728 single men match". Two wordings for one figure.
- Chips on #1-#10 nearly all "▲ Dating pool ▲ Compatibility ▼ Rent". Wraps to 2 lines on phone rows.
- Footnote "Balance compares all single men with all single women..." at bottom of list — balance appears nowhere on cards or collapsed rows; orphan.
- "Lifestyle: four things you weight — ..." starts lowercase.
- Sheet: clean, What matters to you visible; Narrow it down collapsed below. Sex/ages not in sheet.
- After Cost=A lot, Weather=A lot, Social=Not much → "Show results": sheet closes, page stays at scrollY 2500 (rows 9-10). Top of list not in view; nothing says what moved. Live region says "Results updated for what matters to you".
- New order: Austin, Boston, SF, Houston, LA, NY, Pittsburgh, San Jose, Seattle, New Orleans. Boston and SF still top 3 with "▼ Rent" after I said cost matters a lot.
- Row expand: three tiles. Balance tile "105 men per 100 women", track labels "More women / More men" no "Even" (city page has "Even").
- Compatibility 97 "where 100 is the US average" yet What moved shows Compatibility +0.9 (positive) — below-average compat adds points (because points are vs middle of ranked cities).
- Info box for Balance covers the balance figure it explains; info box for What moved covers the top three bars.
- ⓘ buttons accessible names = "Balance", "What moved the score (points)" (same as heading; not "About balance").
- Chip "Students" vs control "Student life" vs sr-only "The student crowd".
- City page (Houston): good. "4 of 193 cities for men 28–40, never married or divorced or widowed" — clunky. Big blank space under footer.
- "Who lives here 7.4 million" — gap between number and caption.
- Header search: native blue × clear button next to the close ×.
- Abilene: "sits below the population floor this site ranks, so it never appears in results — its profile is below." Floor not stated. "A city of about 200,000 people about three hours northwest of Killeen." "200,000 people, of whom 100,000 are adults" — looks like 1-sig-fig rounding making adults ≈ 50%.

## 1440 desk, fresh context
- Strong first view: H1, sentence-style quick search, rail + top 3 cards above the fold.
- Cards have no expand: top 3 — the cities that matter most — show the least (no balance, compatibility, what moved) on the home page.
- Re-weight cost=A lot: Boston #1, SF #2 (the two priciest), Austin #3; median 43→44. No indication of what moved.
- Compare: nav → /compare → type two names → "Compare these two". Answer: Austin 67 vs Denver 65, #9 vs #11.
- Compare banner "These figures use the stated default search — men 28–40 ... Change anything on the home page and they become yours." shown even though the default is exactly the visitor's search. Reads as a warning.
- Edge column: always A−B sign under the winner: "▲ Denver −31,802", "▲ Denver −4", "▲ Austin −2" (rank). Misreadable.
- Austin and Denver both 125 men per 100 women (check).
- No uncertainty anywhere on home / city / compare: matches to the unit (266,309), API serves pool_moe (5,221), cv, n_unweighted, tier — none shown.
- /api/rank response 1.48 MB uncompressed; next start does not compress the route handler. Home HTML 1.96 MB (297 KB gzip).
