# Dating Stats Atlas — data licensing and publication review

**Prepared for counsel · 12 September 2026 · Nathan, sole founder**

## What we are asking for

A written memo covering (a) whether each data source listed in Part B may be used as
described, and on what conditions, and (b) the two analysis questions in Part C that we
cannot answer ourselves — our exposure on personalised rankings that include a
race/ethnicity filter, and whether the distinction we draw between publishing a rendered
page and distributing data holds up.

A per-source table of **yes / no / yes-with-conditions**, plus required attribution or
disclaimer language, is the most useful form for us: our build system has a typed licence
field on every data source and refuses to ship if a source marked non-shippable reaches the
published artifact, so your answers get encoded and enforced automatically.

We are **not** asking about corporate structure, employment, tax, or fundraising.

Attached: dated copies of each source's licence or terms page, saved on the date shown in
each filename.

## Part A — The product, in one page

**What it is.** A pre-launch website that estimates, for one person's stated preferences,
how many compatible potential partners live in each US metropolitan area, how many other
people are competing for them, and what living there costs — then ranks the metro areas
accordingly. It is a statistical reference tool, not a dating app: there are no profiles, no
messaging, and no other users to meet.

**Where the numbers come from.** Almost entirely from US federal statistical agencies,
chiefly the Census Bureau's American Community Survey public-use microdata — anonymised
individual survey records, published by the Bureau for exactly this kind of analysis, with
no names, addresses, or identifying detail. We aggregate those records to metropolitan-area
population estimates. Nothing we publish describes an identifiable person.

**What we collect from visitors: nothing.** At launch there are no accounts, no login and no
personal information. A visitor's preferences live in the page URL and are never stored.

**Aggregate only, with suppression.** Every figure displayed is a population estimate for a
metro area of at least 250,000 people. Where the underlying sample is too small to support
an estimate — fewer than 100 survey respondents — we suppress the result and say so rather
than publishing a number.

**Build time versus serve time.** A build process reads the source data and produces a
fixed, immutable data file. The website reads only that file. Some sources are read **only
during the build**, used as a quality check, and never contribute any value to the published
file. This separation is enforced by an automated assertion that fails the build, not by
staff discipline.

**No public API.** The site renders pages. There is no data feed, no bulk download and no
documented public endpoint — the ranking endpoint is same-origin and undocumented. This is a
deliberate decision (see question 3).

**Identity filters.** A visitor may optionally filter by race and ethnicity, using the eight
standard categories derived from Census variables. Our own guardrails: the filter is off by
default; we publish no page or headline of the form "best cities to meet [group] women";
metro pages describe population composition as demography; and whenever the filter is on we
display alongside it the observed rate at which people of that group partner outside it,
computed from the same public data, so the filter reads as the visitor's own preference
rather than a boundary. A later release will add a religion estimate, modelled from a public
survey and labelled as modelled with a wider stated uncertainty.

**Status and intent.** Pre-launch, no public URL, no revenue. Intended to become a
commercial product; business model not yet decided.

## Part B — Data sources

**Group 1 — federal sources that will ship at launch.** Our understanding is that these are
US government works, usable commercially with attribution. Question 1 asks you to confirm
that and to specify required attribution or disclaimer language.

