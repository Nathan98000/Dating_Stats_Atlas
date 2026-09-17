# Design direction — art-direction review of the Phase 2b site

Reviewed 2026-09-16 against four screenshots of build `dc23609755ad` (default ranking,
race-filtered ranking, the all-suppressed empty state, a suppressed metro page). This is a
visual brief, not a methodology review. Current tokens are in `web/src/app/globals.css`.

## 1. Diagnosis

The site currently reads as **a well-set academic document, not a product**. That is a real
achievement over the listicle competition — it looks honest, it is quiet, nothing is
oversold. But four things hold it at "internal tool":

1. **There is no figure/ground.** One flat near-white (`--paper: #fbfbfc`) carries the
   masthead, the controls and the results. Nothing is foreground. The eye has no entry point,
   so every screen reads as one undifferentiated column of text.
2. **Native form controls.** The selects, checkboxes and the range slider are browser
   defaults — macOS blue ticks, stock chevrons, 4px system radius, `#ccc` borders. Nothing
   else on the page has those materials. This single detail does more damage to perceived
   quality than anything else on the site.
3. **A quantitative product with no marks.** Not one bar, dot or rule encodes a value. The
   metro page has a column literally headed **Standing** containing em dashes. Every number is
   set as text, so nothing can be compared at a glance — the exact task the site exists for.
4. **The important numbers are not the biggest ones.** In a ranking row, the largest glyph is
   the rank numeral; the score is ~15px with a 10px "score" label; the pool — the product's
   central claim — is 15px inline in a sentence. In the empty state, the meaningful figure
   (**0**) is buried mid-sentence.

Two supporting problems: mono is overused (units, inline prose, identifiers, values — four
jobs), and red/green parenthetical deltas are the one piece of color in the data, which is
both the most dashboard-like encoding available and the least colorblind-safe.

## 2. Recommended direction — "the almanac"

The reference annual, redrawn for the web: a statistical yearbook that a person reads for
pleasure. Authoritative like a printed reference, warmer than a government table, and
absolutely not a dashboard.

- **Ground.** Retire the blue-white. Move to a barely-blush paper `#FBF6F3`, with true white
  reserved for exactly one surface (the control rail). The tint is the cheapest possible
  credibility move — it reads as stock, not as UI — and it carries a whisper of the subject
  without a single heart or gradient.
- **Type.** Keep the serif for editorial voice, give it a real display size, replace the
  institutional sans, and demote mono to identifiers only.
- **Color.** One accent — **oxblood `#7A2A33`** — for links, focus, the slider and the
  selected row. Data gets its own pair: **teal `#1F6F73`** for "helped your score", **clay
  `#B4562F`** for "hurt it". Never red/green.
- **Shape.** 2px radius on inputs and chips, 0 everywhere else. One hairline weight. No drop
  shadows anywhere. Exactly one card on the site.
- **Density.** Generous vertical rhythm in the results column, tight and structured in the
  rail. 72ch maximum measure for prose; the results column can run wider.
- **Data.** Every number that has a comparison gets a mark: a log-scaled pool bar with its
  margin drawn as a lighter cap, a ten-dot unit chart for odds, diverging bars for
  contributions, a dot-on-a-line for standing.
- **Tone.** Warmth comes from the paper, the serif italic in asides, plain-language copy, and
  one locator map per metro page. Nothing else. No illustration, no photography, no icons
  beyond the drawn chevron and check.

## 3. The ten highest-impact changes, in order

1. **Tint the ground and float the rail.** Body `#FBF6F3`; the controls move onto a white
   surface with a 1px `#E5DED9` hairline, 2px radius, 24px padding, sticky at 24px from top.
   Instant figure/ground; the page stops being one sheet of paper.
2. **Draw the pool bar.** Under each pool figure, a 6px log-scaled bar across the ranked set,
   neutral `#CFC7C1`, with the margin as a 2px lighter cap at its right end. The site's entire
   thesis — a population estimate with visible uncertainty — becomes something you can see
   rather than read. No competitor has this.
3. **Kill every native control.** Custom select (1px hairline, 2px radius, 13px sans, SVG
   chevron at 10px), custom checkbox (16px square, 1.5px ink border, drawn check), custom
   slider (2px track, 14px circular ink handle, oxblood fill to the left of the handle, end
   labels in small caps). Marital status becomes a three-up segmented control, not checkboxes.
