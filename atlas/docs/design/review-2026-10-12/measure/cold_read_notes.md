# Cold read, 12 October 2026 (written before reading any project document)

Live site, https://datingscenedata.com, headless Chromium (Playwright 1.63) through
`driver.mjs`. Phone = 390×844, DPR 2, touch. Desk = 1440×900. Screens in `../screens/`.

## Phone, 390

1. **Arrival** (`home-390-cold-first.png`). The headline says what the site does at once:
   "Which city has the best dating scene for you?". The four-field quick search sits
   above the fold, already filled in (Woman, 30, Men, 28–40), and the #1 card's score
   and matches peek in at the bottom. Good first five seconds.
2. Nothing on the first screen says I can weigh cost, weather and so on. I only learn
   that when the "Refine your search" bar slides up on my first scroll.
3. **Cards** (`home-390-scroll1.png`). Big photo, rank medallion, "77 /100", "266,309
   matches", a bar with a tick labelled "median 43", and three chips: ▲ Walkability,
   ▲ Places to go out, ▼ Rent. *Confusion:* median of what, 43 what? I guess it's the
   middle city's score. *Confusion:* nothing tells me what the chips are; I guess
   "good and bad things here". The same three chips sit on SF, Boston and New York.
4. **"266,309 matches"**: an exact count to the person. It looks like a head count, not
   an estimate. Nothing near it says how sure the site is.
5. **Rows** (`home-390-scroll2.png`): the score is "74" with a short bar under it. There's
   no "/100" here, unlike the cards just above. One row's chips wrap to two lines, so row
   heights jump (San Jose, Seattle).
6. **Sheet** (`home-390-sheet-open.png`): clear. "Woman, 30 · Men 28–40 — Change" sums up
   the search. Its vocabulary is "Social life", but the chips say "Walkability" and
   "Places to go out"; it's "Cost of living", but the chips say "Rent" and "Everyday prices".
   I can map them only because the sheet's subtitles list them.
7. **Re-weight** (task 2): Cost of living A lot, Weather A lot, Social life Not much → Show
   results. The sheet closes, the page lands at the results header and a line says
   "Results updated for what matters to you. New top three: Austin, Boston, San
   Francisco" (`home-390-after-reweight.png`). *Impressed.* But I can't tell what moved
   below the top three: nothing marks Austin as up from 9th, and no row says ↑ or ↓.
   Every score dropped about 10 points (77 → 67 at the top), and nothing tells me why
   (I lowered "Social life", which SF was good at). The tick still says "median 43".
8. **Austin's detail** (`home-390-card-open-austin.png`): Compatibility 107 "where 100 is the
   US average" (clear); Balance 125 men per 100 women with dots (clear, attractive);
   "What moved the score (points), compared with the median city": Dating pool +12.2,
   Compatibility +8.0, Weather +2.1, Cost of living +2.0, Student +0.6, Social +0.5.
   *Confusion 1:* the chips above said "▼ Rent" in red, but nothing in the bars is
   negative: Cost of living is +2.0. *Confusion 2:* the chips never mention the two
   biggest reasons, the dating pool and compatibility. *Confusion 3:* I added the bars up:
   median 43 + 25.4 = 68.4, but the card says 67.
9. Balance ⓘ (`home-390-card-balance-info.png`): the box floats above and covers
   Compatibility; the wording is clear enough.
10. **City page** from "Open Austin →" (`city-390-austin-from-search.png`): "← Back to
    your results", title, a one-line description ("about 2.4 million people about three
    hours west": two "about"s), a big red "Compare with another city", then the card:
    "1 of 193 **cities**". The home page says "193 **metro areas**". There's no "What moved
    the score" here: the city's own page explains less than the home page's row did.
    The photo comes *after* the card. No photo credit anywhere on the page.
11. **Compare** (task 3): on the city page, "Compare with another city" turns into a "Type a
    city name" field; "Denv" + ↓ + Enter → `/compare/austin-texas/denver-colorado`. Fast
    (3 taps). On the phone, ▲ marks the better value; there's no "Comparison" column.
    *Surprise:* both cities show "125 men per 100 women" (to check: real, or a bug?).
12. **Abilene** (task 6): header 🔍 → "Abil" → Enter → Abilene's page. It says plainly why
    it isn't ranked. 3 steps.
13. **Back to your results** restores my search from the address bar. 
14. **Share** (task 7): no share button anywhere. The only way is to copy the address bar.
15. **Menu** (`home-390-menu-open.png`): Rankings / Compare / How it works. The footer has What
    we measure / Privacy / Terms / Data sources, and nothing else: no contact, no
    "who we are".

## Desk, 1440

