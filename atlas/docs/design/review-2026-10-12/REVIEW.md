# Design review, round 4: the site after Phase 6 and the October changes

Reviewed 12 October 2026, on Nathan's Mac. **Primary target:** the live site,
https://datingscenedata.com (m4.3.0 on build d62202fd0280). **For anything repeated or
broken:** a local production build of `main` at `e34aa55` (code as `76de4ef`), `next start`
on port 3400 over the API on the real build at 8100. Headless Chromium through Playwright
1.63, axe-core 4.13. **WebKit (Safari's engine) isn't installed on this Mac**, so there was
no Safari pass; nothing was downloaded. VoiceOver wasn't driven; the screen-reader pass is the
accessibility tree (`measure/local/m7_aria.txt`).

Everything cited is in this folder: screenshots in `screens/`, scripts and raw outputs in
`measure/` (its README says how to re-run them). All copy is a DRAFT for Nathan's approval.
Nothing in the product was changed, committed, pushed or deployed.

---

## 1. In plain words

The site is in much better shape than at round 3. Of round 3's 37 findings, 31 are fixed
on the live site, and the big ones (slow photos, uncompressed results, signs that
contradicted their arrows) are gone. A phone now sees the first big picture in about
**3.5 seconds instead of 11.5**, and a change of weights lands in **1.8 seconds instead of 7.9**.
axe finds nothing on any page. What's left is mostly about pieces that were each fine on
their own and no longer fit together after three days of small changes.

1. **Below desk width, a keyboard can't reach the search settings.** On a phone or tablet
   with a keyboard, or on a desktop zoomed to 200%, pressing Tab walks past "Refine your
   search" without ever stopping on it. The button only exists on screen once you've
   scrolled, and its turn in the Tab order comes while you're still at the top. It's like
   a shop door that only opens if you walk in backwards. The fix is small.
2. **The "why" the site shows doesn't match its own numbers.** The little tags under each
   city ("▲ Walkability ▲ Places to go out ▼ Rent") only ever name lifestyle details. The
   real reasons, the size of the dating pool and the compatibility figure, never appear
   until you open a city, though the list's heading says "why it ranks here". In the default
   search, on 36 of the 193 cities a tag points the opposite way to its own bar. After a
   re-weight that puts Austin first, its "▼ Rent" sits in red above "Cost of living +2.0" in
   green. And "Compared with the median city" doesn't add up
   to the "median 43" mark on the same card. It's like a receipt whose lines don't add up to
   the total printed under them. Nobody may check, but anyone who does stops trusting it.
3. **People arriving from outside meet loose ends.** Every browser tab shows Vercel's black
   triangle, the framework's starter icon, never replaced in the rename. Search engines find
   no `robots.txt`, no sitemap and no canonical addresses. And a city page reached from a
   search engine says "Where Austin lands for **your** search" and offers "Back to **your**
   results" to someone who never searched. Compare already says "This comparison uses the
   site's starting search"; the city page doesn't.
4. **On a 1440×900 laptop, clicking one of the three top cards seems to do nothing.** Its
   details open just below the bottom edge of the screen (17 pixels show). The same happens
   on a tablet held upright.

---

## 2. What works (keep it)

- **The first five seconds.** "Which city has the best dating scene for you?" and the
  sentence-shaped search ("I'm a Woman aged 30, looking for Men aged 28–40") say what the
  site does at once, at every width (`screens/home-1440-cold-first.png`,
  `home-390-cold-first.png`). On a phone, #1's score sits at 819px of 844.
- **Feedback after a change.** "Results updated for what matters to you. New top three:
  Austin, Boston, San Francisco", landing on the results heading after "Show results"
  (`screens/home-390-after-reweight.png`). Choosing a race is announced the same way.
- **The row and card detail.** Compatibility against 100, balance as dots, and "What moved
  the score" as signed bars: the clearest part of the site (`screens/home-390-card-open-austin.png`).
- **Compare.** "▲ Austin by 2 places", "▲ Denver by 31,802": the arrows and the sizes now
  read straight; the starting-search note is neutral and plain
  (`screens/compare-1440-cold-austin-denver.png`).
- **Honesty on narrow searches.** "5 metro areas ranked for your search. 188 metro areas don't
  have enough people matching this search for a reliable estimate"
  (`screens/home-390-narrowed.png`); the caution captions (Virginia Beach's dorms and
  barracks, `screens/city-1440-virginia-beach-top.png`); "Abilene has fewer than 250,000
  people, so it isn't ranked".
- **The Privacy page.** Specific and convincing: "never leave your browser… we never learn
  which one that is", the one cookie named, the host named.
- **The privacy architecture holds.** The site's `/api/rank` refuses a body with the
  visitor's own sex (422); the cookie holds the partner search and age only; the server
  logs nothing about a visit (deploy records).
- **Accessibility basics.** axe: **0 violations** on 23 pages at 1440 and 390 and 14 home
  states each (74 runs, all rules plus experimental). No target under 44×44 below 1120px
  outside running text, no text under 12px, no contrast failure where text is used,
  nothing sideways at 320px or 200%, no motion under reduced motion.
- **Speed and weight.** Photos at the size they're shown (home 317 KB of images on a phone,
  71 KB on the desk), `/api/rank` compressed (zstd, 251 KB on the wire), a week's caching on
  photos, city HTML at 36 KB.
- **The photographs.** About 180 of 193 read as their place, and the 11 replaced in Phase 6
  (Los Angeles, Reading, Davenport…) are clear improvements (`screens/photos/`).
- **The rename on the server.** Both old addresses and `www` answer 301 to the same page,
  path and query kept; `http` answers 308; certificates valid to January 2027; TLS 1.1
  refused (`measure/live_site.txt`).

---

## 3. Round 3, revisited

Status on the live site, 12 October 2026.