4. **Make the score the visual anchor of a row.** 30px tabular sans 600, right-aligned, with a
   3px meter beneath it scaled across the shown range and filled in oxblood. Scores cluster
   between 63 and 73, so a bare number reads as noise; a meter makes a 4-point gap legible.
5. **Replace the Standing em dashes with a dot plot.** A 120px 1px track, a 7px ink dot at the
   percentile, a 1px tick at the median, and the number to its right. One change turns the
   metro table from a spreadsheet dump into a data product. For unranked metros, plot the
   national percentile rather than showing nothing.
6. **Swap the sans.** Public Sans is a federal-register face and it makes the site feel like a
   government publication. Move to **Archivo** (400/500/600, tabular figures on) for all UI,
   body and data. Keep **Newsreader** for display and editorial.
7. **Odds as a ten-dot unit chart.** "3.6 matches per 10 people looking" renders as ten 7px
   dots, 3.6 filled. It makes 3.6 versus 11.5 visceral, it is charming without being cute, and
   it is the one place the site can afford a small delight.
8. **Diverging bars for the movers.** Replace the green/red parentheticals with a compact
   two-column list: stat name, then a ±24px bar from a centre line in teal or clay with the
   signed points at its end. Reads as analysis rather than as a diff.
9. **Rebuild the empty state around its number.** Set the **0** at 56px Newsreader, with the
   explanation beside it, the suppression split as a 100%-width stacked bar (2 / 191 / 0), and
   — the real improvement — two actual buttons: "Widen ages to 22–40" and "Drop the income
   floor", each restating the query it would produce. The honest blank becomes a helpful one.
10. **Fix the mono sprawl.** Mono for identifiers only (`CBSA 39340`, build id). Units become
    11px small-caps sans in `--ink-3`. Values become tabular sans. The inline mono chunk in
    the Provo paragraph ("0 effective respondents; the bar is 100.") becomes plain prose with
    the figure in sans 600 — it currently reads as a code fragment mid-sentence.

## 4. Page by page

### Default ranking (193 metros)

*Working:* the rank numerals in serif; the one-sentence query restatement above the list; row
hairlines rather than cards; the permanent suppression footer.

*Weak:* every row is three lines of run-on text at one size, so the eye cannot find the
comparison; the score label is smaller than the score's own decimal; "moved most by the pool
(+18.1), the odds (+7.0), walkability where residents live 13.0 on the 1–20 index (+4.9)" is a
sentence pretending to be a data display; top-5 is all megacities, so the page reads as a
population ranking until you notice the odds.

*Changes:* three-column row grid — **left** rank + name + flags; **middle** pool with its bar
and margin, then the odds dot chart; **right** score with its meter. Movers become the
diverging-bar list, indented under the middle column, maximum three. "Every stat" becomes a
right-aligned chevron affordance on the row, not a link in the text flow. Add a thin
population-rank annotation ("#1 by population") on the top rows so the reader can see the
ranking is *not* just size.

### Race-filtered ranking (59 metros)

*Working:* the counterweight is present on every row, which is the policy working.

*Weak:* it is appended to the pool line with a `·`, so it reads as a footnote to the pool
rather than a sibling of it — §10.4 asks for the same visual weight and the layout does not
deliver it.

*Changes:* give pool and counterweight equal cells in the middle column, each with its label
above in 11px small caps ("compatible people" / "partnered outside their group"), each with its
own margin beneath. Set the counterweight's percentage at the same size as the pool figure.
Consider a 1px vertical rule between them so they read as a pair of readings.

### Suppressed metro page (Provo)

*Working:* the profile callout; the copy ("An honest blank beats a bad number"); grouping
static stats away from the personalised layer.

*Weak:* the Standing column is entirely em dashes — an empty column is worse than no column;
pillar labels ("Cost", "Reach", "Lifestyle") repeat on every row instead of grouping them;
units in mono; the page has no image of the place at any level.

*Changes:* group the table under three small-caps pillar subheads with a hairline above each,
dropping the per-row labels. Add the dot-plot standings using national percentiles. Add a
**locator map**: a 220px square US outline with the metro's dot in oxblood, other metros in
`#E5DED9` — informative, cheap, and it gives every one of 387 pages a face. Right-align the
value column and set values in 18px tabular sans with small-caps units.

### All-suppressed empty state

