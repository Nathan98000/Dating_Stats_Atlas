# Dating Stats Atlas — data licensing and publication review

**Prepared for counsel · 24 September 2026 · Nathan, sole founder**

## What we are asking for

A written memo covering (a) whether each data source listed in Part B may be used as
described, and on what conditions, and (b) the three analysis questions in Part C that we
cannot answer ourselves — our exposure on personalised rankings that use race and
ethnicity, both as an optional filter and inside the "chances of matching" figure described
in Part A; whether the distinction we draw between publishing a rendered page and
distributing data holds up; and what follows from a visitor's own race or ethnicity, if
they choose to give it, travelling in the page address and in a cookie.

A per-source table of **yes / no / yes-with-conditions**, plus required attribution or
disclaimer language, is the most useful form for us: our build system has a typed licence
field on every data source and refuses to ship if a source marked non-shippable reaches the
published artifact, so your answers get encoded and enforced automatically.

We are **not** asking about corporate structure, employment, tax, or fundraising.

Attached: dated copies of each source's licence or terms page, saved on the date shown in
each filename.

## Part A — The product, in one page

**What it is.** A pre-launch website that estimates, for one person's stated preferences,
how many compatible potential partners live in each US metropolitan area, how closely those
people resemble the people who actually pair with someone like the visitor (the "chances of
matching" figure below), and what living there costs — then ranks the metro areas
accordingly. It also shows, for information and not as part of the ranking, the balance of
single men to single women at the visitor's chosen ages. It is a statistical reference tool,
not a dating app: there are no profiles, no messaging, and no other users to meet.

**Where the numbers come from.** Almost entirely from US federal statistical agencies,
chiefly the Census Bureau's American Community Survey public-use microdata — anonymised
individual survey records, published by the Bureau for exactly this kind of analysis, with
no names, addresses, or identifying detail. We aggregate those records to metropolitan-area
population estimates. Nothing we publish describes an identifiable person.

**Chances of matching (added 23 September 2026; race and education combined since 24
September).** Beside the count of compatible people, each metro area now carries a second
figure, "Chances of matching": how closely the people who match the visitor's search
resemble the people who actually pair with someone like the visitor, where 100 is the US
average for that same search. The pattern behind it comes from real couples in the same
Census survey — the person answering the survey and their spouse or unmarried partner in the
household — across the whole country: how often each age gap, each education pairing and
each racial or ethnic pairing occurs among couples, compared with how often it would occur
if single people paired at random. That national pattern is adjusted a little for each
metro's own couples and applied to the single people who match the search there. It
describes observed pairing patterns in aggregate. It is not a prediction about any person,
and the page says so in as many words ("an aggregate pattern from recent unions, not a
prediction about any one person"). A slider divides the people side of the score between
pool size and chances of matching; by default it sits a little towards pool size (pool size
carries 30% of the overall score and chances of matching 25%; cost, social life, weather
and students share the rest). The figure is displayed as a whole number against the US
average of 100 and is capped on the page at "250+"; the ranking behind the page uses the
uncapped figure. What the page tells the visitor about race is in three places, all in the
same register as age and education and with no separate caveat, by recorded decision: the
information box beside the figure says it compares the visitor's matches against "the
racial and ethnic pairings that occur"; the "How this is measured" text names race or
ethnicity as one of the three inputs, says the pattern is measured against random pairing,
and carries the not-a-prediction sentence; and the optional "about you" controls carry a
note that the visitor's own education and race or ethnicity feed only this figure, and that
the average for people of their age and sex is used if either is left unset.

**What a visitor may tell the site, and what it does with it.** About themselves: their sex
and age (the panel always holds a value for both, starting from a stated default profile),
and optionally their education (four levels) and their race or ethnicity (the eight Census
categories, with "Prefer not to say"). About whom they are looking for: sex (defaults to the
opposite of their own), an age range, marital status (never married, previously married, or
both), a minimum education, a minimum income, and any of the eight race or ethnicity groups
as a filter. And how to weigh things: the slider, four "how much this matters" controls,
and a sort order. Everything after the visitor's own sex and age is optional.

A visitor's own race or ethnicity, if given, changes their ranking in one way: the
chances-of-matching figure is then built from how often people of that group pair within
the group and with each of the other groups — measured nationally for each sex and adjusted
a little per metro — and, since 24 September, from how those rates differ by education. Two
visitors identical in every other respect can therefore see different figures and a
different order of cities for the same search; measured on the current build, the
difference is material, not cosmetic. A visitor who gives no race or ethnicity is not
outside those patterns: their figure uses the average of the patterns across all eight
groups, weighted by how common each group is among single people of their sex and age
nationally, so the observed rates at which groups pair with one another shape every
visitor's ranking to some degree. The same holds for education. For a visitor seeking
their own sex, the age gaps and the education pairings come from same-sex couples in the
same survey; the racial and ethnic pairings are borrowed from opposite-sex couples, because
the survey's same-sex couples are too few to measure them dependably for the smaller
groups. The page says this in one sentence on every row of a same-sex search and on the
methodology page.

**What we collect from visitors.** At launch there are no accounts, no login, no analytics,
no third-party scripts (fonts and photographs are served from our own site) and no database
of visitors or searches; the ranking service holds nothing between requests and writes
nothing. A visitor's search nevertheless lives in two places on their own device, and both
can carry the two optional items about the visitor themselves. First, the page address:
every setting above is a parameter in the URL of the results page (for example `self_race=`
and `self_edu=` beside the filters), so it sits in the browser's history and in any link the
visitor copies or shares; a "permalink" to a fixed edition of the results carries the same
settings encoded in its path. Second, a first-party cookie named `dsa_prefs`, written by
the page whenever the visitor changes their search so that the search follows them to the
site's other pages: it holds the same parameters as the URL, is kept for about 180 days, is
restricted to our own site (SameSite=Lax) and is sent by the browser with every request to
our site; the site reads it only when a page is opened with no search parameters in the
URL. What our servers and the host keep: the ranking service's standard request log records
the time, path and status of each ranking call made by our own web server — the search
itself travels in the body of that call and is not logged — and our web server writes no
per-request log of its own. The hosting provider in our committed but not yet deployed
configuration, Fly.io, terminates the visitor's connection, so its edge sees every request
address and cookie in passing, and it retains both processes' logs for its own standard
period; we have set up no log shipping and no other recording. In short: our servers store
no search; the visitor's browser does, in the URL and the cookie. Questions 8 and 9 follow
from this.

**Aggregate only, with suppression.** Every figure displayed is a population estimate for a
metro area of at least 250,000 people. Where the underlying sample is too small to support
an estimate — fewer than 100 survey respondents — we suppress the result and say so rather
than publishing a number; the chances-of-matching figure is suppressed on the same rule.
One disclosure decision a reviewer will otherwise ask about (Phase 2g, ADR 0008): the site
computes margins of error on every count and suppresses on them, but since the
methodology-page rewrite it no longer tells visitors anywhere that this uncertainty
machinery exists — the removal was deliberate, and the technical figures remain available
on request.

**Build time versus serve time.** A build process reads the source data and produces a
fixed, immutable data file. The website reads only that file. Some sources are read **only
during the build**, used as a quality check, and never contribute any value to the published
file; the Pew Research Center table in Part B, Group 3, is one today. This separation is
enforced by an automated assertion that fails the build, not by staff discipline (one
qualification, for that table, is stated in Group 3).

**No public API.** The site renders pages. There is no data feed, no bulk download and no
documented public endpoint — the ranking endpoint is same-origin and undocumented. This is a
deliberate decision (see question 3).

**Identity filters.** A visitor may optionally filter by race and ethnicity, using the eight
standard categories derived from Census variables. Our own guardrails: the filter is off by
default; we publish no page or headline of the form "best cities to meet [group] women";
metro pages describe population composition as demography; and whenever the filter is on we
display alongside it the observed rate at which people of that group partner outside it,
computed from the same public data, so the filter reads as the visitor's own preference
rather than a boundary. The chances-of-matching figure uses race and ethnicity differently —
as observed pairing patterns rather than as a filter — and is described above; question 2
covers both. A later release will add a religion estimate, modelled from a public survey and
labelled as modelled with a wider stated uncertainty.

**Status and intent.** Pre-launch, no public URL, no revenue. Intended to become a
commercial product; business model not yet decided.

## Part B — Data sources

**Group 1 — federal sources that will ship at launch.** Our understanding is that these are
US government works, usable commercially with attribution. Question 1 asks you to confirm
that and to specify required attribution or disclaimer language.

| Source | Publisher | Provides | How used | Reaches the site? |
|---|---|---|---|---|
| ACS 5-year public-use microdata (PUMS), 2020–2024 | Census Bureau | The core population estimates; since September 2026 also the couples (spouses and unmarried partners in the same household) behind the chances-of-matching figure | Aggregated into our data file; the pairing pattern is fitted from the couple records and stored as national tables plus one small adjustment per metro | Yes, as aggregates |
| ACS 5-year summary tables | Census Bureau | Median rent, group-quarters share, calibration totals | Context features; accuracy checks | Yes |
| 2020 Census DHC (tables P1, P18) | Census Bureau | Tract-level population and group-quarters counts | Geographic allocation weights | Indirectly, via weights |
| Census geographic relationship files (2020 tract-to-PUMA, 2010 tract-to-PUMA, 2020↔2010 tract crosswalk) | Census Bureau | Geographic crosswalks | Geographic allocation | Indirectly |
| TIGERweb map services | Census Bureau | Centre points for counties and places | Metro display names, the dots on the locator map, and the joins from metros to weather stations and police agencies | Yes, as names and map positions |
| OMB Bulletin 23-01 metro delineation | OMB | Which counties form each metro area | Defines the geography | Yes, as names |
| Regional Price Parities | Bureau of Economic Analysis | Cost-of-living deflator | A scored feature | Yes |
| County Business Patterns | Census Bureau | Venue and establishment counts by industry | A scored feature | Yes |
| Quarterly Census of Employment and Wages | Bureau of Labor Statistics | Cross-check on the above | Accuracy check | No — check only |
| Smart Location Database v3.0 | EPA | Street-network walkability measures | A scored feature | Yes |
| GHCN-Daily observations 1991–2020 | NOAA | Pleasant-day counts (replaced Climate Normals in Phase 2d) | A scored feature | Yes |
| 50th Percentile Rent Estimates, FY2027 | HUD | The rent statistic (replaced ACS B25031 in Phase 2g); county file aggregated to metros with ACS renter-household weights | A scored feature; a work of the US government like the rows above | Yes |
| IPEDS 2024–25 | NCES / Dept. of Education | Student population by metro | A scored feature | Yes |
| Crime Data Explorer | FBI | Offence rates and reporting coverage | Displayed on metro pages with the FBI's own comparability caveat; **never** part of any ranking | Yes, as context |
| Cartographic boundary file (state, 1:20M) | Census Bureau | State outlines for the locator map | Projected at build time into static geometry | Yes, as drawings |
| **City and stat-page photographs** | Wikipedia / Wikimedia Commons contributors | One lead photograph per city page and per stat page | Displayed unmodified with per-image attribution; licences read from the Commons API and restricted to public domain, CC0, CC-BY and CC-BY-SA; per-image manifest (source, author, licence, deed link, retrieval date, hash) at `results/phase2e/city_images.csv` | Yes — **the site's first third-party shipped assets; needs counsel's read before launch** |
| **Home-page hero photograph** | Wikimedia Commons (Carol M. Highsmith, *View of the Burlington Marketplace*, 2017) | The one photograph on the home page | Sourced through the same pipeline and licence gate as the city photographs but held to a stricter bar: **public domain / CC0 only**, because the hero renders as a cropped band and a crop of a CC-BY-SA image would be an adaptation carrying ShareAlike. Licence read live from the Commons API (public domain — the photographer's Library of Congress dedication); attribution rendered beneath the band and bound to the file by SHA-256, so a swapped image cannot wear this credit; manifest row at `results/phase2f/hero_image.csv` | Yes — same posture as the city photographs; **include in counsel's read** |

Note for question 1: we obtain some of this through the Census Bureau's API (which has its
own terms of service, attached) and some by downloading bulk files from the Bureau's public
file server. We would like to know whether those two routes carry different obligations.

**Group 2 — planned for a later release.**

| Source | Publisher | Licence as we read it | Intended use |
|---|---|---|---|
| Overture Places | Overture Maps Foundation | Permissive, attribution required | Venue counts |
| Foursquare OS Places | Foursquare | Apache 2.0, NOTICE must be preserved | Venue counts, merged with the above |
| Cooperative Election Study | Harvard Dataverse | CC0 1.0 (public domain dedication) | The religion estimate |

**Group 3 — read during the build, never published.** Three sources. The two religion
sources forbid redistribution, and one states it is not for marketing purposes; we are not
seeking permission from either, and neither is in the build yet. The third, a Pew Research
Center table, is in the build today. The arrangement is the same for all three: read them
during the build, compare them against our own estimates as a quality check that can fail
the build, and write no value derived from them into the published file. Question 4 asks
whether that satisfies their terms.

| Source | Publisher | Status |
|---|---|---|
| 2020 US Religion Census | ASARB | Planned |
| American Values Atlas county estimates | PRRI | Planned |
| "Intermarriage across the U.S. by metro area" — the share of newlyweds married to someone of a different race or ethnicity, 2011–2015, for the nation and the 124 largest metro areas | Pew Research Center | In the build now |

*The Pew table, in detail.* Obtained on 16 September 2026 from the data endpoint behind
Pew's published interactive feature of 18 May 2017
(`https://www.pewresearch.org/wp-json/prc-api/v2/interactive?slug=intermarriage-map`) and
saved as a small text file (`results/reference/pew_intermarriage_2015.csv`, 124 metros plus
a national row) whose header records the source, the date and Pew's copyright. It is used
in two ways, both at build time. First, when the pairing pattern behind the
chances-of-matching figure is fitted, each metro is left out in turn, its intermarriage
rate is predicted from the pattern plus its own population mix, and the predictions are
compared with Pew's published rates — a check that the pattern captures something local
rather than restating national averages. Second, the build's validation step re-reads that
recorded comparison and reports it. It is not used to choose between versions of the
pattern (a recorded decision), it is never scored, and no value derived from it enters the
published file: we verified this on the current build (`f20cb02c3af8`) by inspecting the
published data file, its manifest and the pairing-pattern file, none of which carries any
field traced to the table. On licence machinery, one honest qualification. The assertion
that enforces build-only use works by tracing each published field to the data source that
fed it, and it can only see sources that flow through our data adapters. The Pew table is
read directly by the fitting and validation scripts, outside any adapter, so that assertion
could not by itself have caught a leak. Two things now cover it: the typed licence field
carries the table marked non-shippable, so any published field ever traced to it fails the
build; and a second, specific check inspects the published files for anything derived from
the table and fails validation if it finds any. Our reading is that this is a factual
reference used with attribution; Pew's terms page is attached for your read.

**Group 4 — considered and excluded**, on our own reading of their terms, listed so you can
tell us if we have been more conservative than necessary: Yelp Fusion (forbids caching
beyond 24 hours and building a competing listings database), Walk Score (forbids storing
scores without written approval), Pew Religious Landscape restricted file (academic,
non-commercial), General Social Survey sensitive files (faculty-gated, mandatory
destruction, no AI input).

**Group 5 — wanted, but not used pending your advice** (question 5): Zillow Research and
Redfin Data Center housing series, and the Opportunity Insights Social Capital Atlas. All
three are widely used commercially; none publishes an explicit commercial grant we could
find. We have built without them.

## Part C — Questions

1. **Federal sources.** Can you confirm there is no licensing obstacle to commercial use of
   each Group 1 source, and specify the attribution or disclaimer language each requires?
   We know HUD requires a "not endorsed or certified by HUD User" disclaimer if we use HUD
   data; are there equivalents we have missed? Do the Census API terms of service impose
   obligations beyond those attaching to the same data downloaded as bulk files?

2. **Personalised rankings that use race or ethnicity.** This is our most important
   question, and the feature has grown since we first drafted it. Race and ethnicity now
   enter the ranking in two distinct ways. (a) *As a filter*: a visitor can tick any of the
   eight groups, and the site counts only those groups in the pool, as before. (b) *Inside
   the chances-of-matching figure*: the figure is built from the observed rates at which
   couples in the Census survey pair within and across racial and ethnic groups, by sex and,
   since 24 September, varying with education. Two things follow. A visitor who gives their
   own race or ethnicity (optional) is ranked by that group's observed pairing pattern, so
   two visitors identical in every other respect can see different figures and a different
   order of cities for the same search. A visitor who gives nothing is ranked by the average
   of those patterns across all groups, so the pairing rates between groups shape everyone's
   ranking to some degree. The page describes this in plain words beside the figure and on
   the methodology page (Part A) and carries no separate caveat for race, by design. What is
   our exposure on each use — fair-housing advertising rules, state consumer-protection law,
   discrimination law as it applies to a statistical service, or anything else we have not
   thought of? Are the guardrails described in Part A adequate for both, and what would you
   add or require? We would rather change the design now than add a disclaimer later.

3. **Rendered pages versus data distribution.** We publish no API deliberately. Our
   reasoning is that a rendered page is a work *produced from* data, whereas an API
   *distributes* the data itself, and that several ambiguous sources are comfortable with
   the former and not the latter. Is that distinction sound as a matter of licence
   interpretation? Does it materially reduce our exposure, and would opening a public API
   later require this review to be redone?

4. **Build-time-only use.** Does the Group 3 arrangement — read during the build, used as a
   comparison, never written into the published file, enforced by an automated check —
   satisfy terms that forbid redistribution and reposting and state that the data are not
   for marketing purposes? Does the same arrangement satisfy Pew's terms for the
   intermarriage table, which is in the build today and is the only source we read that is
   neither a US government work nor a Commons image?

5. **Group 5 sources.** What would we need in order to use Zillow, Redfin or Opportunity
   Insights data? Would publishing only a derived index, with attribution and without their
   underlying values, be sufficient?

6. **Attribution mechanics for Group 2.** What exactly must we display for Overture and for
   Foursquare OS Places, and where on the site must it appear?

7. **Name and domain.** Can we use the name "Dating Stats Atlas" and register the matching
   domain? Any obvious conflicts?

8. **Site policies.** Given no accounts, no server-side record of visitors, and the
   browser-side storage described in Part A, what do we need by way of a privacy policy and
   terms of use? We had wanted to state plainly that we do not store visitors' search
   preferences. That is true of our servers and not of the visitor's browser, where the
   search lives in the page address and in a cookie; we want wording that is accurate and
   safe to make, and question 9 covers the cookie itself.

9. **A visitor's own race or ethnicity in the URL and the cookie.** When a visitor chooses
   to give their race or ethnicity (optional, with "Prefer not to say"), it is carried as a
   parameter in the page address, in any link they copy or share, and in the first-party
   preferences cookie described in Part A, which lives for about 180 days and is sent with
   every request to our site. Several state privacy laws treat racial or ethnic origin as
   sensitive personal data with consent, notice or opt-out requirements, and some treat
   cookies as tracking. Does any of that reach a site with no accounts, no server-side
   storage and a single first-party convenience cookie? Does the cookie need consent or a
   banner? Would we be better placed if the cookie never carried the two optional "about
   you" items, holding those only in the URL, or if it were dropped altogether? We can
   change this design cheaply before launch.

## Part D — Attachments

Saved copies of each source's licence or terms page, with the retrieval date in each
filename, in `attachments/` — including Pew Research Center's terms and conditions page for
the Group 3 table.