| ID | Round 3's finding | Status | Evidence |
|---|---|---|---|
| F01 | Same-sex matches overstated, no note | **Fixed.** Nathan's note shows under the results header, the city card's matches and Compare's Matches row. Its balance caption was added, then deleted by Nathan (10 Oct). | `screens/home-1440-samesex.png` |
| F02 | Targets under 44×44 below 1120 | **Fixed.** 0 outside running text at 390, 768, 1024, 1119 | `measure/local/m4_sizes.json` |
| F03 | Phones wait for full-size photos | **Fixed.** Home images 317 KB at 390 (was 1,810); phone LCP 3.45 s live (was 11.46) | `measure/live/m1_pages_1440_390.json`, `m2_speed_live.json` |
| F04 | `/api/rank` uncompressed | **Fixed.** zstd, 250,889 bytes on the wire (was 1,503,429) | `measure/live_site.txt` |
| F05 | No feedback after a change on phones | **Fixed.** Lands on the heading; "New top three" line; 1.78 s to settle on the slow phone, live (was 7.86) | `screens/home-390-after-reweight.png` |
| F06 | Top three cards had no detail | **Fixed**, but at 1440×900 and 768×1024 the detail opens off-screen (R03) | `screens/home-1440-card-open-sf.png` |
| F07 | Compare's Edge signs contradicted arrows | **Fixed.** "▲ Austin by 2 places"; the column is now "Comparison" | `screens/compare-1440-cold-austin-denver.png` |
| F08 | Served cautions never shown | **Fixed** | `screens/city-1440-virginia-beach-top.png` |
| F09 | "Who lives here" rounding | **Fixed** ("180,000 people, of whom 120,000 are adults"; Champaign "about 240,000"). The descriptions' wording waits on Nathan (known). | `measure/og_live.txt` |
| F10 | Race asked with no word on privacy | **(a) Fixed** (Privacy sentence). **(b) Reversed by Nathan** on 10 Oct: no ⓘ beside Sharpen compatibility. | `/privacy` |
| F11 | How it works said race is always used | **Reversed by Nathan** on 10 Oct: his wording, kept after the caveat was raised | `copy_2026_10_10` #14 |
| F12 | Chips repeated | **Fixed as decided** (lifestyle chips), but see R05 | `numbers_check.json` |
| F13 | About-you changes not announced | **Fixed.** "Results updated for your race or ethnicity. New top three: New York, New Orleans, Philadelphia" | hand test, local |
| F14 | Matches shown as exact counts | **Open, set aside by Nathan** (ADR 0004 §3) | — |
| F15 | #1's score below the phone's first screen | **Fixed** (819px of 844), but the 12 Oct bar now covers it on the first scroll (R08) | `screens/home-390-bar-first-scroll.png` |
| F16 | City page led by the photo | **Fixed.** The card starts at 402px at 1440 | `screens/city-1440-virginia-beach-top.png` |
| F17 | Info boxes covered what they explain; opened on focus | **Fixed.** Open on click; float above (Nathan's decision) | `screens/home-390-card-balance-info.png` |
| F18 | Back lost your place | **Fixed.** Row 50 of 193 restored | hand test, local |
| F19 | Sheet couldn't change sex and ages | **Fixed.** "Woman, 30 · Men 28–40 — Change" | `screens/home-390-sheet-open.png` |
| F20 | Silent flip of "Looking for" | **Fixed** (flips only while untouched, and says so) | hand test |
| F21 | One figure, five names | **Partly.** Cards and phone rows say "matches"; desk rows and the city card say "single men" under a "Matches" label; the city card says "of 193 cities" where the home page says "metro areas" (R15) | `screens/home-1440-scroll1.png` |
| F22 | The bars' yardstick hidden | **Fixed** (always shown), but its words don't match the tick (R06) | `screens/home-390-card-open-austin.png` |
| F23 | Compare's default note in warning amber | **Fixed** on Compare; the city page has no such note (R04) | `screens/compare-1440-cold-austin-denver.png` |
| F24 | Floor unstated, strings hard-coded | **Fixed** | `screens/compare-1440-austin-abilene.png` |
| F25 | No "Even" in the tile | **Fixed** | `screens/home-390-card-open-austin.png` |
| F26 | Screen-reader labels | **Fixed** ("Overall score 74 out of 100", "About balance"); one heading still reads "Balance About balance" (R16) | `measure/local/m7_aria.txt` |
| F27 | Focus hidden under the bar | **Fixed** (no stop hidden), but the fix put the bar where Tab never reaches it (R01) | `measure/keyboard_bar.txt` |
| F28 | Menu ignored Escape | **Fixed** | `measure/local/m5_keyboard.json` |
| F29 | Places elsewhere in the metro uncaptioned | **Fixed** ("Daytona Beach, in the Deltona metro area") | live check |
| F30 | Crops and weak photos | **Mostly fixed.** Fargo's band still reads "FARG" (known); Palm Bay and Rockford kept by decision | `screens/photos/` |
| F31 | Bare link previews | **Fixed** (results titles, own `og:url`, large previews, home image); no canonical addresses yet (R07) | `measure/og_live.txt` |
| F32 | City HTML 281 KB | **Fixed.** 36 KB | `measure/live/m1_pages_1440_390.json` |
| F33 | Stat sort control | **Fixed** | `screens/stat-390-rent-top.png` |
| F34 | Copy polish | **Fixed** | — |
| F35 | Browser's blue "×" | **Fixed** (the site's own Clear) | — |
| F36 | 404 footer floating | **Fixed** | `screens/404-390-top.png` |
| F37 | Age token name mismatch | **Fixed** (axe experimental clean) | `measure/local/m3_axe.json` |

---

## 4. The cold read

Full notes, written before reading any project document: `measure/cold_read_notes.md`.

### First visit, 390

- *Clear in five seconds.* The headline, then the 2×2 quick search already filled in, then
  #1's photo, score and matches at the bottom of the first screen.
- *Hidden:* nothing on the first screen says you can weigh cost or weather. The "Refine
  your search" bar arrives on the first scroll, as it was designed to. But in that moment
  it slices through #1's "77/100" and "266,309 matches" (`screens/home-390-bar-first-scroll.png`).