| Source | Publisher | Provides | How used | Reaches the site? |
|---|---|---|---|---|
| ACS 5-year public-use microdata (PUMS), 2020–2024 | Census Bureau | The core population estimates | Aggregated into our data file | Yes, as aggregates |
| ACS 5-year summary tables | Census Bureau | Median rent, group-quarters share, calibration totals | Context features; accuracy checks | Yes |
| 2020 Census DHC (tables P1, P18) | Census Bureau | Tract-level population and group-quarters counts | Geographic allocation weights | Indirectly, via weights |
| 2020 Census tract-to-PUMA relationship file | Census Bureau | Geographic crosswalk | Geographic allocation | Indirectly |
| OMB Bulletin 23-01 metro delineation | OMB | Which counties form each metro area | Defines the geography | Yes, as names |
| Regional Price Parities | Bureau of Economic Analysis | Cost-of-living deflator | A scored feature | Yes |
| County Business Patterns | Census Bureau | Venue and establishment counts by industry | A scored feature | Yes |
| Quarterly Census of Employment and Wages | Bureau of Labor Statistics | Cross-check on the above | Accuracy check | No — check only |
| Smart Location Database v3.0 | EPA | Street-network walkability measures | A scored feature | Yes |
| Climate Normals 1991–2020 | NOAA | Pleasant-day counts | A scored feature | Yes |
| IPEDS 2024–25 | NCES / Dept. of Education | Student population by metro | A scored feature | Yes |
| Crime Data Explorer | FBI | Offence rates | Displayed on metro pages with the FBI's own comparability caveat; **never** part of any ranking | Yes, as context |

Note for question 1: we obtain some of this through the Census Bureau's API (which has its
own terms of service, attached) and some by downloading bulk files from the Bureau's public
file server. We would like to know whether those two routes carry different obligations.

**Group 2 — planned for a later release.**

| Source | Publisher | Licence as we read it | Intended use |
|---|---|---|---|
| Overture Places | Overture Maps Foundation | Permissive, attribution required | Venue counts |
| Foursquare OS Places | Foursquare | Apache 2.0, NOTICE must be preserved | Venue counts, merged with the above |
| Cooperative Election Study | Harvard Dataverse | CC0 1.0 (public domain dedication) | The religion estimate |

**Group 3 — read during the build, never published.** Both forbid redistribution; one states
it is not for marketing purposes. We are not seeking permission from either. Our plan is to
read them during the build, compare them against our own modelled religion estimates as a
quality check that can fail the build, and write no value derived from them into the
published file. Question 4 asks whether that satisfies their terms.

| Source | Publisher |
|---|---|
| 2020 US Religion Census | ASARB |
| American Values Atlas county estimates | PRRI |

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

2. **Personalised rankings with a race or ethnicity filter.** This is our most important
   question. A visitor can filter by race and ethnicity, and the site then ranks metro areas
   for them personally, using public Census data. What is our exposure — fair-housing
   advertising rules, state consumer-protection law, or anything else we have not thought
   of? Are the guardrails described in Part A adequate, and what would you add or require?
   We would rather change the design now than add a disclaimer later.

3. **Rendered pages versus data distribution.** We publish no API deliberately. Our
   reasoning is that a rendered page is a work *produced from* data, whereas an API
   *distributes* the data itself, and that several ambiguous sources are comfortable with
   the former and not the latter. Is that distinction sound as a matter of licence
   interpretation? Does it materially reduce our exposure, and would opening a public API
   later require this review to be redone?

4. **Build-time-only use.** Does the Group 3 arrangement — read during the build, used as a
   comparison, never written into the published file, enforced by an automated check —
   satisfy terms that forbid redistribution and reposting and state that the data are not
   for marketing purposes?

5. **Group 5 sources.** What would we need in order to use Zillow, Redfin or Opportunity
   Insights data? Would publishing only a derived index, with attribution and without their
   underlying values, be sufficient?

6. **Attribution mechanics for Group 2.** What exactly must we display for Overture and for
   Foursquare OS Places, and where on the site must it appear?

7. **Name and domain.** Can we use the name "Dating Stats Atlas" and register the matching
   domain? Any obvious conflicts?

8. **Site policies.** Given no accounts and no personal information collected at launch,
   what do we need by way of a privacy policy and terms of use? We would like to state
   plainly that we do not store visitors' search preferences, and want to be sure that
   statement is accurate and safe to make.

## Part D — Attachments

Saved copies of each source's licence or terms page, with the retrieval date in each
filename, in `attachments/`.
