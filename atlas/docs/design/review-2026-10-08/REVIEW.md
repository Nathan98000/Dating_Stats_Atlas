# Design review, round 3: the site after Phase 5

Reviewed 8 October 2026 (started 22:04 EDT). Branch `claude/phase5` at `f18a810`, build
`63c4e5fa51bf`, model `m4.2.1`, as a local production build (`next build` with
`NEXT_DIST_DIR=.next-review`, `next start -p 3300`, the API on the real build). The
live site still runs Phase 4 (nav "Home · Compare cities · About the site", m4.2.0), so
it was checked only for what the server alone shows (`measure/live_site.txt`).

**Where it ran.** The scripts ran in a Linux cloud workspace, not on your Mac: Chromium
141 headless through Playwright 1.63 from `atlas/web`, 2 CPUs. The repo, the build and
the photographs were copied from the main checkout at `f18a810` (photos included), so
nothing in the worktree or in `atlas/web/tsconfig.json` on your machine was touched.
Absolute timings will differ from your Mac's; the throttled phone profile is the same
as Lighthouse's, and every comparison below is like for like.

Everything cited is in this folder: screenshots in `screens/`, scripts and raw outputs
in `measure/` (its README lists how to re-run them). Copy is marked DRAFT throughout.

---

## 1. In plain words

1. **Phones wait for photographs.** The home page sends 2.4 MB, and 1.8 MB of it is
   three photos shown at thumbnail size. Each is the full 1,920-pixel original. It is
   like mailing someone a poster so they can look at a postage stamp. On a typical
   phone connection the first city's photo, the biggest thing on the screen, finishes
   at **11.5 seconds**. Sending a copy sized for the card brings that to **2.0
   seconds**, with the photos unchanged to the eye. Separately, the search results
   travel uncompressed (1.5 MB a time). Switching on the compression you already
   built (commit A) cuts the wait after each change on a phone from **7.9 s to 1.9 s**.
2. **The same-sex search overstates the number that matters most.** A man looking for
   men 28–38 is told "903,150 matches" in New York. That is every single man of those
   ages. The Census doesn't ask who people date, so the number of possible partners is
   a small share of that. Nothing on the page says so. For a gay or lesbian visitor
   the headline figure reads as many times too large, and the ranking leans on it.
   This needs one honest sentence where the number appears; whether the model should
   change is a separate question for you.