- *Puzzling:* "median 43" under the score track: median of what?
- *Puzzling:* the chips have no label at all on a phone. The same "▲ Walkability ▲ Places to
  go out ▼ Rent" sits on San Francisco, Boston and New York.
- *Inconsistent:* the cards say "77 /100", the rows below say "74" with nothing after it.
- *Impressive:* re-weighting in the sheet, then "Show results", lands on "Results updated…
  New top three: Austin, Boston, San Francisco".
- *Confusing:* Austin's open card says "▼ Rent" in red, then the bars say "Cost of living ·
  everyday prices, rent +2.0" in green. And median 43 plus the bars (+25.4) is 68.4, but the
  card says 67 (`screens/home-390-card-open-austin.png`).
- *City page:* "1 of 193 cities", where the home page said "193 metro areas". No "What
  moved the score" here: the city's own page explains less than its row did.
- *Surprise:* Compare showed Austin and Denver both at "125 men per 100 women". I checked:
  it's real, not a bug (`measure/numbers_check.json`).

### First visit, 1440

- *Strong first view:* the sentence search, the rail and the three cards in one screen.
- *Wrong turn:* I clicked San Francisco's card. Nothing seemed to happen; the detail had
  opened at y = 883 of a 900px window (`screens/home-1440-card-open-sf.png`).
- *Reading:* the rows' header says "City · why it ranks here", but the sentence that names
  the real biggest pluses ("the size of the pool, the compatibility figure") is for screen
  readers only.
- *Same-sex:* choosing Man flipped "Looking for" to Women, which is fine; the note in Nathan's
  words then sits under the count line (`screens/home-1440-samesex.png`).
- *Sharing:* there's no share control. The address carries the search but not the visitor's
  own sex (by design, ADR 0018 §4), so a friend opening a man's same-sex link sees "I'm a
  Woman" and no same-sex note (`screens/home-1440-shared-samesex-link.png`).
- *Trust:* the Privacy page is excellent; nothing points to it at the moment of typing your
  age and sex. Nobody is named anywhere as the maker. The browser tab shows a black triangle.

### The tasks

Steps count taps, clicks and keys, typing excluded. Times are what the browser took.

