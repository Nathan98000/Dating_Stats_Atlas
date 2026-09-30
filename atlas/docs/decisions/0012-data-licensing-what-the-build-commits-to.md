# ADR 0012 — Data licensing: what the build commits to

Date: 2026-09-28 (Phase 4, Stage 2)
Status: accepted. Every commitment below is **Nathan's decision**. Phase 4
Stage 3 encodes them in the typed licence registry
(`pipeline/adapters/base.py`, `LicenseTerms`) so the build enforces them;
Stage 4 (ADR 0016) replaces the Pew check; Stage 5 puts every credit in
one place. The number was reserved in Phase 3c for this record.

## Context

The site serves figures built from public federal data, shows
photographs from Wikimedia Commons, and until Phase 4 read one Pew
Research Center table at build time as a check. Each source comes with
its own terms and its own way of being credited. Until now the build
recorded a licence name and a short attribution per source, and the
credits were scattered: a line under the hero, under each city
photograph and under each stat-page photograph.

This record sets, source by source, what the build commits to. The
exact citation strings are the registry's; this record repeats them so
they can be read in one place.

## Across every source

- **Citations.** Every source a served figure traces to is cited, with
  the exact string below, in one "Sources and credits" section on the
  About us page (Stage 5). No credit line sits under a photograph or
  anywhere else.
- **No agency logos or seals**, and nothing implying endorsement. No
  agency logo, emblem or seal appears in `web/public` or on any page
  (Stage 3 confirms it); no sentence says or suggests that an agency
  endorses, certifies or produced the site's figures. *[Amended after
  Phase 4c: two restored photographs show one, by Nathan's decision — the
  last section.]*
- **Modelled figures are ours.** A figure the site computes — the pool
  counts, the balance, the compatibility figure ("chances of matching"
  until Stage 5), every rate per 100,000 — is never called "Census
  data". It is an estimate by Dating
  Stats Atlas from Census data. Stage 3 lists every sentence that said
  otherwise, for rewording.
- **The build enforces it.** A served feature that traces to a source
  marked unshippable fails the build.

## Source by source

### U.S. Census Bureau

