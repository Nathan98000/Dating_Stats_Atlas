# Measurements for the round-3 review (8 October 2026)

**Phase 6 port (commit R).** These are the review's scripts from
`atlas/docs/design/review-2026-10-08/measure/`, made to run on the Mac from `atlas/web`:
bare imports (`@playwright/test`, `@axe-core/playwright`, `sharp`) resolve from
`atlas/web/node_modules`, Playwright drives its own Chromium (no `executablePath`),
`img_proxy.mjs` reads `atlas/web/public`, and `photo_sheets.py` reads paths relative to
`atlas/web` (the rank order from `RANK_JSON`, else the API's default search). `BASE` is
still an environment variable. Each script writes to the current directory: run it from
the output folder, e.g. `cd atlas/results/phase6/before && node ../../../web/scripts/review/m1_pages.mjs 1440,390`.
The review's own copy, and its original text below, are the record and are unchanged.

All scripts drive a **local production build** at `http://localhost:3300` (`next start`
with `NEXT_DIST_DIR=.next-review`) over the API on build `63c4e5fa51bf`, both started
exactly as `atlas/PHASE6_REVIEW_PROMPT.md` says. They use Playwright from `atlas/web`
(1.63) and `@axe-core/playwright` 4.13. `common.mjs` names the Chromium binary it
used (`EXE`); on a Mac, delete `executablePath` from `launch()` to use Playwright's
own.

Run from this folder with Node 22: `node <script>`. Each writes its JSON here.

| Script | What it measures | Output |
|---|---|---|
| `m1_pages.mjs [widths]` | Every page at 1440, 1280, 1120, 1119, 1024, 768, 390, 320, cold: title, og/twitter tags, sideways scroll, clipped elements, page height, page weight by kind (count, bytes on the wire), every image's natural vs shown size, lazy/priority | `m1_pages.json` (merged), `m1_pages_1440_390.json`, `m1_pages_1280_1120_1119_1024_768_320.json` |
| `m2_speed.mjs [base] [label]` | LCP (element), FCP, TTFB, CLS (with sources), and the delay after "Cost of living: A lot" before the list settles. 5 cold runs at 1440 unthrottled and 390 with Lighthouse's mobile profile (150 ms RTT, 1.6 Mbps down, 750 kbps up, 4× CPU) | `m2_speed_local.json` (as served), `m2_speed_gzip.json` (through `gzip_proxy.mjs`) |
| `gzip_proxy.mjs` | A stand-in for Caddy's `encode` (commit A): port 3301 → 3300, gzipping what arrives uncompressed (`/api/rank`) | — |
| `img_proxy.mjs` + `m2b_image_sim.mjs` | A stand-in for right-sized photos: port 3302 answers `/cities/*.jpg` with a 720px WebP q72 (sharp) over the gzip stand-in; phone LCP measured as in m2 | `m2b_image_sim.json` |
| `m3_axe.mjs` (+ `m3_fix.mjs`, a re-run of three states whose selectors needed fixing) | axe on every page at 1440 and 390 (default rules: WCAG 2.0/2.1/2.2 A/AA + best practice; experimental separately), and 11 home states | `m3_axe.json` |
| `m4_sizes.mjs` + `audit_in_page.js` | At 390, 768, 1024, 1119 (and 1440 for text): targets under 44×44, text under 12px, text contrast against the opaque background actually behind it, control boundaries under 3:1 | `m4_sizes.json`, `m4.log` |
| `m5_keyboard.mjs` | Tab order and visible focus at 1440 and 390, focus hidden under fixed layers, the sheet, info boxes, the age popover, the phone menu and the header search with Escape and an outside click | `m5_keyboard.json`, `m5.log` |
| `m6_reflow_motion.mjs` | Sideways scroll at 320 and at 200% zoom (720×450 at scale 2); transitions and animations with and without reduced motion | `m6_reflow_motion.json` |
| `m7_aria.mjs` | The accessibility tree (Playwright ARIA snapshots) of the header, hero, rail, results header, a card, a row closed and open, the sheet, a city page and a compare table | `m7_aria.txt` |
| `m8_fullpages.mjs` | Full-page screenshots of every page at 1440 and 390 (not shipped; the cited ones are in `../screens/`) | — |
| `m9_pending.mjs` | What a phone shows while a weight change is in flight: the sheet, the page right after "Show results", and when the list lands | `m9_pending.json` |
| `m10_geometry.mjs` | Where the #1 result sits and the row heights at every width | `m10_geometry.json` |
| `who_lives_here.py` | The "Who lives here" card for all 387 metros from `POST /v1/profile`: the value vs its display, and the adult share the two rounded figures imply | `who_lives_here.json` |
| `photo_sheets.py` | Contact sheets of all 193 ranked cities' photos as the card (16:10) and band (16:7) crop them at `object-position: 50% 35%`, with each file's pixels and size | `photos/photo_files.json`; sheets in `../screens/photos/` |
| `rank_bytes.py` | `/api/rank` for the default search: raw, and gzipped at levels 6 and 9 | `rank_bytes.json` |
| `live_site.sh` | What only the server shows on the live site: compression, caching | `live_site.txt` |
| `cold_read_driver.py` | The small persistent Playwright driver used for the cold read and the tasks (`POST` a list of steps to :9333) | — |
| `states.mjs`, `common.mjs` | Shared page list, widths and home-page states | — |

`cold_read_notes.md` is the first-visit log, written before any project document was
read.

**Caveats.** The scripts ran in a Linux cloud workspace (2 CPUs, Chromium 141), not on
Nathan's Mac, so absolute times differ; comparisons are like for like. The `median 43`
contrast hits in `m4_sizes.json` are false positives: the label is positioned below the
track and actually sits on white. The About page's target count includes the credit
lists' links, measured as if the lists were open.