| Task | 390 (touch) | 1440 | Wrong turns | Where the answer was |
|---|---|---|---|---|
| 1. Woman 30, men 28–40: best three and why | 0 steps (the default search); answer on screen at once | 0 steps | The visible "why" (lifestyle chips) leaves out the two biggest reasons; the open detail at 1440 lands off-screen | Cards; full "why" one tap deeper, in "What moved the score" |
| 2. Cost and weather a lot, social less | First scroll shows the bar; 1 tap, 3 choices, "Show results": 5 taps. Lands on "Results updated… New top three: Austin, Boston, San Francisco"; settles in 1.8 s on the slow profile | 3 clicks in the rail; settles in 0.63 s | None. Below the top three you can't tell what moved, and Austin's "▼ Rent" contradicts its bar | The update line. It makes sense: San Francisco falls 77 → 66 on rent (−13.2), Austin holds 67 |
| 3. Austin or Denver? | Card → Open Austin → "Compare with another city" → type "Denv" → Enter: 4 steps | Same, or Compare in the header | None | Compare page: Austin 67 vs Denver 65 (default search) |
| 4. What does a compatibility of 72 mean? Trust the matches? | Open a row: "where 100 is the US average"; full meaning under "How the score works" at the page's foot | Same | — | Meaning on the page. Trust in matches: suppression and the cautions only (by decision, ADR 0004 §3) |
| 5. Man 33, men 28–38 | 4 controls (I'm a, age, Looking for back to Men, age box) | Same | The flip to Women is announced and expected | Note under the count line; balance still shown as men per 100 women |
| 6. Where does Abilene stand? | 🔍, "Abil", Enter: 3 steps | 2 steps | None | "Abilene has fewer than 250,000 people, so it isn't ranked" |
| 7. Send results to a friend | No share control: copy the address bar | Same | The friend's page assumes "Woman" and drops the same-sex note | — |
| 8. Is what I tell it kept? Who made the numbers? | Footer → Privacy: 2 steps; How it works | Same | No one is named as the maker | Privacy: clear. "Who": "our estimate", "we", unnamed |

---

## 5. Findings

Most severe first. Sizes: S ≈ an hour or two, M ≈ a day, L = more. IDs are round 4's (R…);
round 3's are F….

| ID | Sev | Page · width | What I saw (evidence) | Who it hurts, how | Recommendation | Size | Tags |
|---|---|---|---|---|---|---|---|
| R01 | **Blocker** | Home · every width below 1120, and 1440 at 200% zoom | Tab never reaches "Refine your search". Two full Tab loops at 390 (80 presses) and one at 1024 (50): the bar is never focused. It sits in the DOM right after the age box (Phase 6 F27 moved it there), but it is `display:none` until the page scrolls, and the page is still at the top when Tab passes its slot. It is reachable only by Shift+Tab from inside the list (`measure/keyboard_bar.txt`; `screens/home-390-keyboard-bar.png`). Round 3's run reached it ("Adjust your search", after the list). | Keyboard and switch users on tablets and phones, and anyone on a desktop zoomed to 200%: the weights, "Narrow it down" and "Sharpen compatibility" are out of reach in normal order. WCAG 2.1.1 / 2.4.3 in practice. | Never hide the bar with `display:none`. Keep it rendered in its DOM slot, moved off-screen with `transform: translateY(100%)` while hidden, and shown when visible **or** when focus enters it (`:focus-within` → `translateY(0)`; under reduced motion, no transition). Then the next Tab after "Their age" lands on "Refine your search", which is where it belongs. Add an e2e check: from "Their age", Tab focuses the bar at 390 and 1024. | S | — |
| R02 | Major | Every page · all | The favicon is Next.js's starter icon, **Vercel's black triangle** (25,931 bytes, unchanged since the first scaffold commit, 16 Sep; `screens/favicon-256-live.png`). No `apple-touch-icon` or manifest, so an iPhone home-screen bookmark gets a screenshot. The starter files `/next.svg`, `/vercel.svg`, `/file.svg`, `/globe.svg`, `/window.svg` are still served (200) (`measure/live_site.txt`). | Everyone with the site in a tab or bookmark: the brand after the rename is another company's logo. | A mark of the site's own: for example a Fraunces "D" (SOFT 30, 600) in `--surface` on `--accent` #9E3B57, in `app/icon.svg` plus `app/apple-icon.png` (180×180) and a 32×32 `favicon.ico`. Delete the five starter SVGs from `public/`. | S | needs Nathan's decision (the mark) |
| R03 | Major | Home cards · 1440×900, 768×1024 (and any window under ~1,000px tall at those widths) | Clicking a top-three card (anywhere, Nathan's 10 Oct change) opens its detail under the row of cards, at y = 883 of 900 (17px visible) at 1440, and 954 of 1024 (70px) at 768. The page doesn't move (`screens/home-1440-card-open-sf.png`, `…-scrolled.png`, `home-768-card-open.png`). | Most laptop visitors: the most-clicked thing on the page appears to do nothing. | After opening, if the panel's bottom is below the window, `panel.scrollIntoView({block: "nearest"})`; `behavior: "smooth"`, but `"auto"` under reduced motion. Same for rows near the bottom edge. No layout change. | S | — |
| R04 | Major | City pages · all, arriving cold | A visitor from a search engine or a shared city link sees "← Back to your results", "Where Virginia Beach lands for your search", "47 of 193 cities", for a search they never made (the site's starting search: a woman of 30 looking for men 28–40) (`screens/city-1440-virginia-beach-top.png`). Compare shows `compare_default_note` in the same situation (`screens/compare-1440-cold-austin-denver.png`); the city page shows nothing. | Cold visitors, most of whom aren't women looking for men 28–40: a rank presented as theirs. | On the city card, when the figures are the starting search (`isDefaultSearch && !fromCookie`, Compare's own test), show the same neutral note, `--sunken` fill, `--ink-2`, with "Make it your search" (copy §9). Make the back link "← See the rankings" in that case. | S | copy |
| R05 | Major | Home rows, cards and detail; city card · all | The chips name lifestyle items only (ADR 0003, Phase 6), but the desk header calls them "City · why it ranks here", and the sentence naming the real biggest pluses is screen-reader only. On **36 of 193** rows in the default search (34 after task 2's re-weight; 3 to 4 in the top 20), a chip's sign is the opposite of its own pillar's bar: Austin #1 after task 2 reads "▼ Rent" above "Cost of living · everyday prices, rent +2.0"; Houston "▲ Walkability" above "Social life −0.3"; Detroit "▲ Rent" above "Cost of living −1.4" (`measure/numbers_check.json`; `screens/home-390-card-open-austin.png`). Each is right on its own terms: the chip is one item, the bar is the pillar. | Anyone reading the open detail for "why": the two marks for the same thing disagree in colour and sign. | In "What moved the score", show the cost and social-life items as their own bars when a chip names one of them. Austin after task 2: "Rent −2.7 · Everyday prices +4.6" under "Cost of living +2.0". The API serves each stat's `contribution` (`stats[]`; Austin's rent −2.65, goods prices +2.38, services prices +2.26, adding to the pillar's +1.99). Everyday prices is two of those merged into one item (ADR 0003, m4.1.1), and adding them in the browser would be a new figure, so the API should serve one contribution per chip item beside `lifestyle_movers`. And rename the desk header to what the chips are (copy §9: `col_city`). | M | copy, needs the model (per-item contributions), needs Nathan's decision |
| R06 | Minor | Card and row detail, city card · all | The bars are measured from a reference built from each stat's median (ADR 0003, decision 1). That scores about 41 for every search (40.9 to 41.7), not the "median 43" the tick shows. So median + bars misses the shown score for **all 193** cities, by 2 points or more for 116 (default search; SF: 43 + 36.6 = 79.6 vs 77). The caption "Compared with the median city" names something the tick also calls median (`measure/numbers_check.json`). | Careful readers who add up the bars: the arithmetic doesn't close, on a site whose promise is honesty. | Say what the bars are measured from. DRAFT `moved_caption`: "Compared with a city in the middle on every measure" (§9). Keep the tick as it is. | S | copy, reopens a decision (Nathan's caption) |
| R07 | Minor | Server · all | `/robots.txt` and `/sitemap.xml` answer 404 (the HTML 404 page). No page has a canonical link. City pages are also reachable with the search in the query string (`/city/austin-texas?self_age=30&sex=male…`), so each city has many addresses (`measure/live_site.txt`). | Visitors from search engines: thinner, duplicated indexing at launch. | `app/robots.ts` (allow all; `Sitemap: https://datingscenedata.com/sitemap.xml`); `app/sitemap.ts` with home, How it works, What we measure, crime, Privacy, Terms, the 8 stat pages and the 387 city pages (not compare pairs or `/r/`); `alternates.canonical` on every page, the path without its query. | S | — |
| R08 | Minor | Home · 390 | Since 12 Oct the bar shows after 8px of scroll. On that first scroll its 76px band cuts across #1's "77/100" and "266,309 matches" (at 40px of scroll the score sits at 761–781px, the band starts at 768) (`screens/home-390-bar-first-scroll.png`). Phase 6 F15 had put that score in the first screen. #1's score clears the band from 53px of scroll at 390×844. | Phone visitors on their first look at #1. | Show the bar once the page has scrolled 8px **and** #1's score has cleared the band's top edge (measured from the layout, not a constant: 53px at 390×844). It still appears on the first flick of a thumb, as Nathan asked, without hiding the city that answers the question. | S | reopens a decision (lightly: the threshold of 12 Oct) |
| R09 | Minor | Home rows, Compare · all | The count line no longer says "each scored out of 100" (12 Oct). Cards and the city card still show "/100"; the rows (#4–193) show a bare "74", and Compare's "Overall score" row shows "67" and "65" (`screens/home-1440-scroll1.png`, `compare-1440-cold-austin-denver.png`). | First-time readers of the list: a bare 74 could be a percentage or a rank. | Show the existing `score_out_of` ("/100") after row scores (`text-caption`, `--ink-3`, as on the cards) and after Compare's score values. No new copy. | S | — |
| R10 | Minor | Home · all | No way to share results except copying the address bar. A shared link opens as "I'm a Woman" when the recipient has nothing stored: a man's same-sex link loses its note and shows the woman's compatibility figures (by design for figures, ADR 0018 §4, but the default is a guess) (`screens/home-1440-shared-samesex-link.png`). | Task 7, and recipients of same-sex links. | (a) A "Copy link" button beside Best/Worst (Web Share sheet on phones), copying the page's own address (the query form ADR 0007 calls "the shareable form"; not the `/r/` permalink ADR 0004 §3 keeps out of the UI). (b) When a link arrives with nothing stored, a one-line prompt above the quick search: copy §9. | M | copy, needs Nathan's decision |
| R11 | Minor | Home, footer, How it works · all | Trust is all on secondary pages. The home page says "Based on Census data", unlinked. Nothing says who made the site; the only contact address is at the foot of Terms. | Visitors deciding whether to believe a ranking about where to live. | Without restoring the deleted lines: make "Based on Census data" in the hero a link to How it works (no new copy). Add "Contact: hello@datingscenedata.com" to the footer. Add one sentence on How it works naming who makes the site (§9). | S | copy, needs Nathan's decision |
| R12 | Minor | Server · all | The only security header is `Referrer-Policy`. No HSTS, no `Content-Security-Policy`, no `X-Content-Type-Options`, no framing rule (`measure/live_site.txt`). | Everyone, quietly. A CSP would also *enforce* the Privacy page's "no page loads anything from another company's servers". | In the Caddyfile: `Strict-Transport-Security "max-age=31536000"`; `X-Content-Type-Options nosniff`; `Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"`. Test on the private staging copy first. | S | needs Nathan's decision (deploy) |
| R13 | Minor | City pages, cards · all | Two ranked cities' photos have unusable alt text: Indianapolis "indianapolis", and Montgomery a raw library record ("Title: Aerial view of Montgomery, Alabama / Physical description: 1 photograph: digital, TIFF file, color. / Notes: …"). Among unranked cities, 6 are raw Commons text (Casper "File:Casperskyline.jpg but cropped in a 1:1 ratio.", Hot Springs a list of file names, Gettysburg, Kahului, Sebastian, St. Cloud), 5 are announced as nothing (Abilene's "image" and four file names are filtered to `alt=""`: Chambersburg, El Centro, Gadsden, Macon), and about 20 give only the place's name (Victoria "Skyline") (`src/data/city-images.json`; live pages). | Screen-reader users on those pages. | Write real alts (drafts for Indianapolis and Montgomery in §9; the rest after Nathan approves the form). | S | copy |
| R14 | Minor | Compare · all | Unjudged rows: Balance's tie shows a bare "0"; Who lives here shows "−600,000" with no city named (Austin minus Denver) (`screens/compare-1440-cold-austin-denver.png`). | Anyone reading the Comparison column: a lone 0 or a minus sign has no subject. | Tie: "Same". Who lives here: "Denver, by 600,000" in `--ink-2` without the ▲ (it isn't judged) (§9). | S | copy, reopens a decision (plain difference, 10 Oct) |
| R18 | Minor | Every page · all | Fonts are 138 KB on every first visit, 121 KB of it Fraunces, loaded as a variable font with the optical-size and SOFT axes and its whole weight range. The site uses SOFT at 30 only, and weights 600–700 (`globals.css`, `layout.tsx`). | First visits on phones: the biggest fixed cost after the scripts. | Load Fraunces pinned to what's used (weight 600–700, SOFT 30, `opsz` kept if the optical sizes matter to Nathan), or self-host a subset; measure the saving before deciding. | M | — |
| R20 | Minor | Photos · all | San Jose (#5 by default, and #2 in narrowed searches) is a hotel front at Santana Row with "Hotel Valencia" on its façade. Charleston's Rainbow Row has parked cars across the foreground. York (1024px) and Reno (900px) are narrower than the 1,056px band. Peoria's brightest mark is a bank's octagonal logo; Fargo's band still cuts the sign (known) (`screens/photos/sheet-01.jpg`, `-04`, `-06`, `-09`). | Visitors who know the place: a hotel's name as a top city's face. | Replacements chosen by Nathan (§8). | M | needs Nathan's decision |
| R22 | Minor | City page · all | The city's own card explains less than its home row: it shows the chips, but not "What moved the score" (`screens/city-390-austin-from-search.png`). | Visitors who open a city to learn why it ranks where it does. | Under the chips, the same bars as the detail (served `contributions`), behind a "What moved the score" disclosure so the card's order stays as Nathan set it. | M | needs Nathan's decision |
| R23 | Minor | Home · all | On the live site the home page's first byte takes **839 ms** at 1440 (median of 5), against 75 ms for a prerendered stat page and 481–559 ms for Compare and a city page. The server builds the whole ranking, every "about you" variant included, before it sends anything, so the headline (the desk's largest paint, 1,000 ms) waits on it (`measure/live/m2_speed_live.json`, `m2c_pages_live.json`). | Every visitor's first wait, on a small free VM. | Stream the page: send the header, hero and quick search at once, and the results inside a `Suspense` boundary as the ranking arrives (its skeleton the same height as the cards, so nothing shifts). Measure the TTFB and LCP before and after. | M | — |
| R15 | Polish | City card, Compare · all | "Ranked 1 of 193 **cities**" under a home page that says "193 **metro areas**"; Compare says "Spot in your results". These, "Where {city} lands for your search", "← Back to your results", "Reported crime", "City to compare with" and "Single means" are literals in the web code, not registry strings. | Consistency; the registry rule. | Move them into the registry; "of {n} ranked" on the city card (§9). | S | copy |
| R16 | Polish | Detail, city card · all | The ⓘ button sits inside the Balance heading, so the heading reads "Balance About balance" (`measure/local/m7_aria.txt`). | Screen-reader users navigating by heading. | Put the button after the heading element, not inside it; same look. | S | — |
| R17 | Polish | Several · all | Two site descriptions: the home page's (the subtitle) and `SITE_DESCRIPTION` ("…Estimated from the Census Bureau's own survey, city by city.") on About, Privacy, Terms, What we measure and the 404. The 404's title is "Dating Scene Data", not "Page not found · …". Compare pairs have no preview image (`measure/og_live.txt`). | Link previews and tabs. | One description (the subtitle); the 404 title from `not_found_title`; Compare pairs use city A's preview image. | S | copy |
| R19 | Polish | Server · all | Files no page uses are served: `/hero.jpg` (344 KB), the starter SVGs (R02), and every original photograph at `/cities/<slug>.jpg` (up to 3 MB; pages use `/cities/w/` copies). | No visitor; tidiness, and what a scraper takes. | Remove `hero.jpg` from `public/` (the repo note says it stays for the record; keep it outside `public/`); stop serving originals, or leave them knowingly. | S | needs Nathan's decision |
| R21 | Polish | Home · 390, 1440 | Phone rows vary between 125px and 155px as chips wrap. On the desk cards, the third chip drops alone to a second line beside the chevron (`screens/home-390-scroll2.png`, `home-1440-cold-first.png`). | A ragged list. | Phone rows: move the chevron into the score column, so chips get the full width (rows 125px). Desk cards: chips `flex-wrap` with the chevron absolutely placed at the card's bottom right. | S | — |

Already known and waiting on Nathan, with my weigh-in:

- **The red "Compare with another city" button.** On both widths it's the only filled button
  above the card, so it reads as the page's main action. And the page ends with a second
  filled "Compare cities" (`screens/city-390-austin-from-search.png`). I'd make the top one
  outlined, like "Change your search", and keep the bottom one filled.
- **City descriptions' rounding.** When they're regenerated, also avoid the double "about"
  ("about 2.4 million people about three hours west of Houston").

---

## 6. Top ten, in the order I'd build them

Quick wins (size S, can ship alone) are marked ★.

1. ★ **R01, the keyboard path to "Refine your search" (S).** An accessibility failure on
   every phone and tablet with a keyboard, fixed by changing how the bar hides.
2. ★ **R03, bring the opened card detail into view (S).** One line, and the most-clicked
   thing on the desk stops looking broken.
3. ★ **R02, the site's own icon; the starter files gone (S).** The rename isn't finished
   while every tab shows Vercel's logo.
4. ★ **R04, the starting-search note on city pages (S).** The pages search engines bring
   people to stop telling them a rank is theirs.
5. ★ **R07, robots, sitemap, canonical (S).** Search engines get a map, and one address per
   city.
6. **R05, chips and bars that agree (M).** The "why" stops contradicting itself. The API
   serves one contribution per chip item (a small, additive model change); the page draws
   it.
7. ★ **R09, "/100" on rows and Compare (S).** Every score says what it's out of again.
8. ★ **R06, an honest caption for the bars (S).** A copy change; the arithmetic closes.
9. ★ **R08, the phone bar waits for #1's score to clear (S).** Still on the first flick
   of a thumb (53px at 390×844), without hiding the answer.
10. ★ **R12, security headers and a CSP (S).** The privacy promise becomes something the
    browser enforces.

Next: R10 (sharing), R11 (who made it), R22 (bars on the city card), R23 (streaming the
home page), R18 (fonts).

---

## 7. Measurements

How: `measure/README.md`. Cold runs (a fresh context, no cookie, empty cache). Round 3's
figures are its local build before Phase 6 (a Linux workspace); round 4's are the live site
(and the local build where marked).

### Page weight, transferred (KB)

| Page | Round 3 (390) | Round 4 live 390 | Round 4 live 1440 | of which images 390 / 1440 |
|---|---|---|---|---|
| Home (default) | 2,425 | **923** | 676 | 317 / 71 |
| Permalink | 2,425 | 923 | 678 | 317 / 71 |
| City: San Francisco | 1,129 | **403** | 404 | 79 / 79 |
| City: Deltona | 1,035 | 396 | 396 | 72 / 72 |
| City: Abilene | 1,023 | 372 | 349 | 44 / 44 |
| City: Champaign (no photo) | 578 | 331 | 353 | 3 / 3 (the map) |
| Compare | 316 | 288 | 288 | 0 |
| Compare: Austin–Denver | 373 | 345 | 345 | 0 |
| Compare: Austin–Abilene | 371 | 343 | 342 | 0 |
| How it works | 409 | 380 | 380 | 0 |
| What we measure | 341 | 313 | 324 | 0 |
| About the crime data | 316 | 288 | 288 | 0 |
| Stat: rent | 793 | 389 | 346 | 86 / 42 |
| Stat: everyday prices | 563 | 364 | 337 | 63 / 36 |
| Stat: political lean | 683 | 346 | 324 | 48 / 26 |
| Stat: places to go out | 1,133 | 463 | 380 | 160 / 78 |
| Stat: walkability | — | 425 | 357 | 122 / 55 |
| Stat: nice days | — | 377 | 342 | 75 / 40 |
| Stat: students | — | 400 | 345 | 97 / 43 |
| Stat: who lives here | — | 456 | 374 | 153 / 71 |
| Privacy / Terms / 404 | 315 / 317 / 311 | 287 / 289 / 282 | 287 / 289 / 282 | 0 |

Every page carries the same fixed part: HTML (4–308 KB), JS 130–149 KB in 8–10 files, CSS
11 KB, **fonts 138 KB (2 files)**. The home HTML is 307 KB gzipped (2.2 MB raw), because it
embeds the ranking with every "about you" variant (ADR 0018). Local and live agree within
10 KB on every page (`measure/local/m1_pages.json`).

### Speed (median of 5 runs, home; 3 runs, other pages)

| | TTFB | FCP | LCP (element) | CLS | Weight change → list settled |
|---|---|---|---|---|---|
| Round 3, 1440 | 411 ms | 612 | 612 (H1) | 0 | 443 ms |
| Round 3, 390 slow phone | 714 | 1,488 | 11,460 (#1 photo) | 0.032 | 7,857 ms |
| **Live, 1440** | 839 | 1,000 | **1,000** (H1) | 0 | **633 ms** |
| **Live, 390 slow phone** | 730 | 1,332 | **3,452** (#1 photo, the 1080px copy) | 0.031 | **1,780 ms** (pending line at 207 ms) |
| Local, 1440 | 154 | 216 | 216 (H1) | 0 | 296 ms |
| Local, 390 slow phone | 170 | 764 | 2,224 (#1 photo) | 0.031 | 7,989 ms (uncompressed locally) |

Other pages (live; local in brackets):

| Page | 1440 LCP | 390 slow-phone LCP (element) | CLS |
|---|---|---|---|
| City: San Francisco | 744 (132), the band photo | 992 (712), the H1 | 0.0004 |
| Compare: Austin–Denver | 596 (124), the starting-search note | 1,004 (680), the same | 0.0001 |
| Stat: rent | 196 (36), the photo | 2,072 (2,004), the photo | 0.0003 |

The phone's layout shift is the hero's subhead moving (at 4.2 s live, 3.1 s locally), likely
the web-font swap, as in round 3; at 0.031 it is well under the 0.1 "good" line
(`measure/live/m2_speed_live.json`, `shifts`). Phase 6 measured the phone LCP at 2.38 s
locally through a gzip stand-in; live, with the real network path and the 1080px copy a 3×
phone asks for, it is 3.45 s. The desk's first byte is R23.

### Where #1 sits (home, default search; `measure/local/m10_geometry.json`)

| Width × height | #1 top | #1 score bottom | Rows 4–10 | Round 3 score bottom |
|---|---|---|---|---|
| 1440×900 | 498 | 746 | 81 | 762 |
| 1280×720 | 498 | **746 (fold 720)** | 81 | 762 |
| 1120×800 | 498 | 730 | 81 | 746 |
| 1119×800 | 514 | **812 (fold 800)** | 103 | 812 |
| 1024×768 | 514 | **792 (fold 768)** | 103 | 792 |
| 768×1024 | 568 | 793 | 103–133 | 793 |
| 390×844 | 570 | 819 | **125–155** | 927 |
| 320×640 | 628 | 846 (fold 640) | 155–185 | 950 |

### Accessibility

- **axe** (all rules incl. best practice, and experimental): **0 violations** on 23 pages at
  1440 and 390 and on 14 home states at each (row open, row ⓘ, card open, the card's
  balance box, race chosen, age popover, rail/sheet with both groups open, slider ⓘ, find in
  results, header search, menu, narrowed, empty, same-sex) (`measure/local/m3_axe.json`).
- **Targets under 44×44 below 1120:** none outside running text, on any page or state at
  390, 768, 1024, 1119. Inline links (Terms' contact, Compare's "Make it your search") are
  exempt.
- **Text under 12px:** none. **Contrast where used:** no failure (the "median 43" hit is the
  known false positive; the label sits on white). **Control boundaries:** none under 3:1
  (`measure/local/m4_sizes.json`).
- **Keyboard** (`measure/local/m5_keyboard.json`, `measure/keyboard_bar.txt`): a visible
  ring on every stop at 1440 and 390, and no stop hidden under the bar. The sheet is
  a true modal (focus to Close, trapped, Escape returns to the bar). Info boxes open on
  Enter/click, not focus. The age popover returns focus on Escape. The menu closes on
  Escape (F28 fixed). The header search returns on Escape. **The bar is never reached
  going forward (R01).**
- **Reflow and motion** (`measure/local/m6_reflow_motion.json`): no sideways scroll on any
  page at 320 or at 200% (720×450); the sheet at 200% is 420 wide and scrolls inside.
  Reduced motion: 0 animations and 0 transitions through a weight change, a row opening and
  a photo hover.
- **Screen reader (accessibility tree):** landmarks and headings sound; rows read "Ranked 4:
  Los Angeles, CA · Biggest pluses… · 783,728 single men · Overall score 74 out of 100";
  the slider says "45 percent toward compatibility"; "Balance About balance" is R16.

### The server (`measure/live_site.txt`)

- **Compression:** HTML gzip (2.2 MB → 314 KB); JS and CSS gzip; `/api/rank` zstd (251 KB).
- **Caching:** static chunks and fonts `max-age=31536000, immutable`; photos, previews
  `max-age=604800`; maps a day; HTML `no-store`.
- **Redirects:** `dating-stats-atlas.duckdns.org`, `datingscenedata.duckdns.org` and
  `www.` → 301 to the same path and query on `datingscenedata.com`; `http` → 308.
- **Certificates:** Let's Encrypt, one per name, valid to 1–9 January 2027. TLS 1.2 and 1.3
  accepted, 1.1 refused (1.0 untested: this Mac's OpenSSL can't offer it).
- **Exposure:** `/v1/health`, `/v1/meta` → 404 through the site; `/api/rank` with the
  visitor's sex → 422.
- **Missing:** `robots.txt`, `sitemap.xml`, canonical links (R07); the site's own icon (R02);
  security headers beyond `Referrer-Policy` (R12).

---

## 8. The photographs

All 193 ranked cities, as the desk card (16:10) and the phone card and city band (16:7) crop
them, in default rank order: `screens/photos/sheet-01.jpg` … `sheet-10.jpg`
(`measure/photo_sheets.mjs`). Phase 6's replacements read well. What still goes wrong:

| City (rank) | What goes wrong | Suggestion |
|---|---|---|
| San Jose, CA (#5) | A hotel front at Santana Row, "Hotel Valencia" on the façade; it shows as a top-three card in narrowed searches. Reads as a resort, not as San Jose. | Downtown San Jose (the skyline over Plaza de César Chávez, or the Guadalupe River Park) |
| Charleston, SC (#65) | Rainbow Row behind parked cars, an SUV foremost (round 3's New Orleans issue) | A crop higher (`50% 20%`), or a car-free view of Rainbow Row or the Battery |
| York, PA (#178) | 1024×768, upscaled in the 1,056px band (2× on a retina laptop) | A larger original |
| Reno, NV (#105) | 900×600, upscaled (known since round 3) | A larger original |
| Peoria, IL (#104) | A bank's octagonal logo on a white tower is the brightest mark in the frame, with a Caterpillar sign further right | Leave it (logos are part of any skyline), or a view from the bluffs |
| Fargo, ND (#56) | The band reads "FARG" (known, PHASE6 3e) | The card shows it whole; leave it, or a wider original |

**Alt text:** Indianapolis's is "indianapolis" and Montgomery's a library record (§9 has
drafts); 11 unranked cities have raw or empty alts and about 20 name the place only (R13).

**With the almanac direction:** still a good fit; the medallion and numbers sit under the
photo, not over it. Mixed light (dusk in Atlantic City, Augusta and Dayton beside noon
skylines) still makes neighbouring cards feel unrelated, as round 3 said.

---

## 9. Copy drafts (all DRAFT, for Nathan's approval)

Registry keys are in `atlas/pipeline/registry/features.yaml` under `strings:` unless noted.
No banned word; nothing touches political lean.

| Key | Old | New (DRAFT) | Finding |
|---|---|---|---|
| `col_city` | City · why it ranks here | City · lifestyle pluses and minus | R05 |
| `moved_caption` | Compared with the median city | Compared with a city in the middle on every measure | R06 |
| `city_default_note` (new) | — (the city page has none) | These figures use the site's starting search: {search}. Set your own on the home page and it follows you here. | R04 |
| `make_it_your_search` (new; today a literal on Compare) | Make it your search | Make it your search | R04, R15 |
| `back_to_rankings` (new) | ← Back to your results (when there's no search) | ← See the rankings | R04 |
| `back_to_results` (new; today a literal) | ← Back to your results | ← Back to your results | R15 |
| `city_card_heading` (new; today a literal) | Where {city} lands for your search | Where {city} lands for your search | R15 |
| `city_rank_of` (new; today a literal) | of {n} cities | of {n} ranked | R15 |
| `compare_spot` (new; today a literal) | Spot in your results | Spot in your results | R15 |
| `compare_same` (new) | 0 | Same | R14 |
| `compare_unjudged_by` (new) | −600,000 | {city}, by {diff} | R14 |
| `share_copy` / `share_copied` (new) | — | Copy link / Link copied | R10 |
| `shared_link_prompt` (new) | — | This link doesn't say whether you're a man or a woman. Set "I'm a" to see your own compatibility figures. | R10 |
| `footer_contact` (new) | — | Contact: hello@datingscenedata.com | R11 |
| `about_who` (new; How it works, under "How are the numbers made?") | — | Dating Scene Data is made by {name}, independently. It takes no advertising and sells no data. | R11 |
| `SITE_DESCRIPTION` (`web/src/lib/chrome.ts`) | Which city has the best dating scene for you? Estimated from the Census Bureau's own survey, city by city. | the registry's `home_subtitle`, as it stands | R17 |
| 404 `<title>` (code) | Dating Scene Data | Page not found · Dating Scene Data (`not_found_title` through `title_template`) | R17 |
| Indianapolis `alt` (`src/data/city-images.json`) | indianapolis | Downtown Indianapolis from above on a clear day, its twin-spired tallest tower at the centre and an arena's arched roof in the foreground. | R13 |
| Montgomery `alt` (`src/data/city-images.json`) | Title: Aerial view of Montgomery, Alabama… (a library record) | Downtown Montgomery from the air, with the riverboat landing and the long train shed on the Alabama River in the foreground. | R13 |

The hero's "Based on Census data." keeps its words and becomes a link to How it works (R11).

---

## 10. Open questions for Nathan

1. **The icon (R02).** What should the mark be? My suggestion is a Fraunces "D" in white on
   the berry accent. Should the five starter files and `hero.jpg` go?
2. **The "why" (R05, R06).** May the detail split cost of living and social life into
   their items, so the bars agree with the chips? Which header wording do you want for the
   chips? And may "Compared with the median city" become "…a city in the middle on every
   measure", given the bars don't add up to the median shown?
3. **Cold arrivals (R04).** Show Compare's starting-search note on city pages too, and "See
   the rankings" instead of "Back to your results" when there's no search?
4. **Sharing (R10).** A "Copy link" button that copies the page's own address (not the
   permalink, which ADR 0004 keeps out of the UI)? And the one-line prompt when a shared
   link arrives with no "I'm a" stored?
5. **Who makes the site (R11).** Are you willing to be named on How it works, and to put the
   contact address in the footer?
6. **Compare's unjudged rows (R14).** "Same" for a tie and "Denver, by 600,000" for Who lives
   here, instead of "0" and "−600,000"?
7. **Security headers (R12).** May the Caddyfile add HSTS and a CSP at the next deploy?
8. **Photos (R20).** Replace San Jose's hotel front? Charleston's crop, York and Reno?
9. **The red Compare button.** My weigh-in: make it outlined, as "Change your search" is.

Which of these do you want built? The implementation brief (`atlas/PHASE7_PROMPT.md`) waits
for your answer.
