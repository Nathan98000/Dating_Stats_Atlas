# Counsel packet — what's left for you to do

The packet itself (`counsel_packet.md`, and the PDF/DOCX generated from it by `render.sh`,
which records the method) is written. Three things remain, and they're all mechanical.

## 1. Save the licence pages as dated PDFs (about 30 minutes)

**Done 24 September 2026** — all 17 are in `attachments/`, three of them marked `NONE-FOUND`
(BEA, IPEDS, PRRI); `attachments/MANIFEST.md` lists the pages in each file and how each was saved.
The PDFs stay out of git (third-party pages; the repository is public).

A legal opinion is only good for the terms the lawyer actually read, and terms change. So the
packet attaches a dated snapshot of each one.

**How to save one properly:** open the page in Chrome → ⌘P → set Destination to **Save as
PDF** → open "More settings" and tick **Headers and footers** (this prints the URL and the
date onto the page itself, which is what makes it evidence rather than a screenshot) → save
into `attachments/` using the filename below.

| Source | Where to start | Save as |
|---|---|---|
| Census API terms | https://www.census.gov/data/developers/about/terms-of-service.html | `census-api-terms_2026-09-24.pdf` |
| Census citation policy | census.gov → search "citation and copyright" | `census-citation_2026-09-24.pdf` |
| BLS copyright | https://www.bls.gov/opub/copyright-information.htm | `bls-copyright_2026-09-24.pdf` |
| BEA terms of use | bea.gov → search "terms of use" | `bea-terms_2026-09-24.pdf` |
| EPA Smart Location DB | https://www.epa.gov/smartgrowth/smart-location-mapping | `epa-sld_2026-09-24.pdf` |
| NOAA Climate Normals | ncei.noaa.gov → "US Climate Normals" | `noaa-normals_2026-09-24.pdf` |
| IPEDS / NCES | nces.ed.gov/ipeds → data policy or use terms | `ipeds_2026-09-24.pdf` |
| FBI Crime Data Explorer | https://cde.ucr.cjis.gov | `fbi-cde_2026-09-24.pdf` |
| Overture Places | docs.overturemaps.org → licensing | `overture-licence_2026-09-24.pdf` |
| Foursquare OS Places | docs.foursquare.com → OS Places licence | `foursquare-licence_2026-09-24.pdf` |
| Cooperative Election Study | Harvard Dataverse CES page → terms | `ces-cc0_2026-09-24.pdf` |
| 2020 US Religion Census | usreligioncensus.org → terms / permissions | `religion-census-terms_2026-09-24.pdf` |
| PRRI | prri.org → terms of use | `prri-terms_2026-09-24.pdf` |
| Zillow Research | zillow.com/research/data + Zillow terms of use | `zillow-terms_2026-09-24.pdf` |
| Redfin Data Center | redfin.com/news/data-center | `redfin-terms_2026-09-24.pdf` |
| Opportunity Insights | opportunityinsights.org/data | `opportunity-insights_2026-09-24.pdf` |
| Pew Research Center terms (the intermarriage table, Part B Group 3) | pewresearch.org → "Terms & Conditions" in the site footer, plus the feature page itself (pewresearch.org/social-trends/interactives/intermarriage-across-the-u-s-by-metro-area) | `pew-terms_2026-09-24.pdf` |

Two links are verified live as of today: the Census API terms and the BLS copyright page.
The rest are starting points — save whichever terms, licence or copyright page the site
actually links to, and if a source has none, note that in the filename (e.g.
`bea-terms_NONE-FOUND_2026-09-24.pdf` containing the page you did check). "No terms page
exists" is itself useful information for counsel.

Use today's date in the filenames if you save them today; change it if you do this later.

## 2. Send it

Export `counsel_packet.md` to PDF (already done for you — `counsel_packet.pdf`, regenerated
24 September 2026 by `render.sh`; run it again if you edit the markdown), zip it with the
`attachments/` folder, and send with something like this:

> Subject: Scoped data-licensing review — pre-launch statistics website
>
> Hello — I'm a solo founder building a pre-launch website that ranks US metro areas using
> public Census data. Before I put it online I need a written review of (1) whether each of
> my data sources may be used as I describe, and (2) my exposure on personalised rankings
> that use race and ethnicity — as an optional filter, and inside a figure built from the
> rates at which couples in Census data pair within and across groups.
>
> I've attached a packet: a one-page product description, a table of every source and how
> it's used, nine specific questions, and dated copies of each source's licence terms.
>
> I'm looking for a flat fee for a written memo, not an ongoing engagement. Could you let me
> know whether this is work you take, and what you'd estimate? Happy to answer questions
> first.

Before you agree to anything, confirm four things: a **flat fee** for a defined deliverable
rather than an open hourly meter; a written **engagement letter**; **who** does the work (a
partner or a junior associate); and that they've run a **conflict check**. If the first quote
surprises you, ask two more firms — the spread in this specialty is wide.

## 3. The answers

**Received** (September 2026).

- **Kept private.** The answers live outside the repository and are never
  committed. The gitignore refuses `docs/decisions/counsel_packet/private/`
  and any file whose name contains "counsel" together with "answer" or
  "memo".
- **ADR 0012** (`docs/decisions/0012-data-licensing-what-the-build-commits-to.md`)
  records Nathan's decisions, source by source.
- **The build enforces them.** Phase 4 Stage 3 encodes each source's verdict
  in the typed licence registry (`pipeline/adapters/base.py`, `LicenseTerms`:
  `shippable`, the exact citation string and the conditions), and the build
  fails if a served feature traces to an unshippable source.