Used: the ACS 2020–2024 5-year Public Use Microdata Sample (every people
count and the compatibility figure's model); the ACS 2020–2024 5-year
detailed tables (tract populations, renter households, calibration);
the 2020 Census Demographic and Housing Characteristics File (allocation
weights); County Business Patterns 2023 (places to go out); the
geographic relationship files, TIGERweb and the 2023 cartographic
boundary file (geography and the locator map).

- **Citation**, one per product and vintage, in the form: "Source: U.S.
  Census Bureau, [product, vintage]; estimates by Dating Stats Atlas."
- **The Census API notice**, because the census adapter calls the Census
  Data API: "This product uses the Census Bureau Data API but is not
  endorsed or certified by the Census Bureau." It appears with the
  citations.
- **Never "Census data"** for a modelled figure (above).

### U.S. Department of Housing and Urban Development

Used: the FY2027 50th Percentile Rent Estimates (rent), from HUD's bulk
files — no HUD API is called.

- **Citation:** HUD only — "Source: U.S. Department of Housing and Urban
  Development, FY2027 50th Percentile Rent Estimates." No API notice.
- A dated snapshot of HUD's terms page joins the counsel-packet
  attachments before launch (`docs/deploy.md`, "Before launch").
  *[Saved 30 September 2026: `hud-terms_2026-09-30.pdf`, listed in the
  attachments' `MANIFEST.md`.]*

### NOAA National Centers for Environmental Information

Used: GHCN-Daily station observations, 1991–2020 (nice days a year).

- **Citation:** "Source: NOAA National Centers for Environmental
  Information, Global Historical Climatology Network – Daily
  (GHCN-Daily), 1991–2020."
- **US weather stations only.** Every served metro's station is a US
  station; Stage 3 reports each one, and any station outside the US is
  rematched to the nearest qualifying US station in a build of its own.

### U.S. Environmental Protection Agency

Used: the Smart Location Database v3.0 (walkability), street-network
measures only.

- **Citation:** "Source: U.S. Environmental Protection Agency, Smart
  Location Database v3.0 (June 2021)."

### U.S. Bureau of Economic Analysis

Used: Regional Price Parities by metropolitan area, 2024 (everyday
prices).

- **Citation:** "Source: U.S. Bureau of Economic Analysis, Regional
  Price Parities by Metropolitan Area, 2024."

### National Center for Education Statistics (IPEDS)

Used: IPEDS 2023–24 (students).

- **Citation:** "Source: U.S. Department of Education, National Center
  for Education Statistics, Integrated Postsecondary Education Data
  System (IPEDS), 2023–24."

### U.S. Office of Management and Budget

Used: the metropolitan area delineations of OMB Bulletin No. 23-01
(which counties form each of the 387 metros).

- **Citation:** "Metropolitan areas as delineated in U.S. Office of
  Management and Budget Bulletin No. 23-01 (July 21, 2023)."

### Federal Bureau of Investigation

Used: the Crime Data Explorer — the 2025 figures, as context on city and
compare pages, never scored.

- **Citation:** "Source: Federal Bureau of Investigation, Crime Data
  Explorer, 2025."
- **The crime caveat stays** where the figures are. It is a note on the
  data's quality, not an attribution, so it does not move to the credits
  section.

### MIT Election Data and Science Lab *[added in Phase 4d — the last section]*

Used: *County Presidential Election Returns 2000–2024* (Harvard Dataverse,
doi:10.7910/DVN/VOQCHQ, V20), for political lean, the 2024 figure, as
context on city, compare and stat pages, never scored (ADR 0019). Its
state-level returns (*U.S. President 1976–2024*, doi:10.7910/DVN/42MVDX)
serve as a check only.

- **Licence:** CC0 1.0, read from the dataset page on 30 September 2026.
- **Citation**, the data citation the dataset page shows, which its Terms
  tab asks for, with the house full stop: "MIT Election Data and Science
  Lab, 2018, "County Presidential Election Returns 2000-2024",
  https://doi.org/10.7910/DVN/VOQCHQ, Harvard Dataverse, V20,
  UNF:6:xvsJJxrfXMIvzAuDYlfvVw== [fileUNF]."
- **Context only**: never scored, never a filter, never a weight, never
  asked of the visitor (ADR 0019).

### U.S. Bureau of Labor Statistics

Used as a check only (QCEW beside County Business Patterns); no served
figure traces to it, so it is not cited on the site. Its registry entry
keeps a citation for the day one does.

### Wikimedia Commons photographs

The city photographs, the stat-page photographs and the home-page hero.

- **Licences:** public domain, CC0, CC BY and CC BY-SA only, read per
  image from the Commons API; nothing NC or ND, and nothing whose licence
  or author cannot be read.
- **Subjects:** no photograph whose subject is an identifiable person,
  and no photograph of a recent US sculpture or mural. A removed
  photograph falls back to no photo — the existing "no file, no photo"
  rule. *[After Phase 4c Nathan kept fifteen of the photographs this rule
  removed — the last section.]*
- **The record, per photograph in use:** title, author, source link,
  licence and licence-version link, and whether the layout crops it. A
  crop is an adaptation, and is credited as "cropped".
- **The hero** stays public domain or CC0 only, because the band crop is
  an adaptation. If the hero is Carol M. Highsmith's, its credit is
  "Carol M. Highsmith Archive, Library of Congress, Prints and
  Photographs Division."
- **Credits** live in the one "Sources and credits" section, in a
  collapsible list. The photographs under CC 2.0 and 3.0 licences are
  listed in PHASE4.md for Nathan to confirm that the central credit
  suits them. *[Confirmed after Phase 4c — the last section.]*

### Pew Research Center

The newlywed intermarriage table by metro (2011–2015).

- **Build-time only: never published, and never compared in public.**
  The table lives only in a gitignored private folder on the build
  machine. Phase 4 took it, and every per-metro value copied from it,
  out of the repository and its history.
- **Replaced** as the intermarriage check by one computed from the
  Census PUMS (ADR 0016).
- Its licence entry stays, marked unshippable, and `build.validate`
  keeps its hard "pew never shipped" check.

### Zillow, Redfin, Opportunity Insights, PRRI

None is used, and none will be used without written permission from
its publisher. For home values, the substitute is the Federal Housing
Finance Agency's House Price Index.

### Overture Maps and Foursquare Open Source Places (deferred)

Both stay deferred with `poi_venue_density`. Their credit lines,
recorded now from each source's own published attribution page (the
dated snapshots of 24 September 2026), for the day they are used:

- **Overture Maps Foundation:** "Overture Maps Foundation,
  overturemaps.org", with the date the data were accessed; any layer
  built from OpenStreetMap data adds "© OpenStreetMap contributors,
  Overture Maps Foundation". The Places theme's own attribution section
  is read again at that time, since the snapshot shows it collapsed.
- **Foursquare OS Places:** "Foursquare OS Places © Foursquare Labs,
  Inc., licensed under the Apache License, Version 2.0", with the full
  text of Foursquare's NOTICE file preserved and a copy of the licence
  provided. The Places Portal's account terms are Nathan's to accept
  when venues are un-deferred.

### Not changed by this record

The Cooperative Election Study and the 2020 US Religion Census stay
"not started", as `docs/sources.md` lists them.

## Consequences

- Stage 3 adds `shippable`, the exact citation and the conditions to
  every `LicenseTerms`, and the build fails if a served feature traces to
  an unshippable source.
- The About us page gains the one "Sources and credits" section, and
  the `Attribution` lines under the hero, the city photographs and the
  stat-page photographs go (Stage 5).
- Adding a source means adding its registry entry, with its citation and
  conditions, before any feature can trace to it.

## Amended after Phase 4c (2026-09-29): the photo review, decided

These are **Nathan's decisions** on the photographs Stage 3 removed
pending his confirmation, and on its one finding (the record:
`results/phase4/photo_review.json`; PHASE4.md, "After the phase").

- **Fifteen of the sixteen removals are restored**, as they were. For them
  he sets aside the subject rule — three show recognisable people, eight
  recent sculptures and two murals — and, for Hilton Head Island (the
  America 250 emblem on its lighthouse) and Lakeland (the city's logo sign),
  the line under "Across every source" that no agency logo, emblem or seal
  appears on any page. The rules stand for every other photograph and for
  new ones: the two replacements below meet them.
- **Waco's collage stays removed, and Waco and Savannah take
  replacements.** Savannah's photograph showed Tarangire National Park,
  Tanzania, because the lookup landed on the article "Savanna". Each
  replacement is a Commons file the review names (`replaced`) — the Waco
  Suspension Bridge's tower (CC BY-SA 2.0, Nathan's pick of three) and the
  Forsyth Park fountain (CC BY-SA 4.0) — which the pipeline sources through
  the same licence rule on any re-run, while refusing the files they
  replace. Neither Commons description can serve as alt text (the
  fountain's is only in Italian, the bridge's is the photographer's
  caption), so the review gives both an English one, approved by Nathan.
- **The photographs under Creative Commons licences before 4.0 stay** in
  the one central credit list, the question the Wikimedia section left
  open; with the restorations and Waco's replacement they are 150 of the
  372 photographs shown.


## Amended in Phase 4d (2026-09-30): the election returns

A new source, for political lean (ADR 0019, Nathan's decision: context,
never scored or asked). What the build commits to:

- **The county returns.** MIT Election Data and Science Lab, *County
  Presidential Election Returns 2000–2024*, Harvard Dataverse,
  doi:10.7910/DVN/VOQCHQ, version 20, CC0 1.0. The licence was read from
  the dataset page on 30 September 2026. Its Terms tab adds the Dataverse
  community norm that credit is given by the data citation the page shows.
  The registry entry `medsl_president` (shippable) carries that citation,
  with the house full stop, and it appears only in Sources and credits.
  The stat page's source line names the lab and links the dataset, as
  every stat page's line does.
- **Obtained by hand.** The dataset sits behind a guestbook (a name, an
  email, an institution, a position, then "Accept" on its terms), which
  the pipeline never fills in. Nathan downloaded it himself.
  `adapters/medsl_president.py` pins that copy by its SHA-256, checked
  against the MD5 Dataverse publishes, and its fetch-manifest entry says
  how it was obtained.
- **A check only, never shown.** The lab's state-level returns (*U.S.
  President 1976–2024*, doi:10.7910/DVN/42MVDX, CC0 1.0, no guestbook) and
  the Census Bureau's 2024 Alaska district-to-tract relationship file are
  read to check the county sums and to decide Alaska's metros. No served
  figure traces to either, so neither is cited on the site (the QCEW
  precedent).
- **No logo, and nothing implying endorsement** by MIT or the lab, as for
  every source.
