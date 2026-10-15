# Phase 8 — the round-4 review's remaining findings, built

## 1. In plain words

Everything on the 15 October list is built, on a branch. **Nothing new is pushed or deployed.**
Only `ec5bd0c`, which you approved, went to GitHub.

- **Photo descriptions.** 78 city photos now have a real description for screen readers.
  Indianapolis's said "indianapolis", Columbia's was a credit line, and ten quoted population
  figures the site never computed. Twelve were cut off mid-word. These are drafts for you (§3a).
- **Wording moved out of the code.** 64 bits of text that lived in the code now live in the
  registry, with the rest of the site's words. One line changes on screen, and it's your call:
  the city card says "9 of 193 metro areas" instead of "of 193 cities" (§3b).
- **Screen readers hear "Balance", then "About balance"**, not "Balance About balance".
- **Faster first visits.**
  - The heading font is trimmed to the weights the site uses. It looks the same at 58 KB
    instead of 121 KB, so every page is about 60 KB lighter.
  - The site's starting search is now kept ready on the server. It's the same for everyone and
    says nothing about any visitor, so this keeps no record of anyone. Locally the home page
    starts arriving in half the time; on the server it should save about a third of a second.
  - Phones with very sharp screens get the same photo size as other phones. The phone home
    page's photos drop from 318 KB to 152 KB, against the 250 KB target.
  - On a simulated slow phone, the home page's main photo appears in 1.3 s instead of 2.4 s
    (locally).
  - The review suggested sending the home page in pieces. I built it: the desktop headline
    appeared sooner, but phones got slower (2.4 s to 4.5 s), so it isn't in.