16. **Arrival** (`home-1440-cold-first.png`): the search reads as a sentence: "I'm a Woman
    aged 30, looking for Men aged 28–40". The rail sits left, and three cards right. Very clear.
    On the cards, the third chip wraps alone onto a second line next to the chevron.
17. The rows' column header says "**City · why it ranks here**". So the chips *are* the
    why. But SF's detail says the why is mostly the dating pool (+18.1) and
    compatibility (+13.1); walkability and places to go out together are +9.4. The
    sentence that says so ("Biggest pluses: the size of the pool, the compatibility
    figure · Biggest minus: Rent") exists only for screen readers (`.sr-only`).
18. **Card detail at the desk**: clicking SF's chevron opens the detail *below* the row of
    three cards at y = 883 of a 900px window. Nothing visible happens; I had to scroll
    to find it (`home-1440-card-open-sf.png`, `…-scrolled.png`).
19. **Same-sex** (task 5): Man → "Looking for" flips to Women by itself (good); set Men,
    33, 28–38 through the age box. The results header shows Nathan's note: "On a
    same-sex search, matches count every single man in these ages, not just those
    looking for men." The update line says only "Results updated for ages 28–38". The detail
    still shows Balance as "119 men per 100 women": what does balance mean to a man
    looking for men?
20. **Friend opens the link** (task 7 again): the address carries `self_age=33&sex=male&…`,
    but not my own sex. In a fresh browser it opens as "I'm a **Woman**, aged 33, looking
    for Men", with no same-sex note and the woman's compatibility figures
    (`home-1440-shared-samesex-link.png`).
21. **Privacy** (task 8): footer → Privacy. Plain, specific and convincing ("never
    leave your browser… we never learn which one that is"). But nothing on the
    home page tells me this before I type my age and sex.
22. **Who made it** (task 8): "How it works" says "our estimate", "we". Nobody is named
    anywhere. A contact address is only on Terms.
23. **Compatibility of 72** (task 4): on the card, "where 100 is the US average". The full
    meaning is in "How the score works" at the foot of the home page, and in How it works.
    Whether to trust the matches figure: no on-page answer. "How it works → Which cities are
    included?" talks about noisy estimates, but no figure carries a range or a flag.

## Tasks

| # | Task | Phone (390) | Desk (1440) | Where the answer was | Wrong turns |
|---|---|---|---|---|---|
| 1 | Woman 30 → men 28–40: best three, why | 0 steps (it's the default search); ~5 s to read | same | Cards; "why" from chips | The chips' "why" leaves out the two biggest reasons (pool, compatibility) |
| 2 | Re-weight cost + weather up, social down | 5 taps (open sheet, 3 choices, Show results), ~10 s | 3 clicks, list updates in place | The update line names the new top three | Can't see what moved below the top 3; can't tell why all scores fell ~10 |
| 3 | Austin or Denver | Card → Open Austin → Compare with another city → type → Enter: 5 steps, ~15 s | same path, or Compare in the header | Compare page | None; but both balance figures read 125 (check) |
| 4 | What does compatibility 72 mean; trust matches? | Open a row; "where 100 is the US average"; then scroll to "How the score works" | same | Partly on the card, fully on How it works | No on-page signal of how sure a match count is |
| 5 | Man 33 → men 28–38 | 4 controls (sex, age, looking for, age box) | same | Results header note | The update line names only the last change; balance shown as men per 100 women |
| 6 | Where does Abilene stand | 🔍, type, Enter: 3 steps, ~5 s | same | City page note | None |
| 7 | Send results to a friend | No share control; copy the address bar | same | — | The friend's page shows a different person ("Woman") and different compatibility figures |
| 8 | Is what I tell it kept; who made the numbers | Footer → Privacy (2 steps); How it works | same | Privacy page; About | Privacy answered well. "Who" isn't answered: no person or organisation named |

## Checked afterwards (not part of the cold read)

- Note 7: not every score fell. San Francisco fell 77 → 66 (rent −13.2 with cost at "A lot"),
  Austin held 67 and rose to #1; the top score fell because the leader changed
  (`numbers_check.json`).
- Note 8, confusion 3: confirmed, and general: the bars are measured from a reference near 41,
  not from the "median 43" tick (REVIEW R06).
- Note 11: both balances really are 125 men per 100 women in the default search (Austin 125.5,
  Denver 124.6, both shown as 125); not a bug.
- Note 19: balance on a same-sex search is decided (ADR 0004, amended 29 Sep and 10 Oct).
- Note 20: the recipient seeing their own figures is decided (ADR 0018 §4); REVIEW R10 keeps
  only the guessed default and the missing share control.
- The slider is announced as "45 percent toward compatibility", not "0.45"
  (`local/m7_aria.txt`).
