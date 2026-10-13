# Measurements for the round-4 review (12 October 2026)

Round 3's scripts (`atlas/web/scripts/review/`, as Phase 6 ported them to this Mac) are
copied here, so that round 4's numbers sit beside round 3's, with the changes noted below.
They ran on Nathan's Mac (Low Power Mode off: `pmset -g | grep lowpowermode` said 0),
headless Chromium through Playwright 1.63 and `@axe-core/playwright` 4.13. **WebKit
(Safari's engine) is not installed on this Mac, so there was no WebKit pass**, and none was
downloaded.

Two targets:

- **Local:** a production build of `main` at `e34aa55` (code as `76de4ef`), `next build`
  with `NEXT_DIST_DIR=.next-review` and `next start -p 3400`, over the API on build
  `d62202fd0280` at port 8100, both started from the main checkout as the prompt says.
  Note: `next start` does not compress `/api/rank` (1.5 MB raw); Caddy does on the live site.
- **Live:** https://datingscenedata.com (m4.3.0 on d62202fd0280). Page weight at 1440 and
  390 (one pass), speed (5 runs per condition, one batch per script with pauses), and
  one-request server checks. No load testing.

To run them, first link `atlas/web/node_modules` here (`ln -s ../../../../web/node_modules node_modules`),
so the scripts' bare imports resolve, and delete the link after use (it was removed after this review). Run each script from the output folder, for example
`cd local && node ../m1_pages.mjs`, or `BASE=https://datingscenedata.com node ../m1_pages.mjs 1440,390`.

| Script | What it measures | Output |
|---|---|---|
| `common.mjs`, `states.mjs` | Round 3's, with `BASE` defaulting to :3400, all eight stat pages, "Refine your search", and two new home states: the card's balance box open, and race chosen in Sharpen compatibility | — |
| `m1_pages.mjs [widths]` | Every page (23) at every width (8), cold: title, og tags, canonical, sideways scroll, clipping, page weight by kind | `local/m1_pages.json`, `live/m1_pages_1440_390.json` |
| `m2_speed.mjs [base] [label]` | Home: LCP, FCP, TTFB, CLS, and "Cost of living: A lot" → list settled; 5 cold runs at 1440 unthrottled and 390 slow phone (150 ms RTT, 1.6 Mbps down, 750 kbps up, 4× CPU) | `local/m2_speed_local.json`, `live/m2_speed_live.json` |
| `m2c_pages.mjs [base] [label]` | **New.** The same paint and shift figures for a city page, a compare pair and a stat page; 3 runs per condition | `local/m2c_pages_local.json`, `live/m2c_pages_live.json` |
| `m3_axe.mjs` | axe, all default rules (WCAG A/AA + best practice) and experimental, every page at 1440 and 390, plus 14 home states | `local/m3_axe.json` |
| `m4_sizes.mjs` + `audit_in_page.js` | Targets under 44×44 below 1120, text under 12px, contrast where used, control boundaries under 3:1, at 390/768/1024/1119/1440 | `local/m4_sizes.json` |
| `m5_keyboard.mjs` | Tab order and focus at 1440 and 390; the sheet, info boxes, age popover, menu, header search | `local/m5_keyboard.json` |
| `m6_reflow_motion.mjs` | Sideways scroll at 320 and 200% zoom; motion with and without reduced motion | `local/m6_reflow_motion.json` |
| `m7_aria.mjs` | Accessibility-tree snapshots | `local/m7_aria.txt` |
| `m9_pending.mjs` | The phone's weight change in the sheet (throttled; uncompressed locally) | `local/m9_pending.json` |
| `m10_geometry.mjs` | Where #1 sits, row heights, at every width | `local/m10_geometry.json` |
| `numbers_check.py` | **New.** Served numbers side by side, for three searches: the "What moved the score" bars against the "median N" tick, chips against bars, shared balance figures | `numbers_check.json` |
| `photo_sheets.mjs` | **New** (a sharp port of round 3's `photo_sheets.py`; no PIL here): all 193 ranked cities as the desk card (16:10) and the phone card / band (16:7) crop them | `../screens/photos/sheet-01…10.jpg`, `photos.json` |
| `live_site.sh` | **Extended.** Compression and caching, plus redirects from the old addresses, certificates, TLS versions, security headers, robots.txt, sitemap, canonical links, icons, starter files | `live_site.txt` |
| `driver.mjs` | **New** (a Node port of `cold_read_driver.py`): the persistent headless browser for the cold read and the tasks | — |
| `og_live.txt`, `og_by_agent.txt` | Every page's title and link-preview tags on the live site; which user agents get them in the `<head>` | — |
| `keyboard_bar.txt` | **New.** The hand-run Tab and Shift+Tab sequences at 390 and 1024 showing that "Refine your search" is never reached going forward | — |

The scripts also write first-screen shots to `shots/` beside their output; those were deleted
after the review (90 MB, regenerable), except the two the review cites, now in `../screens/`.

`cold_read_notes.md` is the first-visit log, written before any project document was read.
Round 3's other scripts (`gzip_proxy.mjs`, `img_proxy.mjs`, `m2b_image_sim.mjs`, `m3_fix.mjs`,
`m8_fullpages.mjs`, `phase6_screens.mjs`, `rank_bytes.py`, `who_lives_here.py`,
`photo_sheets.py`) are copied for completeness but were not needed: compression and the
sized photographs are live, so the live site measures them directly.

**Caveats.** The "median 43" contrast hits in `m4_sizes.json` are round 3's known false
positive: the label sits below the track, on white. Small targets the audit lists are all
links inside running text (exempt). The local phone weight-change time is uncompressed;
use the live figure.