*Working:* the copy is genuinely good and the suppression breakdown is honest.

*Weak:* three stacked paragraphs of identical weight; the "0" is invisible; the reader is told
to "loosen a filter" but must work out which.

*Changes:* as change 9 above. Also move the "Fewer than 40 metros" notice *above* the zero
block — it is the general policy, not a reaction to this query — and set it in the serif
italic at 15px with a 2px oxblood left rule, which becomes the site's one editorial-aside
component.

## 5. Design system

**Fonts** — Display/editorial: Newsreader 400/600 + italic. UI/body/data: Archivo 400/500/600,
`font-variant-numeric: tabular-nums` globally on data. Identifiers: IBM Plex Mono 400.

**Type scale (px/line-height)** — metro title 44/1.1 · site title 26/1.2 · section 20/1.3 ·
rank numeral 34/1 · metro name in row 19/1.3 · score 30/1 · pool 22/1.15 · body 15/1.55 · row
detail 14/1.5 · label 11/1 uppercase +0.08em · unit 11 small-caps · mono 12.5.

**Color** — paper `#FBF6F3` · surface `#FFFFFF` · ink `#1A1A1C` · ink-2 `#54555C` · ink-3
`#6B6C73` (4.9:1 on paper) · rule `#E5DED9` · rule-strong `#1A1A1C` (masthead, 2px) · accent
`#7A2A33` · accent-hover `#5E1F27` · selected-row tint `#F3EAE4` · data-neutral `#CFC7C1` ·
data-up `#1F6F73` · data-down `#B4562F`. Dark theme: paper `#15161A`, surface `#1B1D22`, ink
`#EDEAE7`, rule `#2C2E34`, accent `#D98A93`, data-up `#5FB3B6`, data-down `#E08A5F`.

**Radius** 2px on inputs, chips, the rail; 0 on rows, tables, bars. **Borders** 1px `--rule`
hairlines; 2px ink under the masthead; no border on table cells, only row bottoms.
**Shadows** none — the rail separates by tint and hairline, not elevation.

**Spacing** 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64. Row padding 16px block. Rail padding 24px.
Column gap 48px. Page gutter 24px (16px under 600px).

**Buttons** Secondary: 1px ink border, 2px radius, 6px/14px padding, 13px Archivo 600, ink on
transparent; hover fills `#F3EAE4`. Primary: ink fill, paper text. Text/link: accent, 1px
underline at 0.12em offset, thickening on hover. Focus: 2px accent outline, 2px offset,
everywhere.

**Cards** Exactly one: the control rail. Everything else is hairline-separated on the paper.
**Chips/badges** for flags: 11px uppercase, 2px radius, 1px `--rule`, no fill, `--ink-3`;
warning flags take a clay border.

**Data marks** Bars 6px tall, square ends, `--data-neutral`, oxblood for the focused metro;
margin caps 2px lighter. Dot plot: 1px `--rule` track, 7px ink dot, 1px median tick. Unit
dots: 7px circles, 3px gap, ink filled / `--rule` empty. Diverging bars: 24px max half-width,
2px tall, teal/clay. No gridlines, no axes, no legends where a label will do, and **no
sparklines** — the artifact is a single 5-year vintage and there is no time series to draw.

## 6. Before → after

Today the site opens as a page of text on a cold white sheet, with system form controls down
the left and three paragraphs of numbers per city. It reads as a competent internal tool.

After: the page opens on warm paper. A white control panel sits at the left under a heavy
black rule, its inputs drawn in the same hand as the rest of the page. To its right, each city
occupies a calm three-column band — a large serif rank and name; a block of readings where the
compatible-population figure carries a bar with its uncertainty drawn at the end, and the odds
render as ten dots with three and a half filled; and at the right a large tabular score over a
short oxblood meter. Under each band, two or three small diverging bars in teal and clay say
what moved this city for *your* weighting. Nothing is boxed, nothing is shadowed, and the only
saturated color on screen is the oxblood accent and the two data hues.

A metro page opens with the city's name at 44px, a small locator map, and its stats grouped
under three headings, each value sitting on a dot-plot track so you can see where it stands
without reading a number. An empty result is a large 0 with two buttons that fix it.

The impression to aim for: *someone with statistical training and a good eye made this on
purpose.* Credible, contemporary, quietly warm — a reference book you would actually pick up.
