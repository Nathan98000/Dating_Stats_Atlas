# ADR 0006 — Eight equal race groups, one-bedroom rent, and the site's first shipped third-party assets

Status: accepted (Phase 2e, models m2.2.0 and m2.3.0)
Reverses: ADR 0004's always-counted race rule. Amends: ADR 0005's crime
rendering and rent input. All three open decisions from Phase 2d are
settled here by Nathan: eight equal groups, the one-bedroom measure, and
all four cleared photo licences.

## 1. The race control: the selection is the filter (m2.2.0)

ADR 0004 ORed "Two or more races" and "Another race" into every race
selection so a filter could never exclude people who fit any selection.
Phase 2d moved that rule's disclosure off the panel and raised the
question; Nathan decided it: **a control whose arithmetic the visitor
can check beats one that quietly adds people they did not tick.**

Eight equal checkboxes, one rule, no special casing anywhere in the
stack. `resolve_race_levels` returns exactly the ticked levels; zero
ticked or all eight ticked is no filter (the identical universe, spelled
two ways, and the frontend normalises the spelling so one search has one
URL and one permalink). The inverted tests assert the three properties
that define the change: a single newly-selectable group masks exactly
its cube level, a partial selection's pool equals the sum of its ticked
groups' pools to float tolerance, and no served figure includes an
unticked level.

**Balance is untouched.** `balance_masks` passes no race on purpose —
m2.0.0 made the sex ratio race-blind so the figure means what its name
says and holds still as filters move. Race enters the pool and nothing
else.

**What moved, measured** (`results/phase2e/race_change_report.json`):
default-setting outputs reproduce m2.1.0 to literally 0.0e+00 across
every race-free persona; race-filtered requests drop what they no longer
silently include — asian_nh in Los Angeles −24.6%, black_nh+hispanic in
Chicago −6.9%, asian_nh in Urban Honolulu −40.5%, largest exactly where
the multiracial share is largest. The newly selectable levels land on
their own calibrated interval strata (1.25 / 1.226), and a thin
selection suppresses through the ordinary gate with the ordinary reasons.

## 2. Rent: the one-bedroom median (m2.3.0)

The all-units median gross rent (B25064) moves with each metro's mix of
studios and family houses, so a metro of new two-bedroom stock reads
expensive for reasons a single person's rent never sees. The verification
came first: Austin's build value matched data.census.gov to the dollar
and no jam value exists anywhere — the data was right; the measure was
the question. The rent card and the cost pillar now take **B25031's
one-bedroom median gross rent**, the number a single person actually
faces, selected from the group metadata by label (the P5/P18
discipline). Fallback for a metro without it: the all-units median with
a build-report flag — unneeded, since all 387 metros publish the
one-bedroom figure. The unit line says what the figure is (a typical
one-bedroom, utilities included — gross rent includes them); pillar
weights are unchanged; New York's rent-stabilisation distortion is
disclosed on the rent stat page in a sentence rather than adjusted away.

The honest before/after: Austin does NOT drop (85th → 87th percentile —
its one-bedroom rents are genuinely high); Provo falls ten percentile
points and Riverside six, which is the unit-mix distortion the change
exists to remove.

## 3. Crime bands are neutral, and the detail lives one click deep

Crime renders as two ordinary-looking cards with a five-band national
position whose tones are **deliberately neutral**: colouring a low rate
"good" would perform exactly the between-cities comparison the FBI's
caution — now in each card's popover with the coverage line and the
explainer link — disclaims. The compare page carries two plain numbers
per city under one banner. D01 stands untouched: never scored, asserted
in three layers.

## 4. Photographs ship, licence-first

The site's first third-party shipped assets. Sourcing is mechanical and
recorded: each principal city's Wikipedia lead image, licence read from
the Commons `imageinfo`/`extmetadata` API. **Public domain, CC0, CC-BY
and CC-BY-SA ship** (Nathan cleared all four); anything carrying NC or
ND terms, anything whose licence the API cannot state, and any CC-BY
family file whose author field is unreadable (attribution would be
impossible) is refused with the reason counted. Share-alike obligations
are satisfied by construction: images display **unmodified** — scaled to
fit, never cropped, recoloured or composited, so no adaptation exists
for a licence to attach to — and the attribution (author, licence name,
deed link, source link) is composed once into the committed manifest
(`results/phase2e/city_images.csv`, `stat_images.csv`) and rendered from
it. Files themselves are gitignored and re-fetchable; manifest hashes
pin them. A photo without a manifest row does not render, which makes
"no image without readable licence metadata ships" structural. Two
things remain for Nathan (recorded in PHASE2E.md): the counsel packet's
source table row, and the human pass over 387 thumbnails for images that
are technically fine and visually wrong.

## 5. The map is data, not a library

State boundaries from the Census cartographic boundary file
(cb_2023_us_state_20m), projected to Albers USA by d3-geo **in the build
script**, shipped as static SVG path strings with the metro dot from the
build's Census internal point. The browser gets paths; an e2e gate greps
the client chunks to prove no mapping library reached the bundle.
(TIGERweb's generalized layers refuse geometry over their query API —
the boundary file is both the brief's literal source and the one that
works.)

## 6. Findings this phase's checks surfaced (fixed, recorded)

- The item-5 search matrix caught **two shipped display-name defects**:
  DC's slug carried the description grammar's "the" (orphaning its
  colloquials since Phase 2c — a dead-key assertion now guards the
  index), and the title-split heuristic served "Winston, NC" and
  "Louisville/Jefferson County, KY". Display names now prefer the
  TIGERweb place resolution with natural-name candidate order, a 150 km
  sanity guard, and two registry judgments (Lexington, Macon) where the
  Census-attested name is consolidated-government legalese.
- The first crime aggregation handed every agency its **state's
  population** (median coverage 0.0 made it undeniable); the population
  series is now keyed by the agency's own name. Recorded in Phase 2d's
  commit history; restated here because item 2 built on the corrected
  table.