3. **A few numbers say the opposite of what they mean.** On Compare, "▲ Abilene
   +$526" means Abilene's rent is $526 *lower*. "Who lives here" rounds the
   population and the adults separately, so Abilene reads "200,000 people, of whom
   100,000 are adults" (it has 183,310 people), and Champaign reads "about 250,000"
   right above a note saying it is too small to rank (the floor is 250,000). And the
   API sends a caution for 15 ranked cities ("a notable share of adults here live in
   … dorms or barracks") that no page shows.
4. **On a phone, changing what matters feels like nothing happened.** The sheet closes
   onto the old list, the progress line is over 2,000 pixels up the page, and the new list
   arrives 6 seconds later, out of sight. Nothing says what moved. And the top three
   cards, the cities a visitor cares about most, are the only results with no "why"
   behind them.

Two more you should know about. The slider thumbs and the city-name links are under
the 44×44px touch size the project requires below 1120px, and a screen reader hears
nothing when choosing your own race reorders the whole list.

---

## 2. What works (keep it)

- **The first screen at the desk.** The headline, the one-line search sentence and
  the #1 card all fit in 1440×900 (#1 card top at 514px, its score at 762px). It says
  what the site does in five seconds (`screens/home-1440-first-screen.png`).
- **The quick-search sentence** ("I'm a [Woman] aged [30], looking for [Men] aged
  [28–40]"). It is the clearest control on the site.
- **The rail's three groups.** "Narrow it down" summarises itself when closed ("Single:
  never married or divorced/widowed · Any education · Any income · All races"). Its own
  scroll works: at 1280×720 only 84px is hidden, behind a visible fade
  (`screens/home-1280-rail.png`). I found no evidence against your scroll-bar decision.
- **Compact rows.** 81px at the desk, 133px on phones. The three-tile detail and the
  "What moved the score" diverging bars with signed points read well
  (`screens/home-1440-row-expanded.png`).
- **The empty state.** "This one's a tall order almost anywhere", with three buttons
  that each restate the search they'd run (`screens/home-1440-empty.png`). The
  near-empty count line is honest too (`screens/home-1440-near-empty.png`).
- **Accessibility basics.** axe reports **0 violations** on all 19 pages at 1440 and
  390 and on 11 interactive states (all rules, best practice included). No text is
  under 12px. No text fails AA contrast where it is used. Nothing scrolls sideways at
  320px or at 200% zoom. Reduced motion stops every animation and transition (0 of 7).
  A focus ring is visible on every tab stop.
- **The sheet.** It is a real modal: focus starts on Close, stays inside, and Escape
  returns it to "Adjust your search". The age popover does the same.
- **The privacy architecture holds.** The cookie holds only the partner search and
  your age (`dsa_prefs=self_age=30&sex=male&age=28-40…`), and the rank request body
  carries no "about you" detail.
- **Most photographs read as their place**, and the 35%-high crop keeps towers and
  domes. About 160 of 193 are good or better (§7).
- **Political lean** is neutral, ordered Democratic · everyone else · Republican, with
  text on every colour and name-order sorting by default.
- **Compare on phones** stacks with no sideways scroll; the crime block keeps the FBI's
  caution.
- **Tone.** The copy is plain and modest ("This doesn't mean nobody matches that
  description, but…").

---

## 3. The cold read

I used the site before reading any project document: first at 390 (touch), then at
1440. Full notes: `measure/cold_read_notes.md`.

### First visit, 390

- *Clear in five seconds.* The headline and the 2×2 quick search say what the site
  does. The eye lands on the Golden Gate Bridge photo at the bottom of the screen, but
  the #1 city's name and score sit below it, under the fold (score at 927px; screen
  844px) (`screens/home-390-first-screen.png`).
- *Where do I say what matters?* Nothing on the first screen. "Adjust your search"
  appears only once the quick search scrolls away.
- *Confusing:* cards say "266,309 matches", rows say "783,728 single men match".
- *Confusing:* a footnote explains "Balance", but no balance figure appears on any
  card or closed row.
- *Repetitive:* every chip row reads "▲ Dating pool ▲ Compatibility ▼ Rent".
- *Impressive:* the sheet is clean and quick. The row detail's three tiles are tidy.
- *Wrong turn:* after setting Cost of living and Weather to "A lot" and Social life to
  "Not much", I pressed "Show results". The sheet closed and left me at rows 9–10
  (scrollY 2,500), with no sign anything had changed.
- *Wrong turn:* I tapped ⓘ on Balance and the box covered the balance figure it
  explains. ⓘ on "What moved the score" covered the top three bars
  (`screens/home-390-info-balance-open.png`, `…-info-moved-open.png`).
- *Puzzling:* Houston's compatibility is 97, "where 100 is the US average", yet "What
  moved the score" gives Compatibility **+0.9** points.
- *Puzzling:* the chip says "▼ Students", the bar says "Student life", and the
  control says "Student life".
- *City page:* good. "4 of 193 cities for men 28–40, never married or divorced or
  widowed" is clunky.
- *Abilene:* "sits below the population floor this site ranks". The floor isn't
  stated. "200,000 people, of whom 100,000 are adults" looked wrong to me at once.
- *Polish:* the header search has a blue browser "×" next to the site's own close "×"
  (`screens/header-390-search-abilene.png`).

### First visit, 1440

- *Strong first view:* the rail and the top three cards are in the first screen.
- *Wrong turn:* I tried to open the #1 card for its detail. There is no control. Only
  rows 4 and below have one.
- *Surprising:* with Cost of living at "A lot", Boston (#1) and San Francisco (#2),
  the two priciest metros, stay on top. Nothing explains why. Pool and compatibility
  carry most of the weight, and "Not much" is a 0.4 floor
  (`screens/home-1440-cost-a-lot.png`).
- *Compare:* the banner "These figures use the stated default search… Change anything
  on the home page and they become yours" appeared in warning amber. But the default
  *was* my search. The Edge column read "▲ Denver −31,802"
  (`screens/compare-1440-austin-denver.png`).
- *Missing:* nothing anywhere showed that "266,309" is an estimate.

### The tasks

Times are what the browser took, not a human. Steps count taps, clicks and keys, typing
excluded.

| Task | 390 (touch) | 1440 | Wrong turns | Where the answer was |
|---|---|---|---|---|
| 1. Woman 30, men 28–40: best three and why | 0 steps (it is the default search). #1 at 656–1,018px, #3 ends at 1,774px. The "why" is three identical chip rows; to see balance, compatibility and what moved for #1–#3 I had to open three city pages. | 0 steps. All three cards in the first screen. The same "why" gap. | Tried to expand a card (no control). | The answer is on the cards; the reasons are one page further for #1–#3. |
| 2. Cost and weather a lot, social life less | Scroll about 425px before the bar appears, then 1 tap for the sheet, 3 taps, and "Show results". The list lands **6.4–7.9 s** later, about 2,200px above where I was, at today's transfer size. The new top three (Austin, Boston, San Francisco) are only visible after scrolling up. | 3 clicks in the rail; settles in **0.44 s**. The top three reorder. | "Show results" left me at row 9; no mark of what moved; chips unchanged. | It makes partial sense: Austin rises, but the priciest cities stay top three and the page never says why. You can't tell what moved. |
| 3. Austin or Denver? | Menu → Compare → two pickers → "Compare these two": 6 taps. Or expand Austin's row → Compare → one picker → button: 5 taps. | Same, 4 steps. | The Edge column's signs ("▲ Denver −31,802"). | Austin 67 vs Denver 65, #9 vs #11 (`screens/compare-1440-austin-denver.png`). |
| 4. What does a compatibility of 72 mean? Trust the matches? | Row detail: "where 100 is the US average"; the slider's ⓘ; "How the score works" below the list. | Same. | None; but the meaning of "100" vs the bars' "+ points" conflicts (§4, F22). | Meaning: on the page. Trust in matches: **not on the page.** No margin, no caveat, and the per-city cautions the API serves are never shown. "How it works" says only that counts are estimates and noisy cities are dropped. |
| 5. Man 33, men 28–38 | "I'm a: Man" flips "Looking for" to Women, so 2 changes are needed; plus "My age" and the age popover. The 20px slider thumbs are fiddly; I used arrow keys. 6 steps. | Same, 6 steps. | The silent flip to Women (`screens/home-390-sex-flip.png`). | San Francisco #1, 237,358 "matches". No word that this counts every single man (`screens/home-390-same-sex-cards.png`). |
| 6. Where does Abilene stand? | Search icon → "Abil" → tap the option: 3 steps. | Type in the header field → Enter: 2 steps. | None. | "Abilene sits below the population floor this site ranks." The floor isn't stated (`screens/city-390-abilene-top.png`). |

---

## 4. Findings

Most severe first. Sizes: S ≈ an hour or two, M ≈ a day, L = more. "Evidence" points to
`screens/` or `measure/`.

| ID | Sev | Page · width | What I saw (evidence) | Who it hurts, how | Recommendation | Size | Tags |
|---|---|---|---|---|---|---|---|
| F01 | Blocker | Home, city, compare · all | Same-sex search (man 33 → men 28–38): "903,150 matches" in New York, 237,358 in San Francisco. These count every single man of those ages. The only same-sex note is behind the slider's ⓘ and is about compatibility (`screens/home-1440-same-sex.png`, `…-same-sex-slider-info.png`). Balance shows "110 men per 100 women" with no word on reading it. "How it works" defines the count by the filters alone (sex, age range, marital status, and any education, income or race filters), with nothing about who people date. | Gay, lesbian and bisexual visitors. The headline figure reads as potential partners and is many times too large. With pool at 30% of the default weights, the ranking leans to the biggest metros for a reason that doesn't hold the same way. | **Presentation (buildable now):** on a same-sex search, show a served note under the results heading, under "N people match" on the city score card, and under "People who match" on Compare (copy §8, `same_sex_pool_note`); give balance a same-sex caption. **Model (separate):** whether a same-sex pool should be scaled by a measured share (for example ACS same-sex couples by metro) is a model question. | S (note), L (model) | copy, needs Nathan's decision, needs the model (part 2), reopens a decision (balance caption, ADR 0004 4c) |
| F02 | Blocker | Home, popover, sheet, city, compare, stats, footer · 390–1119 | Targets under 44×44 (`measure/m4_sizes.json`). Slider thumbs are **20×20** on the age range (two thumbs) and on "Bigger pool or closer match?" (the CSS sets them smaller still in Firefox). City-name links are 25px tall on cards and 20px on rows; they are the main way to a city page. "See all cities by …" links on city cards: 18–36px. Compare's city links: 21px. Stat pages: 193 city links at 19px. Footer "Terms": 38×44. The brand link: 26px tall (`screens/home-390-age-popover.png`). | Thumb and motor-impaired users. It is the project's own requirement. A slightly-off tap on a row's name expands the row instead of opening the city. | Below 1120: range inputs 44px tall, with a 28px visible thumb (a transparent 8px border makes the 44px hit). Add two 48px number fields, "From [28] to [40]", inside the age popover for exact ages. City-name links `block min-h-11` (44px; rows: the name cell becomes the link's box). "See all…", stat-list and compare links `inline-flex min-h-11 items-center`. Footer links `min-w-11`. Brand link `min-h-11 inline-flex items-center` (the token sizes, no arbitrary values). | M | — |
| F03 | Major | Home, city, stats · all, worst on phones | Home sends **2,425 KB**, of which images are 1,810 KB (3 files). The photos are 1,920px originals shown at 249×155 (desk) and 356×178 (phone), with no `srcset`, no lazy loading, no `fetchpriority`. They are served `Cache-Control: public, max-age=0`, locally and live, so they are revalidated on every view. Phone (Lighthouse mobile profile): **LCP 11.46 s**, and the LCP element is card #1's photo (`measure/m2_speed_local.json`). The same page with 720px WebP copies: **LCP 1.98 s**, photos 37–76 KB each (`measure/m2b_image_sim.json`). City band: 533 KB for 358×157. Largest file: Dallas, 3.1 MB. | Every phone visitor on cellular: an 11-second first impression and data used. | Keep the photographs (your decision); change only delivery. At build, make derivatives: cards at 480/720/1080 wide, bands at 768/1280/1920, WebP (AVIF optional), from the pinned originals. Use `<img srcset sizes>`; for cards, `sizes="(min-width:1120px) 250px, (min-width:768px) 33vw, 100vw"`. Card #1: `fetchpriority="high"`, eager. Cards #2–#3 on phones and every band below the fold: `loading="lazy" decoding="async"`. Add `width`/`height`. Serve `/cities/*` and `/stats/*` with `Cache-Control: public, max-age=31536000, immutable` under content-hashed names, or `max-age=604800` if names stay. | M | — |
| F04 | Major | Home · phones | `/api/rank` is **1,476,577 bytes** raw from `next start` for the default search (`measure/rank_bytes.json`; 1,478,916 with the weights the page sends) and **1,503,429** raw on the live site (no `content-encoding`; `measure/live_site.txt`). On the phone profile, a weight change takes **7.86 s** to land; through a gzip stand-in for Caddy's `encode`, **1.88 s** (`measure/m2_speed_gzip.json`). | Phone visitors on every change. | Deploy commit A (already built and waiting on you). It is the largest speed gain per minute of work on the site. | S | needs Nathan's decision (deploy) |
| F05 | Major | Home · 390–1119 | After a change in the sheet, "Show results" only closes it. The old list stays in view, `aria-busy="true"`, and the progress line sits at the results header, about 2,200px above. The list lands **more than 6.4 s** after the tap (timed from half a second after it), out of sight (`measure/m9_pending.json`; `screens/home-390-reweight-sheet.png`, `…-after-show-results.png`, `…-landed.png`). Nothing marks what moved. The live region text is for screen readers only. | Phone and tablet visitors on the second core task ("can you tell what moved?"). It fails. | (1) "Show results" closes the sheet, then scrolls to and focuses the results heading (`tabindex=-1`, `scroll-margin-top:16px`). (2) While pending, draw the same 2px `--accent` indeterminate line along the top edge of the sticky bottom bar. (3) When the list lands, tint rows that changed place with `--hover` for 2 s (the find-in-results highlight already does this), and show the existing `results_updated` line visibly under the heading for 6 s, followed by "New top three: A, B, C" (names only, no new numbers; §8). | M | copy |
| F06 | Major | Home · all | The top three cards have no detail control. Rows 4+ open balance, compatibility and "What moved the score"; cards show only chips. `featured-card` has no `row-toggle` (DOM). Task 1's "why" for #1–#3 took three city-page visits. | Everyone: the three cities that answer the main question explain themselves least. | Give each card the rows' "Details" chevron (44×44, `aria-expanded`, `aria-controls`) at its bottom right, opening the same three tiles (`RowDetail`, tile mode). At ≥768px, use one full-width panel under the card row; on phones, inside the card. | M | — |
| F07 | Major | Compare · all | The Edge column puts the winner over the plain A−B difference. So it reads "▲ Denver −31,802", "▲ Denver −4", "▲ Austin −2" (spot in results) and **"▲ Abilene +$526"**, where Abilene is the *cheaper* city. Screen readers hear "Denver −31,802" (`screens/compare-1440-austin-denver.png`, `…-austin-abilene.png`; `measure/m7_aria.txt`). ADR 0007's sign rule predates the Edge column (Phase 5 F). | Anyone comparing: in Austin–Denver the sign contradicts the arrow on 7 of the 10 judged rows. | Show the winner and the size of its lead: "▲ Denver" over "by 31,802". That is the absolute value of the same plain subtraction of displayed values ADR 0007 sanctions; rent "by $339"; spot "by 2 places". Keep "—" rows as they are. New copy (§8). | S | copy |
| F08 | Major | Home rows, city page · all | The API serves a caution for **15 ranked metros** in the default search (`flags`). `gq_flag` ×11, e.g. Virginia Beach #47, New Haven #53, Fargo #56: "A notable share of adults here live in group housing such as dorms or barracks." `low_allocation_purity` ×5, e.g. Duluth, Roanoke, Longview: "Estimates here lean on survey areas this city shares with its neighbors." **No web code reads `flags`** (only `lib/types.ts`). Phase 2b showed them; commit `1cbddcd` (17 Sep) removed the chips without a record I could find. Phase 5 C still re-spelled the purity string. | Visitors weighing those cities, whose pools include dorms and barracks. It breaks the "uncertainty shown" promise with data already in hand. | Show the served policy string as one caption line (`--ink-2`, 13px) under "N people match" on the city score card, and at the top of the row and card detail. | S | needs Nathan's decision (was the removal deliberate?) |
| F09 | Major | City, compare · all | "Who lives here" rounds population and adults to different steps. Over all 387 metros, the shown population is off by **10% or more for 68** and by up to ±20% (Mansfield 125,160 → "150,000"; Staunton 124,589 → "100,000"). The implied adult share runs from 47% to 90%: **29 metros** read as under 60% adults (Abilene "200,000 people, of whom 100,000 are adults" for 183,310). Champaign reads "A college town of about 250,000 people" over "sits below the population floor" (floor 250,000) (`measure/who_lives_here.json`; `screens/city-390-abilene-cards.png`, `city-1440-champaign.png`). Compare differences inherit it ("+2,200,000"). | Anyone reading a city card: visible contradictions cost trust in every other number. | Keep survey-honest rounding, but round both figures, and the description, to 2 significant figures: "180,000 people, of whom {adults to 2 significant figures} are adults"; Champaign "about 240,000". These strings are composed by the API. | S | needs the model |
| F10 | Major | Home rail and sheet · all; Privacy | "Sharpen compatibility" asks for your race and education under nothing but an "Optional" pill (`screens/home-1440-sharpen-open.png`). Phase 4b dropped inline notes "because the Privacy page explains it". It doesn't quite: /privacy says "Your own browser will keep details about you", but never that they are not sent (`screens/privacy-1440-full.png`). | Visitors deciding whether to give their race. Those who decline lose the race-on figure; those who give it have no reason to believe it stays local. | (a) Add one sentence to the Privacy page saying these details never leave the browser and why (§8). (b) Put an ⓘ (the existing InfoTip) beside "Optional", whose box explains the mechanism and links to Privacy. That is an explanation on demand, not the deleted line back. | S | copy; (b) reopens a decision |
| F11 | Major | How it works · all | "The compatibility **score** is built from real couples… we measure how often each age gap, education pairing, and **racial/ethnic pairing** actually occurs." Race is used only if you include your own (ADR 0018 §2), and the figure is "never called a score" (§1). The registry's `match_how` already has it right (`screens/about-1440-full.png`; `docs/methodology.md` lines 47–52). | Visitors deciding whether to share race, told it is always used. | Replace those lines with the `match_how` wording (§8). | S | copy |
| F12 | Major | Home rows and cards · all | Chips repeat. In the default search, 8 of the top 10 read "▲ Dating pool ▲ Compatibility ▼ Rent"; Chicago and Philadelphia "▼ Everyday prices". After Cost of living "A lot", the top three's chips don't change (`screens/home-1440-cost-a-lot.png`). In the same-sex search the top three are identical again. | Everyone reading the list for "why": the chips don't tell cities apart. | I'd take PHASE5 §3f's option: chips show the two largest **lifestyle** movers (with their signs), served as data (`lifestyle_movers`), while the pool and compatibility keep their own column and tile. Keep `summary_line` for screen readers as it is. | M | needs the model, needs Nathan's decision |
| F13 | Major | Home · all | Choosing "My race or ethnicity" (or education) reorders the whole list at once. In the default search, choosing Black makes the top three New York, New Orleans, Philadelphia (Hispanic: Los Angeles, New York, Miami; White: Boston, Pittsburgh, Portland), but the live region stays **empty**: it is only set after a fetch, and an "about you" change makes none (`screens/home-1440-race-chosen.png`). | Screen-reader users: the ranking changes with no word. | Announce about-you changes through the same polite region with `results_updated` ("Results updated for your race or ethnicity" / "your education"). | S | copy |
| F14 | Minor | Home, city, compare · all | Matches show to the person ("266,309") while the API serves `pool_moe` 5,221. ADR 0004 hides margins, and suppression is the only visible uncertainty. Close compare pairs can show an "Edge" inside the margin. | Visitors who read 266,309 as an exact count. | Either show the served margin on the city score card and Compare's row ("± 5,221"), which reopens ADR 0004, or serve a rounded display ("266,000"), which needs the model. My pick: the served margin on the city page only. | S | reopens a decision, needs the model |
| F15 | Minor | Home · 390, 320, 1024×768, 1280×720 | #1's name and score are below the first screen: score bottom 927px vs an 844px viewport at 390; 950 vs 640 at 320; 792 vs 768 at 1024; 762 vs 720 at 1280 (`measure/m10_geometry.json`). At 390 the first screen ends on a photo with no name. | Phone visitors on a first look. | Below 640: put Best/Worst to the right of the count line, or below the three cards (saves 76px), and make the card photo 16:7 (saves 22px). The score then ends at about 829px. | S | — |
| F16 | Minor | City · 1440 | The photo band (1056×462) sits above the score card, so "Where San Francisco lands for your search" starts at **917px**, below a 900px screen (`screens/city-1440-sf-first-screen.png`). Phase 5 G asked for a page "led by the score". | Desk visitors arriving from a link. | Order: title → score card → photo band → "What X is like"; or score card and band side by side at ≥1120. | S | — |
| F17 | Minor | Home row detail · all | Info boxes cover what they explain: the balance figure and the top three bars (`screens/home-390-info-balance-open.png`, `…-info-moved-open.png`). They also open on keyboard focus, so tabbing through a detail pops boxes over content. | Everyone using ⓘ; keyboard users. | Keep them floating above everything (your decision). Anchor them to the tile's edge (above the tile when there is room, else below its bottom edge), not under the button. Open on click and Enter; on hover only for pointer devices; not on focus. | S | — |
| F18 | Minor | Home ↔ city · all | After "Show all 193" and opening #50, both "← Back to your results" and the browser's Back return to the top with 10 rows (scrollY 0 or 1,255; was 4,313). | Anyone browsing past the first ten. | Keep `{visible, cbsa}` for the results in `sessionStorage` (no about-you detail) and restore. "Back to your results" calls `history.back()` when the previous entry is the results. | S | — |
| F19 | Minor | Home sheet · 390–1119 | Sex and ages are only in the hero (Deviation 7). The sheet titled "Adjust your search" can't change them; from row 10 it's a 2,000px scroll up. | Phone visitors refining ages after seeing results. | At the top of the sheet, add one row: "Woman, 30 · Men 28–40 — Change". It closes the sheet, scrolls to the quick search and focuses "I'm a". | S | copy |
| F20 | Minor | Home quick search · all | Setting "I'm a" to Man silently flips "Looking for" to Women (`screens/home-390-sex-flip.png`). | Gay men, whose natural first change undoes their search. | Flip only while "Looking for" hasn't been touched this visit, and announce it ("Looking for changed to Women"). | S | copy |
| F21 | Minor | Home, city, compare · all | One figure, five names: "matches" (cards), "single men match" (phone rows), "single men" (desk rows), "people match what you're looking for" (city), "People who match" (compare), plus "dating pool". Chips name features ("Rent", "Students"), the bars name pillars ("Cost of living", "Student life"). | First-time visitors working out what's what. | Use "matches" for the count everywhere, including phone rows (the open item in PHASE5 §7; I'd shorten). Give bar labels the chip word where they differ: "Cost of living · rent". Rename the students chip "Student life". | S | copy |
| F22 | Minor | Row detail · all | Houston's compatibility is 97, "where 100 is the US average", yet it adds **+0.9 points**. The bars compare with the middle of the ranked cities, and that caption is behind ⓘ. | Anyone reading the two side by side. | Show `moved_caption` under "What moved the score" always (12px `--ink-3`), not only in the box. | S | copy |
| F23 | Minor | Compare · all | The "stated default search" banner, in warning amber, tells a visitor whose search *is* the default that these figures aren't theirs yet (`screens/compare-1440-austin-denver.png`). | Default-search visitors (most first visits). | Use a neutral note style (`--sunken`, `--ink-2`, no border) and new copy (§8). | S | copy |
| F24 | Minor | Compare, city · all | Below-floor cities: "Not covered" and dashes, unexplained (`screens/compare-1440-austin-abilene.png`). Both "Not covered" and the floor sentence are **hard-coded** in `compare-variant.tsx:67`, `compare/[a]/[b]/page.tsx:257` and `city/[slug]/page.tsx:146`, not in the registry. | Anyone comparing with a smaller city. | Move both into the registry and state the floor (§8). | S | copy |
| F25 | Minor | Row detail · all | The balance tile drops "Even" under the centre tick, which the city page and Compare show (`screens/home-390-row-expanded.png` vs `city-390-houston-score.png`). | Anyone reading the dot's position. | Show "Even" in the tile too (it fits the 176px box at 12px). | S | — |
| F26 | Minor | Home, city · all | Screen readers hear: the row score as a bare "74" (no "score" or "out of 100"); headings "Balance Balance" and "What moved the score (points) What moved the score (points)" (the ⓘ button's name repeats the heading); two "About this figure" buttons on each city page (`measure/m7_aria.txt`). | Screen-reader users. | Add `sr-only` "Overall score" and "out of 100" around row scores. Name the buttons "About balance", "About these points", "About the violent crime figure" / "…property crime figure" (§8). | S | copy |
| F27 | Minor | Home · 390 keyboard | Focus lands under the sticky bar on 4 of 36 tab stops (Boston, San Jose, San Diego's details, "Show all 193"). The bar is reached only after the whole list (`screens/home-390-focus-under-bar.png`; `measure/m5_keyboard.json`). WCAG 2.2's 2.4.11, not 2.1. | Keyboard users on tablets and phones. | `html { scroll-padding-bottom: 88px }` while the bar shows; put the bar's markup before the results in the DOM (it stays fixed visually). | S | — |
| F28 | Minor | Phone menu · 390 | Escape doesn't close the menu (`aria-expanded` stays `true`) (`screens/header-390-menu-after-escape.png`). | Keyboard and switch users. | Escape closes it and returns focus to the button, as the sheet does. | S | — |
| F29 | Minor | City · all | 12 cities show a place elsewhere in the metro with no visible caption. Deltona's band is the Daytona Beach pier; only the alt text says so (`screens/city-1440-deltona-first-screen.png`). | Sighted visitors who know the city. | A caption under the band for those 12: "Daytona Beach, in the Deltona metro area" (13px `--ink-3`), from a new manifest field. | S | copy |
| F30 | Minor | Photos · all | Crops and weak photos, listed in §7. | Visitors who know the place. | Per-photo focal point (`object-position` in the manifest) and the replacements in §7. | M | needs Nathan's decision (subjects, trademark) |
| F31 | Minor | Sharing · all | Home: no `og:image`, `twitter:card=summary`. Permalink: `og:url` points to the home page, with a generic title and description. Stat pages have photos but no `og:image`. Compare pairs: a generic description (`measure/m1_pages.json`). | Anyone sharing a link: previews are bare, and permalinks collapse to the home page. | Permalinks: `og:url` = self, title from the results heading ("Top cities for single men, 28–40 · Dating Stats Atlas"). Stats: their photo as `og:image`. Home: a 1200×630 image. | S | copy |
| F32 | Minor | City · all | City HTML is 281 KB compressed (919 KB raw); 304K characters of it are the inline locator map's path data. | Phone visitors on city pages. | Serve the locator as a static, simplified SVG file (`/map/<cbsa>.svg`, about 10 KB), and pass only the strings a page uses. | S | — |
| F33 | Minor | Stat pages · all | The sort control differs from the home page's segmented control (filled berry selected; unselected border 1.23:1). At 1440 the header photo is pillarboxed in a white box (`screens/stat-390-rent-top.png`, `stat-1440-lean-top.png`). | Consistency; the unselected options barely read as buttons. | Reuse the Segmented component. Let the stat photo's box take the photo's own aspect, uncropped as the ADR requires. | S | — |
| F34 | Polish | Several | Copy: "Lifestyle" explainer starts lowercase ("four things you weight —"); "never married or divorced or widowed"; the near-empty line says "cities" where the header says "metro areas"; the quick search wraps "aged" alone at 768 (`screens/home-768-first-screen.png`). | Readers. | §8 drafts. At 640–1119, let the age token share the line (`flex-wrap` with the label kept on its token). | S | copy |
| F35 | Polish | Header search, compare pickers · all | The browser's blue search-clear "×" is off-palette, and sits beside the site's own close "×" (`screens/header-390-search-abilene.png`). | Visual consistency. | `input[type=search]::-webkit-search-cancel-button { appearance:none }`, plus the site's own 44×44 clear button in `--ink-3`. | S | — |
| F36 | Polish | 404, short pages · 390 | About 215px of empty paper below the footer on the 404 (`screens/404-390-full.png`). | Looks unfinished. | Body as a flex column with `main` growing, so the footer sits at the bottom. | S | — |
| F37 | Polish | Quick search · all | axe (experimental) `label-content-name-mismatch`: the age token's name "Their age: 28 to 40" vs visible "28 – 40". | Voice-control users. | Name it "Their age 28 – 40" (visible text included verbatim). | S | — |

---

## 5. Top ten, in the order I'd build them

1. **F04 Deploy compression (S).** Already built. It cuts every phone weight change
   from 7.9 s to 1.9 s.
2. **F03 Right-sized, cached photographs (M).** Phone LCP 11.5 s → 2.0 s, and 1.7 MB
   less per home view, with the photos unchanged to the eye.
3. **F07 Compare's Edge "by" (S).** One template change removes a sign that
   contradicts its arrow on most rows (7 of 10 in Austin–Denver).
4. **F01 The same-sex note (S).** One served sentence brings the headline figure in
   line with the site's honesty promise for a whole audience. The model question can
   follow at your pace.
5. **F08 Show the served cautions (S).** The data is already in every response; it
   fulfils "uncertainty shown" for 15 cities.
6. **F02 Touch targets (M).** It is a requirement, and the sliders and name links are
   the controls people use most.
7. **F05 Feedback after a change on phones (M).** It makes the second core task work:
   you see that it changed, and what.
8. **F06 Details on the top three cards (M).** It answers "why" for the cities that
   matter most without leaving the page.
9. **F10 + F11 Privacy and How it works copy (S).** Trust at the moment of asking for
   race, for an hour's work.
10. **F13 Announce about-you changes (S).** Screen-reader parity for the one change
    that reorders everything silently.

Next, needing the model: **F09** (rounding, small) and **F12** (lifestyle chips).

---

## 6. Measurements

How: `measure/README.md`. All runs were cold (a fresh browser context, no cookie, empty
cache) against the local production build.

### Page weight (390 and 1440 are within 24 KB; transfer as received, compressed where served compressed)

| Page | HTML | JS (files) | CSS | Fonts | Images (n / KB) | Total |
|---|---|---|---|---|---|---|
| Home (default) | 291 KB | 150 KB (10) | 10 KB | 138 KB | 3 / **1,810** | **2,425 KB** |
| Permalink | 291 | 150 (10) | 10 | 138 | 3 / 1,810 | 2,425 |
| City: San Francisco | 281 | 141 (9) | 10 | 138 | 1 / 533 | 1,129 |
| City: Deltona | 281 | 141 (9) | 10 | 138 | 1 / 439 | 1,035 |
| City: Abilene | 240 | 142 (10) | 10 | 138 | 1 / 446 | 1,023 |
| City: Champaign (no photo) | 240 | 142 (10) | 10 | 138 | 0 | 578 |
| Compare | 8 | 134 (9) | 10 | 138 | 0 | 316 |
| Compare: Austin–Denver | 60 | 138 (9) | 10 | 138 | 0 | 373 |
| Compare: Austin–Abilene | 58 | 138 (9) | 10 | 138 | 0 | 371 |
| How it works | 102 | 132 (8) | 10 | 138 | 0 | 409 |
| What we measure | 11 | 134 (9) | 10 | 138 | 0 | 341 |
| About the crime data | 9 | 132 (8) | 10 | 138 | 0 | 316 |
| Stat: rent | 23 | 134 (9) | 10 | 138 | 1 / 461 | 793 |
| Stat: everyday prices | 20 | 134 (9) | 10 | 138 | 1 / 234 | 563 |
| Stat: political lean | 17 | 134 (9) | 10 | 138 | 1 / 357 | 683 |
| Stat: places to go out | 22 | 134 (9) | 10 | 138 | 1 / 802 | 1,133 |
| Privacy / Terms / 404 | 9 / 11 / 4 | 132 (8) | 10 | 138 | 0 | 315 / 317 / 311 |

`/api/rank`, the default search: 1,476,577 bytes raw (`next start` doesn't compress
route handlers), 227,322 at gzip level 6 (`rank_bytes.json`). Live: 1,503,429 raw on the wire. Home HTML raw:
1,961,338 bytes (1.9 MB is the rank response with every variant, ADR 0018), 297 KB
gzipped. The ranked cities' photographs (193 files): median 644 KB, largest 3,110 KB
(Dallas), 126 MB in all. Narrowest: Hickory, 576×432.

### Speed (median of 5 cold runs)

| | TTFB | FCP | LCP (element) | CLS | Weight change → list settled |
|---|---|---|---|---|---|
| 1440, unthrottled | 411 ms | 612 ms | **612 ms** (H1) | 0 | **443 ms** (pending line at 195 ms) |
| 390, 150 ms RTT, 1.6 Mbps, 4× CPU | 714 ms | 1,488 ms | **11,460 ms** (card #1 photo) | 0.032 (the hero subhead, at 4.1–4.3 s; likely the web-font swap) | **7,857 ms** (pending line at 226 ms) |
| 390, same, gzip stand-in for commit A | 724 ms | 1,540 ms | 11,468 ms | 0.032 | **1,880 ms** |
| 390, same, gzip + 720px WebP photos | — | — | **1,976 ms** | — | — |

Sources: `m2_speed_local.json`, `m2_speed_gzip.json`, `m2b_image_sim.json`. Low Power
Mode doesn't apply (Linux); the CPU slowdown is Chrome's, on 2 cores.

### Where the #1 result sits (home, default search; `m10_geometry.json`)

| Width × height | #1 top | #1 score bottom | Row height 4–10 | Page height |
|---|---|---|---|---|
| 1440×900 | 514 | 762 | 81 | 2,155 |
| 1280×720 | 514 | **762 (fold 720)** | 81 | 2,155 |
| 1120×800 | 514 | 746 | 81 | 2,159 |
| 1119×800 | 514 | 812 | 81 | 2,251 |
| 1024×768 | 514 | **792 (fold 768)** | 81 | 2,231 |
| 768×1024 | 568 | 793 | 81 and 111 | 2,362 |
| 390×844 | 656 | **927 (fold 844)** | 133 | 3,768 |
| 320×640 | 714 | **950 (fold 640)** | 151–181 | 4,065 |

### Accessibility

- **axe-core 4.13** (default rules: WCAG 2.0/2.1/2.2 A and AA plus best practice) on
  every page at 1440 and 390, plus 11 home states (row open, ⓘ open, age popover, rail
  or sheet with both groups open, slider ⓘ, find in results, header search, menu,
  narrowed, empty, same-sex) at both widths: **0 violations**. Experimental rules: one,
  `label-content-name-mismatch` on the age token (home, permalink). Needs review:
  `color-contrast` on 26 states (text over the track or overlays; checked by hand,
  below), `aria-valid-attr-value` on the empty state and `duplicate-id-aria` on the
  phone header search (`m3_axe.json`).
- **Text under 12px:** none, on any page or state, at 390, 768, 1024, 1119 or 1440
  (`m4_sizes.json`).
- **Contrast where used:** no text below its AA threshold. The only hits are "median
  43" against `--sunken` (4.39:1); they are false positives, because the label is
  positioned below the track and actually sits on white (`--ink-3` on white is
  5.13:1).
- **Control boundaries under 3:1:** the stat pages' unselected sort buttons (`--rule`
  on paper, 1.23:1, with no fill difference).
- **Targets under 44×44 below 1120**, per page at 390 (the same at 768, 1024 and
  1119), excluding links inside running text:

  | Page | Under 44×44 |
  |---|---|
  | Home | brand (163×26); 3 card names (25 tall); 7 row names (20); "Terms" (38×44) |
  | Home, age popover open | the two age thumbs (20 tall) |
  | Home, sheet open | the weight slider (20 tall) |
  | City | brand; 8 "See all cities by …" links (18–36 tall); "Terms" |
  | Compare pair | brand; 2 city links (21); "Terms" |
  | What we measure | brand; 9 links (20) |
  | Stat pages | brand; 177–193 city links (19 tall); the source link (33) |
  | How it works | brand; 10 source links in the data table (17–40 tall); the credit lists' links (15–36 tall, 712 of them, when the lists are open); the 2 `summary` toggles (20) |
  | Terms | brand; "Terms" |

- **Keyboard** (`m5_keyboard.json`):
  - The tab order at 1440 and 390 follows the page. A ring shows on every stop.
  - At 390, focus is hidden under the sticky bar on 4 of 36 stops.
  - The sheet: focus moves to Close, is trapped, and Escape closes it and returns to
    the bar.
  - Info boxes: they open on focus; Escape closes and keeps focus on the button;
    Enter reopens; an outside click closes; tabbing away closes. (From
    `components/info-tip.tsx` and a re-test by hand; `m5_keyboard.json`'s box detector
    looked for the wrong role and records `open: null`.)
  - Age popover: focus moves to the first thumb; arrows change it; Escape closes and
    returns; an outside click closes.
  - Phone menu: Escape doesn't close it.
  - Header search: Escape twice returns to the search button.
- **Reflow and motion** (`m6_reflow_motion.json`):
  - At 320 and at 200% zoom (720×450 CSS), no page scrolls sideways.
  - At 200%, the drawer is 420 wide with its body scrolling
    (`screens/home-1440z200-drawer.png`).
  - With reduced motion: 0 transitions and 0 animations through a weight change, a
    row opening and a photo hover, and none when the sheet opens.
  - Without it, the progress line, the FLIP moves (200 ms) and the card photo's 300 ms
    zoom.
- **Screen reader (accessibility tree)** (`m7_aria.txt`):
  - Landmarks and headings are sound.
  - Rows read "Ranked 4: Los Angeles, CA, link · Biggest pluses… · 783,728 single men
    · 74". The bare score is F26.
  - Compare is a real table with row and column headers.
- **Live site** (`live_site.txt`):
  - HTML and JS are gzipped by Next; `/api/rank` is not compressed.
  - Photographs: `Cache-Control: public, max-age=0`.
  - Static chunks: `max-age=31536000, immutable`.

---

## 7. The photographs

All 193 ranked cities, each as the card crop (16:10, with the medallion where it sits)
and the band crop (16:7), are in `screens/photos/sheet-01.jpg` … `sheet-10.jpg` (rank
order). The closer looks are in `screens/photos/crop-checks.jpg`. File sizes and
pixels are in `measure/photos/photo_files.json`.

**Crops that lose the subject:**

| City (rank) | What goes wrong | Fix |
|---|---|---|
| Rochester, NY (#34) | The band keeps the buildings and the lip of High Falls; the falls themselves are cut. | `object-position: 50% 85%` on the band |
| Lafayette, LA (#127) | The band cuts the cathedral tower's top. It is also on the permission list. | `50% 10%`, or the replacement you choose |
| Laredo, TX (#152) | The band clips the spire's tip. | `50% 15%` |
| Fargo, ND (#56) | The band shows "ARGO" of the vertical FARGO sign. | `50% 20%` |
| Visalia, CA (#190) | The band cuts the Fox sign; it is also 1,280×640 and at dusk. | `50% 30%`; a daylight replacement |

**Don't read as the place** (beyond PHASE5 §7's list):

| City (rank) | What it shows |
|---|---|
| Palm Bay, FL (#78) | Mostly sky, a palm and a strip of water; nothing of the city |
| Reading, PA (#168) | A dark, hazy aerial; no landmark |
| Davenport, IA (#90) | A thin skyline under 60% sky |
| Bridgeport, CT (#40) | A generic aerial with a power-plant stack |
| Cape Coral, FL (#114) | A palm-lined road (Fort Myers); interchangeable with any Florida town |
| Toledo, OH (#59) | A bridge behind a tree; the city is a strip at the horizon |
| Spartanburg, SC (#191) | One storefront building |
| Wilmington, NC (#73) | The riverfront as a thin band |
| New Orleans, LA (#21) | A French Quarter street where parked cars, a blue minivan foremost, fill the foreground |
| Rockford, IL (#161) | A hazy view over a road bridge |

**Subjects to check against the rules:**

- **Los Angeles (#4)**, a top-three card in the same-sex and several other searches,
  is the Hollywood Sign. The sign's name and likeness are registered trademarks, and
  their holder licenses commercial use of its image. Worth a check under the ADR 0012 subject rules
  before deploy; Griffith Observatory or the downtown skyline avoids the question.
- **Amarillo (#120)** is the Fisk Building with a "COURTYARD Marriott" sign at the top
  (the Commons title is "Marriott Courtyard Downtown Amarillo"). A hotel brand as the
  city's face.

**Resolution and alt text:**

- **Hickory (#183)** is 576×432, stretched 1.8× in the 1,056px band. Its alt is the
  Commons description ("Hickory, North Carolina. Union Square is the center of
  Hickory. This photo from the spring of 2002 looks NW to Smith Drugs, Hickory Wine
  Shoppe, and the Mirac…").
- **Kalamazoo (#125)**'s alt is also a raw description ("Looking southwest from N.
  Edwards Street… Round-topped towers are the Radisson Plaza hotel.").
- **Reno (#105)** is 900×600, stretched 1.2× in the band.

**Weight:** Dallas 3.1 MB, Portland 2.2 MB, San Diego 1.7 MB, Greenville 1.6 MB. At card
size the three measured became 37–76 KB (F03); expect the same order for the rest.

**How they sit with the almanac direction.** The paper, the type and the white cards
carry the photos well. The cards read as a publication's lead images, not a travel
site's, because the medallion and the numbers sit under the photo, not over it. Two
things work against it:

- On phones the photo takes 178 of the card's 362px and pushes the figures below the
  fold (F15).
- Mixed light (dusk, overcast, saturated noon) makes the three cards feel unrelated
  side by side.

A consistent treatment would help, with no recrop: the same `object-position`
discipline, and a 4% `--paper` overlay to settle saturated skies.

---

## 8. Copy drafts (all DRAFT, for your approval)

Registry keys are in `atlas/pipeline/registry/features.yaml` under `strings:` unless
noted. "New" means a new key. No banned word appears below; nothing touches political
lean.

| Key | Old | New (DRAFT) | Finding |
|---|---|---|---|
| `same_sex_pool_note` (new) | — | "On a same-sex search, matches count every single {sought} in these ages. The Census doesn't ask who people date, so only some of them are looking for {sought}." | F01 |
| `balance_caption_same_sex` (new) | — (`balance_same_sex` was retired in 4c) | "Balance compares all single men with all single women in the ages you picked. On a same-sex search it describes the city, not your matches." | F01 |
| `pool_short_unit` | "single {sought} match" | "matches" | F21 (the open §7 item) |
| `features.pool_size.unit` (the city score card's line) | "people match what you're looking for" | "matches" | F21 |
| `compare_edge_by` (new) | (A−B under the winner: "−31,802") | "by {diff}" (absolute value; rent "by $339"; spot "by {n} places") | F07 |
| `compare_edge_note` | "Edge shows which city does better on each measure for your search; a dash means we don't judge it." | "Edge names the city that does better on each measure for your search, and by how much. A dash means we don't judge that measure." | F07 |
| `compare_default_note` | "These figures use the stated default search — {search}. Change anything on the home page and they become yours." | "This comparison uses the site's starting search: {search}. Set your own on the home page and it follows you here." | F23 |
| `compare_not_ranked` (new; replaces hard-coded "Not covered") | "Not covered" | "Not ranked: under 250,000 people" | F24 |
| `city_below_floor` (new; replaces hard-coded sentence in `city/[slug]/page.tsx`) | "{city} sits below the population floor this site ranks, so it never appears in results — its profile is below." | "{city} has fewer than 250,000 people, so it isn't ranked; the site ranks metro areas of 250,000 or more. Its profile is below." | F24 |
| `results_new_top` (new) | — | "New top three: {a}, {b}, {c}" | F05 |
| `results_updated` change phrases (in code) | — | "your race or ethnicity", "your education" | F13 |
| `sheet_search_summary` (new) | — | "{you}, {age} · {sought} {ages} — Change" (e.g. "Woman, 30 · Men 28–40 — Change") | F19 |
| `sought_flipped` (new, live region) | — | "Looking for changed to {sought}" | F20 |
| `balance_info_label` (new; today `balance_label` "Balance" names the ⓘ) | "Balance" | "About balance" | F26 |
| `moved_info_label` (new; today the heading names the ⓘ) | "What moved the score (points)" | "About these points" | F26 |
| `crime_card_info` | "About this figure" | "About the {stat} figure" ("About the violent crime figure") | F26 |
| `score_label_sr` (new, sr-only) | — | "Overall score {n} out of 100" | F26 |
| `explainer_lifestyle` | "Lifestyle: four things you weight — cost of living, social life, student life and weather." | "Lifestyle: four things you weight: cost of living, social life, student life and weather." (renders "Four things you weight…" under its heading) | F34 |
| `excluded_count` (`model/suppression.py`, `POLICY_STRINGS`) | "{n} cities don't have enough people matching this search to make a reliable estimate. Widen your search to see more cities." | "{n} metro areas don't have enough people matching this search for a reliable estimate. Widen your search to see more of them." | F34 |
| describeSearch marital phrase (code, chips) | "men 28–40, never married or divorced or widowed" | "single men 28–40 (never married, divorced or widowed)" | F34 |
| Students `chip_label` (`features.students_per_1k_adults`) | "Students" | "Student life" | F21 |
| Card `moved` bar label for cost (code, from `chip_label`) | "Cost of living" | "Cost of living · rent" / "· everyday prices" (the chip's word) | F21 |
| `sharpen_info` (new; reopens Phase 4b) | — | "Optional. These change the compatibility figure only. They stay on this device: the site sends the figures for every combination, and your browser shows yours. How we handle your details →" | F10b |
| Photo manifest field `place_caption` (new, 12 cities) | — (alt only) | "Daytona Beach, in the Deltona metro area"; likewise Fort Myers (Cape Coral), Destin (Crestview), Biloxi (Gulfport), Belton (Killeen), Bristol (Kingsport), Poughkeepsie (Kiryas Joel), Siesta Key (North Port), Silver Springs (Ocala), Pensacola Beach (Pensacola), vineyards outside Santa Maria (Santa Maria), Notre Dame (South Bend) | F29 |
| Permalink `title` (code, `/r/…` metadata) | "Dating Stats Atlas" | "{results heading} · Dating Stats Atlas" | F31 |
| `docs/privacy.md`, "Your search", 2nd paragraph | "Your own browser will keep details about you so the site remembers them for the next time you visit." | "Your own sex, education and race or ethnicity never leave your browser. Our server sends the figures for every combination of them, and your browser shows the one that fits you, so we never learn which one that is. Your browser keeps them so the site remembers them next time you visit." | F10a |
| `docs/methodology.md` lines 47–52 | "The compatibility score is built from real couples… how often each age gap, education pairing, and racial/ethnic pairing actually occurs… so the score says how closely…" | The registry's `match_how` text as it stands ("The compatibility figure is built from real couples… and their race or ethnicity only if you include yours… so the figure says how closely…") | F11 |
| `unit_line` / `display` for who_lives_here (API) | "200,000" · "people, of whom 100,000 are adults" | "180,000" · "people, of whom {adults, 2 significant figures} are adults" (both to 2 significant figures) | F09 (needs the model) |

The image `alt` for Hickory and Kalamazoo needs writing after you pick (§7).

---

## 9. Open questions for you

1. **Same-sex matches (F01).** Do you want the note now, and should the model later
   estimate a same-sex share? Which wording do you prefer?
2. **The cautions (F08).** Were the flag chips removed on purpose on 17 September? If
   not, may they come back as one caption line?
3. **Privacy at the point of asking (F10b).** Will you allow an ⓘ beside "Optional",
   given your Phase 4b call against inline notes? The Privacy-page sentence (F10a)
   doesn't need it.
4. **Chips (F12).** Show lifestyle movers only, served by the model?
5. **Margins (F14).** Show the served margin on the city page, reopening ADR 0004, or
   leave matches as they are?
6. **Los Angeles's photo.** Keep the Hollywood Sign, or switch to a view that raises no
   trademark question?
7. **Deploy order.** May commit A (compression) go out ahead of the rest of Phase 5?
   It changes no page.
8. **Phone rows.** Shorten "… single men match" to "matches" (my vote: yes, F21)?

Which of the findings do you want built? The implementation brief
(`atlas/PHASE6_PROMPT.md`) waits for your answer.