- **Link previews.** The site uses one description everywhere (the home page's subtitle). A
  missing page's tab says "Page not found", and a Compare link shows the first city's photo.
- **The original photos can't be downloaded any more.** It turned out wide, sharp screens were
  loading those originals (up to 4 MB) on city pages; they now get a full-width WebP copy.
- **Fixed in passing:** the server told browsers to keep stat pages for a week, so after a
  deploy a returning visitor could see an old one.
- **Even phone rows.** Tags now run under the score too. At 390px, 174 of 190 rows are one
  height; before, 59 were.
- **City pages show "What moved the score"**, folded away until clicked.
- **Photos.** Charleston (Rainbow Row without the cars), York (the Central Market House) and
  Reno (a sharp skyline) are replaced, Fargo's banner now reads the whole "FARGO", and Peoria
  stays, as nothing was clearly better. These are yours to approve (§3c).

No score, rank, pool, balance, compatibility figure, band or suppression moved (518 of 518 test
searches identical). The model stays **m4.3.0** on build **d62202fd0280**. Branch
`claude/phase8` off `main` at `ec5bd0c`, unpushed.

## 2. The commits

| | Commit | What changed |
|---|---|---|
| **R** | `d05741f` | Baseline at `ec5bd0c` in `results/phase8/before/`: page weights at 1440 and 390, speed locally and live, #1's position and the rows' heights. |
| **A** | `adbe87b` | **R13:** 50 photo descriptions (drafts). **R15:** 64 strings move from the web code to the registry (`features.yaml`), verbatim but for `city_rank_of` (draft); the header's, footer's and old-link pages' words travel in the chrome block; a unit test fails if a component or page writes visible text of its own. **R16:** the ⓘ sits beside the Balance heading, not inside it. Build manifest refreshed (same id); served numbers 518/518 identical. |
| **B** | `9e92b81` | **R18:** Fraunces trimmed (SOFT 30, weights 600–700, every optical size) and loaded with `next/font/local`, with the stand-in font Google's carried. **R23:** the starting search kept once per build and model on the server; streaming built, measured and dropped (`results/phase8/b/`). A 3x phone gets the 720px photos. |
| **C** | `aa6f221` | **R17:** one description, the 404's title (also on unknown city, compare and stat addresses), Compare's preview image. **R19:** a WebP copy at each photograph's own width, pages name only copies, Caddy answers 404 for originals; the week-long cache now matches image files only. **R21:** phone rows. **R22:** the city card's disclosure. `docs/deploy.md`: every copy must be on the VM before the swap. |
| **D** | `59832a3` | **R20:** Charleston, York and Reno replaced, pinned by their bytes; Fargo's focal point; Peoria kept. ADR 0012 amendment (draft). Screens in `results/phase8/screens/`. |
| **A, follow-up** | `100883b` | **R13:** 28 more descriptions of the kinds A meant to fix, found while checking spelling; the manifest test now refuses credits, signatures, notes, figures and text cut off at 160 characters. |
| report | (this commit) | `PHASE8.md`, `results/phase8/after/`, `string_changes.json`. |

## 3. For your approval

**a. The photo descriptions.** 78 rewritten, each after looking at the photo, naming a building
or place only where the photo's own source (its Commons title or description) names it. The old
text of each is kept in `results/phase4/photo_review.json` (`alt_overrides`, "was").

| City | What it said before | New description (draft) |
|---|---|---|
| Abilene, Texas | "image", announced as nothing | Downtown Abilene's brick and stone towers rising above a line of green trees under a deep blue sky. |
| Altoona, Pennsylvania | a population figure the site did not compute, cut off mid-word | Altoona from above, rows of houses and brick buildings spreading toward a domed church and a white high-rise, with long green ridges and low clouds beyond. |
| Anniston, Alabama | "This is a photo of downtown Anniston, Alabama." | A wide street in downtown Anniston lined with brick storefronts, green awnings and street lamps, under a partly cloudy sky. |
| Appleton, Wisconsin | not a description ("This was taken from the fox river in 2015.") | Old stone and brick mill buildings along the Fox River in Appleton, seen across the water through leafy branches. |
| Auburn, Alabama | a garbled sentence | Auburn City Hall, a red-brick building with tall arched windows and a stone entrance, behind bare trees and a street lamp under a blue sky. |
| Beckley, West Virginia | a population figure the site did not compute | Downtown Beckley from the air, low brick and tan buildings and parking lots among trees turning in autumn, with wooded hills stretching to the horizon. |
| Bellingham, Washington | a population figure the site did not compute | Downtown Bellingham from the air, its red-brick towered old city hall among trees, with forested hills under a summer sky. |
| Bismarck, North Dakota | a population figure the site did not compute | Downtown Bismarck from the air, a grid of low buildings and streets spreading across flat land, with the North Dakota State Capitol's tower on the horizon. |
| Bloomington, Indiana | a web address | Kirkwood Avenue in Bloomington at sunset, a street of shops and restaurants under a golden sky. |
| Bozeman, Montana | the wrong town ("Springfield, Montana") | Main Street in downtown Bozeman, a row of brick buildings and shade trees on a sunny day. |
| Casper, Wyoming | a file name and a crop note | Downtown Casper beside the North Platte River, with the broad slopes of Casper Mountain rising behind the city. |
| Chambersburg, Pennsylvania | empty | Memorial Square in Chambersburg, with a tiered iron fountain and a brick courthouse's white clock cupola on a summer day. |
| Charleston, West Virginia | cut off mid-word at 160 characters | The West Virginia State Capitol in Charleston, its gilded dome above a columned portico and a statue at the top of wide stone steps, between autumn trees. |
| Charlottesville, Virginia | a population figure the site did not compute | Downtown Charlottesville from the air, brick buildings among dense trees with green mountains beyond. |
| Columbia, Missouri | a credit line ("This picture was created by User: …") | Six stone columns standing on a lawn before Jesse Hall's white dome at the University of Missouri in Columbia, under a cloudy sky. |
| Columbus, Indiana | cut off mid-word at 160 characters | The Robert N. Stewart Bridge across the Flatrock River into Columbus, its red A-shaped pylon and fanned white cables framing the road into town. |
| Columbus, Ohio | an edit note ("(Edited version)") | Downtown Columbus's towers above a river and a low arched bridge, seen from the Main Street Bridge under a partly cloudy sky. |
| Decatur, Illinois | "Downtown Decatur" | Downtown Decatur's brick storefronts and a tall historic tower at dusk, seen from above a lit street corner. |
| Detroit, Michigan | an encyclopedia caption, cut off mid-sentence | Detroit's skyline across the Detroit River from Windsor, Ontario, on a sunny day, a cluster of dark glass towers on the riverfront among downtown's high-rises. |
| Dothan, Alabama | a date in brackets | Downtown Dothan's rooftops under a clear sky, a cream-colored tower with a white dome on a lattice mast beside a dark-ribbed office block. |
| Dover, Delaware | wiki markup ("w:Dover") | West Loockerman Street in downtown Dover, with storefronts and bare trees in early spring. |
| Dubuque, Iowa | the place's name only | Downtown Dubuque's brick buildings and church spires seen over treetops from a bluff, with green hills beyond. |
| Eagle Pass, Texas | a talk-page signature and a date | A white welcome sign reading “Bienvenidos, Eagle Pass, Texas” with a Texas-shaped emblem, planted with agaves and shrubs beneath green trees. |
| El Centro, California | empty | The Imperial County courthouse in El Centro, its columned front lit up at dusk beside a palm trunk. |
| Elizabethtown, Kentucky | cut off mid-sentence at 160 characters | The Hardin County Courthouse on Courthouse Square in Elizabethtown, a red-brick building with a columned entrance and a flagpole, on a sunny day. |
| Fayetteville, North Carolina | "Fayetteville, NC Downtown Skyline" | Downtown Fayetteville from above, with church steeples, brick buildings and tree-lined streets on a clear day. |
| Fond du Lac, Wisconsin | wiki markup ("w:") and a copied heritage-listing notice | Main Street in downtown Fond du Lac, a broad street of historic brick buildings under leafy trees on a sunny day. |
| Gadsden, Alabama | a file name, announced as nothing | Gadsden from the air, its downtown grid beside the curving Coosa River among wooded hills. |
| Gainesville, Georgia | the place's name only | A red-brick building with a white domed cupola in downtown Gainesville, framed by tree branches against a blue sky. |
| Gettysburg, Pennsylvania | a caption followed by a copied heritage-listing notice | Devil's Den on the Gettysburg battlefield seen from Little Round Top, with boulders and green grass under a broad sky. |
| Grand Forks, North Dakota | an agency caption with a date, cut off mid-sentence | Downtown Grand Forks from the air, its brick blocks beside a river crossed by an arched steel bridge, with green parkland and leafy neighborhoods around. |
| Grand Island, Nebraska | cut off mid-word at 160 characters | The Hall County Courthouse in Grand Island, a brick and stone building with a green copper clock tower and a wide stone stair, under a blue sky. |
| Grand Junction, Colorado | "Grand Junction, Colorado skyline" | Grand Junction spread across the valley floor beyond dry hills, with a long range of hills on the horizon under clouds. |
| Great Falls, Montana | cut off at 160 characters | Central Avenue in downtown Great Falls, looking west past brick shops and an office tower toward the civic center, on a bright winter day. |
| Greenville, North Carolina | the place's name only | A downtown Greenville street seen from above at sunset, cars passing between brick buildings under a fiery orange sky. |
| Hanford, California | the place's name only | Hanford's civic auditorium, its tall columns and pale front facing a lawn under a deep blue sky. |
| Hattiesburg, Mississippi | a population figure the site did not compute | Downtown Hattiesburg from the air, its brick and stone buildings beside a railway line under an overcast sky. |
| Helena, Montana | a garbled caption with a year | The Montana State Capitol in Helena, its domed stone front behind a bronze statue of a rider on a rearing horse and beds of red flowers. |
| Hot Springs, Arkansas | a list of file names | A collage of Hot Springs: the town among wooded hills from above, a domed bathhouse's arcade, the brick Army and Navy Hospital tower, a hot spring pooling among rocks, and a street of old hotels lit at night. |
| Indianapolis, Indiana | the city's name in lower case | Downtown Indianapolis from above on a clear day, its twin-spired tallest tower at the center and an arena's arched roof in the foreground. |
| Iowa City, Iowa | "Picture of …" and a date | South Clinton Street in downtown Iowa City, brick storefronts and a tall brick building along a sunny street with parked cars. |
| Johnson City, Tennessee | "This is a photo of …" | Downtown Johnson City's brick buildings and a white steeple among green trees, with Buffalo Mountain rising beyond under billowing white clouds. |
| Jonesboro, Arkansas | "Collage of Jonesboro, AR" | A collage of Jonesboro: a tall clock tower, a brick civic building with a statue in front, a red-brick house with a porch, and a downtown street of shopfronts. |
| Kahului, Hawaii | a caption with an uploader's note | Kahului from the air, its low buildings and harbor along the blue Pacific coast of Maui. |
| La Crosse, Wisconsin | "La Crosse Main Street" | Main Street in downtown La Crosse, with red-brick storefronts, a sidewalk clock and people crossing on a summer day. |
| Lawton, Oklahoma | "Picture of the Old Lawton High School Building" | The old Lawton High School, a red-brick building with white columns and a copper dome, behind shade trees on a sunny day. |
| Lebanon, Pennsylvania | "Cumberland Street View Image" | Cumberland Street in downtown Lebanon from above, cars passing brick buildings and a glass-fronted corner building. |
| Macon, Georgia | a file name, announced as nothing | Macon from high above, its downtown streets and highways spread across wooded country in a blue haze. |
| Mankato, Minnesota | wiki markup ("en:") | Brick storefronts of the North Riverfront Drive Commercial District in Mankato on a sunny day. |
| Mansfield, Ohio | the place's name only | Mansfield's skyline above a band of green trees: a tall red-brick tower, two white high-rises and church spires on the left. |
| Midland, Texas | a population figure the site did not compute | Downtown Midland's office towers rising from flat, open country, seen from the air beside a highway under a clear blue sky. |
| Minot, North Dakota | the place's name only | Downtown Minot's low brick buildings and a few taller blocks beyond tall grass and shrubs under a clear sky. |
| Monroe, Michigan | "Monroe Skyline" | Downtown Monroe's brick buildings and a low arched bridge across the River Raisin under a big cloudy sky. |
| Montgomery, Alabama | a library catalogue record | Downtown Montgomery from the air, with the riverboat landing and the long train shed on the Alabama River in the foreground. |
| Morgantown, West Virginia | two words ("Woodburn Hall") | Woodburn Hall in Morgantown, a red-brick building with a clock tower and mansard roofs, framed by green trees. |
| Mount Vernon, Washington | a population figure the site did not compute | Downtown Mount Vernon from the air beside the Skagit River and a bridge, with green mountains under clouds beyond. |
| Oshkosh, Wisconsin | a crop note ("Cropped from the original.") | Main Street in downtown Oshkosh at dusk, brick storefronts and lit signs around a wide intersection, with wreaths on the lampposts. |
| Pittsfield, Massachusetts | a population figure the site did not compute | Downtown Pittsfield from the air, brick buildings among dense trees with the green Berkshire hills beyond. |
| Pueblo, Colorado | a population figure the site did not compute | Downtown Pueblo from the air, its brick buildings and the Riverwalk's channel spread out under a clear sky. |
| Rochester, Minnesota | two words run together ("Peace PlazaDowntown") | Peace Plaza in downtown Rochester, a brick square with lamps and trees surrounded by glass and stone towers. |
| Saginaw, Michigan | "Saginaw from the River" | Saginaw's downtown towers and a bridge seen across the calm Saginaw River on a clear evening. |
| Sandusky, Ohio | a misspelling ("Ariel view") | Downtown Sandusky from the air at sunset, its marina and waterfront on Sandusky Bay below a streaked sky. |
| Sebastian, Florida | "Sebastian, Florida: City hall" with stray line breaks | Sebastian's city hall, a cream building with a red tile roof and an arched porch, among palm trees under a clear blue sky. |
| Sioux City, Iowa | cut off mid-word at 160 characters | The Woodbury County Courthouse in Sioux City, a tan-brick Prairie-style building with a tall tower, under a cloud-streaked sky. |
| Springfield, Illinois | cut off mid-word at 160 characters | The Dana–Thomas House in Springfield, a Prairie-style house by Frank Lloyd Wright with wide copper-trimmed eaves and tan brick walls, under a blue sky. |
| Springfield, Ohio | the place's name only | Red-brick buildings on a corner of downtown Springfield in late-afternoon sun, with people walking beneath leafy trees. |
| St. Cloud, Minnesota | a caption followed by a copied heritage-listing notice | The brick and stone storefronts of St. Germain Street's 800 block in downtown St. Cloud on a sunny day. |
| St. George, Utah | the place's name only, in capitals | St. George's houses spread across the valley below red cliffs, with snow-dusted mountains under a clouded sky beyond. |
| St. Joseph, Missouri | wiki markup ("w:Buchanan County") | The Buchanan County Courthouse in downtown St. Joseph, a red-brick building with white columns and a silver dome. |
| Sumter, South Carolina | "Downtown Sumter" | A tree-lined brick street in downtown Sumter, with a red awning and flower planters in summer. |
| Victoria, Texas | "Skyline" | A broad street in Victoria leading toward a tall office building, with traffic and trees in late-afternoon light. |
| Vineland, New Jersey | a remark ("Nice old downtown buildings") | Landis Avenue in downtown Vineland, a row of colorful two-story storefronts beside a gray stone Gothic church, under a clear blue sky. |
| Waterloo, Iowa | the place's name only | Downtown Waterloo's brick buildings along the Cedar River, its surface patched with ice, behind a low bridge. |
| Watertown, New York | the place's name only | Public Square in Watertown on a spring day, with a stone obelisk, benches and young trees in leaf beside the street. |
| Weirton, West Virginia | a remark about vacant storefronts, cut off mid-word | Main Street in downtown Weirton, a row of brick storefronts with awnings and signs along a quiet street under an overcast sky. |
| Wenatchee, Washington | the place's name only | Wenatchee among green trees in its river valley, with brown foothills and snow-capped mountains behind. |
| Winston-Salem, North Carolina | cut off at 160 characters | Downtown Winston-Salem's towers, among them the Reynolds Building and Winston Tower, behind the redeveloped Bailey Power Plant and its tall brick smokestacks, under an overcast sky. |
| Yuba City, California | "Downtown Yuba City" | A sunny sidewalk in downtown Yuba City, with shopfronts, a palm tree and a water tower behind. |

And the three new photographs' (§3c):

| City | New description (draft) |
|---|---|
| Charleston, South Carolina | Rainbow Row in Charleston: a pink three-story house with black shutters and a small iron balcony, then lavender and green houses among palmetto trees, under a blue sky. |
| York, Pennsylvania | York's Central Market House, a red-brick market hall with two slate-roofed towers, a central gable and green arched doors, under a cloud-streaked sky. |
| Reno, Nevada | Downtown Reno's casino and hotel towers above a broad canopy of green trees, with brown hills and mountains behind. |

**b. The city card's rank line.** "9 of 193 metro areas" (my draft), where it says "of 193
cities" today, under a home page that counts "193 metro areas". The review drafted "of {n}
ranked", but a screen reader would then hear "Ranked 9 of 193 ranked", so I used the home
page's words. The registry key is `city_rank_of`: to keep today's words, set it to "of {n}
cities"; for the review's, "of {n} ranked".

**c. The photographs** (`results/phase8/card_photos.json`, screens in `results/phase8/screens/`):

- **Charleston:** *Rainbow Row, South of Broad, Charleston, SC (49477988853)* by Warren LeMay,
  **CC0**, a clear October sky. Every view of Rainbow Row has cars at the curb; at its focal
  point (50% 15%) the band and the link preview show none, and the card the top of one.
  *Alternative:* keep today's photo with its focal point moved up (50% 10%): the band loses the
  cars, the card keeps them, and the sky stays grey.
- **York:** *York Central Market House PA1* by Acroterion, **CC BY-SA 4.0**, 5540px (today's is
  1024px, upscaled in the band). Focal point 50% 20%, so the cars at its curb stay out of the
  band and the preview. *Alternative:* *York Pennsylvania -002* (CC BY-SA 3.0, 2668px), a
  blossoming street like today's, busier.
- **Reno:** *View of Reno, Nevada from Juniper Ridge (20720895303)* by Ken Lund, **CC BY-SA
  2.0**, 4000px (today's golden-hour skyline is 900px). The same kind of view, in daylight and a
  little hazy. *Alternative:* *Reno from ArrowCreek 5* (CC BY-SA 3.0, 2000px), under snowy
  mountains, with the towers a thin strip in the band.
- **Fargo:** the same photo, focal point 50% 36% instead of 50% 20%. Checked on the page at
  1440, 1024 and 390: the band shows the whole word.
- **Peoria:** kept. The other skylines show the same bank logo, and the views from the bluffs
  (Grandview Drive) show the river without the city.

All three licences are on the list (as each file's own page states it, read 15 October), so
nothing joins the permission record.

**d. ADR 0012 amendment** (at the end of the file, draft): the three photographs and their
licences, the two focal points, and the originals no longer served (each copy carries the
original's credit and licence, as before).

**e. Choices to confirm** (no new words, but you'd see them):

- **One site description.** About, Privacy, Terms, What we measure, About the crime figures
  and the 404 now carry the home page's subtitle in link previews and search results. The second
  description, "Which city has the best dating scene for you? Estimated from the Census Bureau's
  own survey, city by city.", is gone.
- **Sharp-screen phones get the 720px photos.** Thin lines, such as bridge cables, are a touch
  softer if you look closely; the photos download in half the bytes (§4, §6.4).
- **The desk cards' chevron stays where it is.** The review suggested pinning it in the corner,
  but the three tags need 263px where a card has 218px, so they'd still take two lines.
- **The city card's fold reads "What moved the score (points)"**, the detail's own heading.

## 4. Measurements

This Mac, the local production build (`next start` on :3400 over the API at :8100, build
d62202fd0280), with the review's scripts. Low Power Mode was on for both runs, so these compare
with each other, not with the live site. Before: `results/phase8/before/`. After:
`results/phase8/after/`.

| Measure | Before | After | Target |
|---|---|---|---|
| Home page, first byte (1440 / 390) | 302 / 308 ms | **156 / 165 ms** | — |
| Home page, largest paint (1440) | 376 ms | **232 ms** | — |
| Home page, largest paint (390, throttled phone) | 2,380 ms | **1,272 ms** | ≤ 2,500 |
| First paint (390) / page loaded (390) | 956 / 5,153 ms | 832 / 3,937 ms | — |
| Layout shift (390 / 1440) | 0.0306 / 0 | 0.0306 / 0 | — |
| Home page weight (390) | 931 KB | **707 KB** | — |
| Home page photos (390, 3x) | 318 KB | **152 KB** | ≤ 250 KB |
| Fonts, every page | 138 KB | **77 KB** | — |
| Every page (23, at 1440 and 390) | — | about 60 KB lighter each | — |
| Phone rows at 125px (390 / 430 / 360 / 320) | 59 / 125 / 30 / 18 of 190 | **174 / 190 / 132 / 64** | one height |
| Rows from 640px | — | identical to the live site, row for row | — |
| #1's position, every width | `before/m10_geometry.json` | unchanged | — |
| Original photos named or requested (1440@2x, 390@3x, 2560@2x) | on wide screens, 365 of 368 cities' | **none** | none |
| Stand-in font: size change as Fraunces arrives | as live | as live (same numbers) | — |
| axe violations | 0 | **0** (74 runs) | 0 |

The heading font is not byte-for-byte the old one: at letter edges 1.5–6% of pixels anti-alias
differently, and a line can set up to 0.2% narrower. Side by side the two look the same.

**The streaming that was tried** (`results/phase8/b/`), through a local Caddy compressing as the
VM's does:

| | First byte | Largest paint, 1440 | Largest paint, 390 |
|---|---|---|---|
| Before | 334 ms | 396 ms | 2,396 ms |
| Streamed | 17 ms | 64 ms | **4,480 ms** |

The desktop headline appeared at once, but on a phone the largest paint is #1's photo. Next puts
the page data for every "about you" variant (2.1 MB, ADR 0018) ahead of the streamed results, so
the photo's tag reached the phone after it. Should that payload ever shrink, streaming becomes
worth another look.

**On the server**, the starting search's ranking takes about 315 ms of the home page's
610–840 ms first byte (VM timings from this work). The kept copy should take that off every bare
home, city and compare page, except the first after each restart. That's an estimate until it's
measured after a deploy (§7).

## 5. Tests and gates

| | Result |
|---|---|
| pytest | **211** passed |
| vitest | **165** passed (Phase 8 adds 15, `tests/phase8.test.ts`) |
| Playwright (hermetic fixture) | **322 passed, 0 failed, 6 skipped (the real-build checks)** (Phase 8 adds `e2e/phase8.spec.ts`, 17 tests) |
| axe | 0 violations in 74 runs |
| Served numbers | A: 518/518 `/v1/rank` responses, 1,036 rankings and 387 profiles identical (`served_numbers_commit_a.json`). B, C and D touch no model, API or registry file. |
| Caddyfile | validated with `caddy:2`; originals 404, also by encoded, doubled-slash and dot-segment paths; copies, previews and `/og/home.png` 200 with the week's cache; stat pages without it |
| tsc / eslint | clean (eslint: 0 errors in the source; see §8) |
| Banned vocabulary | none in the added registry and web lines |

**What the new tests pin:**

- **Unit tests:**
  - no component or page writes visible text of its own;
  - every description is free of file names, credits, notes and figures, isn't cut off, and runs
    to at least three words;
  - the starting search is kept once, never another search, and never a failure, and a new
    build asks again;
  - the trimmed font file and its licence;
  - every photo's copies reach its width, and `sized()` names only copies;
  - Caddy's two rules;
  - the photo picks.
- **Browser tests:**
  - the registry's words on the city page, Compare, the home page and a stat page;
  - Balance's heading and its ⓘ;
  - which photo copy each screen takes;
  - one Fraunces file and its stand-in;
  - titles, descriptions and Compare's preview;
  - no original photo named or requested;
  - the phone row's layout;
  - the city card's fold, against the home detail's bars.

**Changed tests, each because the behaviour it pinned changed:**

- `copy-2026-10-10.spec`: the ⓘ sits beside the heading (R16).
- `copy-2026-10-07.spec`, `phase4e.spec` and `phase2e.spec`: they found a photo by its
  original's address and now find it by its copy's (R19).

## 6. Deviations

1. **Streaming (R23's suggestion) is not shipped**, for the phone result in §4. The starting
   search kept on the server does R23's job instead. Only that one search is kept: keeping a
   visitor's own search would be a record of a visit, which the Privacy page says the server
   never keeps. Each page gets its own copy, and a failure is never kept.
2. **The trimmed font isn't pixel-identical** (§4). The icons weren't redrawn from it, since
   the "D" would sit about 1px aside; they stay as approved.
3. **The stand-in font keeps Google's numbers.** `next/font/local` measured its stand-in at the
   trimmed file's new default weight. It came out 5–6% wider than the font, against 3% for the
   old one, and a San Francisco heading re-wrapped when the font arrived. So `globals.css`
   declares the old stand-in, and the jump now matches the live site's.
4. **Sharp-screen phones get the 720px photo copies** (§3e). This trade is how the phone home
   page met its 250 KB target. A 430px-wide 3x phone still takes the 1080px copy, as a 2x phone
   that wide does.
5. **R19 is more than "stop serving originals".** Pages were using the originals: an original
   under 2048px was the widest choice in its photo's set. So each photo gained a WebP copy at
   its own width (`public/cities/w` grows from 153 to 276 MB on disk). An image's `src`, used
   only by browsers without `srcset`, is now the widest copy up to 1080px.
6. **The 404's title also covers** a city, compare pair or stat page whose address names
   nothing, which answer 404 too.
7. **R21 places the phone chevron on the pool's line**, under the score, rather than literally
   inside the score's stack. In that stack it made every row 139px. At the end of the tags' line
   it dropped alone onto a second line in 39 rows. The desk cards are unchanged (§3e).
8. **The phrases `lib/prefs` composes from parts** stay in the code: the search described, the
   panel's summary and the wideners. They're built from registry words and numbers, not written
   out.
9. **The descriptions' follow-up (`100883b`) went past A's list.** It covers the same kinds of
   fault, found while checking spelling: 27 more, then Midland, which the stronger test found.
   The photo pipeline's 160-character cut is left in place. Every description it cut is now
   overridden, and the test would catch a new one.
10. **Two of my drafts used British spelling**: Indianapolis's "centre" and Charleston's
    "three-storey". The site's descriptions are American, so they now read "center" and
    "three-story".
11. **The apply step re-stamped "retrieved"** on 102 pinned rows of `city_images.csv`. Only the
    three changed rows were kept, as in Phase 7. York's 1024px and Reno's 900px copies, now
    unused, were moved out of `public/` (to this session's scratch folder), not deleted.
12. **Measured with Low Power Mode on**, as the baseline was. The VM saving is an estimate (§4).
13. **The served-numbers check ran for A only.** B to D change no model, API or registry file.
    C's `home_subtitle` is an existing registry string that now also travels in the chrome
    block.

## 7. Deploying it

On your word, the usual way (`docs/deploy.md`): a fresh `src_next`, the private staging copy
first, then the swap. Phase 8 adds:

- **The photographs.** Run `rsync -a --checksum --delete` of `cities` and `stats` over the new
  folder.
  - It carries a new full-width copy for every photograph (about 125 MB), the three new
    photographs with their copies and previews, and Fargo's re-cropped preview.
  - It removes York's 1024px and Reno's 900px copies.
  - Before the swap, check that every file `photo-sizes.json` lists is in the new folder (the new
    step 2 note).
- **Caddy is recreated** (`--force-recreate caddy`), since the Caddyfile changed.
- **Then check:**
  - `/cities/austin-texas.jpg` answers 404, and `/cities/w/austin-texas-1080.webp` 200 with the
    week's cache;
  - `/stats/rent_1br` has no week's cache;
  - `/no-such-page`'s title reads "Page not found";
  - the home page's first byte against today's (about 0.3 s less expected, after the first
    request warms it).
- **Rollback** is as before: the old images, the old `src` folder, the same build.

Stat pages that browsers kept under the old week-long rule will refresh within a week at most.

## 8. Found, not done

- Two stat pages' tab titles start lowercase: "walkability by city · Dating Scene Data" and
  "population by city · …". They're like that live today; it's a one-line fix if you want it.
- Some descriptions still carry a year or "(United States)" ("Skyline of Bangor, Maine in
  2025"). They're harmless, so I left them.
- The project's lint setup ignores `.next/` but not the other build folders (`.next-e2e`,
  `.next-p8` …). So `npm run lint` in a working copy that has them reports their files: 1,116
  errors, none in the source.
- The "about … about" city descriptions (known) wait for their next regeneration.
- After a weight change on a slow phone, the list takes about 8 s to update: that's the 1.5 MB
  every-variant response (ADR 0018), unchanged here.
