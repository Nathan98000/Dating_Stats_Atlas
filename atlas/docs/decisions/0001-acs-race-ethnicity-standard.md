# ADR 0001 — ACS race and ethnicity standard: 1997, deferred rather than withdrawn

**Status:** verified 2026-09-12. Closes proposal §13.3 pre-flight item 2 ("Confirm the OMB
standards reversal from the primary information-collection record before any roadmap or
methodology copy asserts it").

## Question

Proposal §12.1 asserts that the Census Bureau's timeline for implementing the 2024 revision
of OMB Statistical Policy Directive No. 15 (combined race-and-ethnicity question, MENA
category) "appears to have been withdrawn in 2026 in favour of retaining the 1997
standards," and requires that the claim be confirmed against a primary record before any
published copy depends on it.

## Finding

The 2024 standards are **deferred, not withdrawn.** The 2027 ACS and PRCS will collect under
the 1997 standards; the Bureau states it is continuing to develop implementation plans for
the 2024 standards during an extended deadline. No collection year is announced.

Verbatim from the approved Supporting Statement A, where it appears four times — including
as the Bureau's response to the 83 public comments supporting inclusion of the updated
question:

> In light of OMB's March 27, 2026 announcement of a one-year extension to submit an Action
> Plan for compliance with the updates to Statistical Policy Directive No. 15, Standards for
> Maintaining, Collecting, and Presenting Federal Data on Race and Ethnicity, the Census
> Bureau will use the 1997 standards in the American Community Survey and the Puerto Rico
> Community Survey, and will use the delayed deadline to continue to develop implementation
> plans for the 2024 standards.

What the record does **not** say: that the plan was cancelled, scrapped, or withdrawn. The
ICR history for OMB control number 0607-0810 carries no withdrawn package in 2025 or 2026
(the only "Withdrawn and continue" entry is 202410-0607-003, October 2024). Secondary
reporting characterising this as a cancellation overstates the record.

## Primary record

| Field | Value |
|---|---|
| OMB control number | 0607-0810 (The American Community Survey and the Puerto Rico Community Survey) |
| ICR reference number | 202605-0607-002 |
| Type of request | Revision of currently approved collection |
| Received in OIRA | 2026-05-14 |
| OIRA conclusion action | **Approved with change**, 2026-07-09 |
| Expiration date | 2029-07-31 (previously approved: 2027-06-30) |
| Terms of Clearance | none — the field carries only the burden table |
| Public comments | 91 received on the proposed revisions (83 supporting inclusion of the updated question); comment period closed 2026-02-17 |

Accessed 2026-09-12:

- ICR cover sheet — https://www.reginfo.gov/public/do/PRAViewICR?ref_nbr=202605-0607-002
- ICR history for 0607-0810 — https://www.reginfo.gov/public/do/PRAOMBHistory?ombControlNumber=0607-0810
- Package documents — https://www.reginfo.gov/public/do/PRAViewDocument?ref_nbr=202605-0607-002
- The December 2025 notice that proposed the 2027 change — Federal Register 2025-23329, published 2025-12-19

## Evidence held

`icr_0607-0810_202605_supporting_statement_a_rev_2026-06-18.pdf`
(as served by reginfo.gov: "2027 ACS SupportingStatement A_revised 6-18-2026", uploaded to
the ICR package 2026-06-23)

- bytes: 564,956
- sha256: `b290adb4343d8355fb84b582b5133576a05771371902390650a4ca4a0ed185c6`
- retrieved: 2026-09-12

## Consequences

**For the build: none.** The cube's race and ethnicity axis is derived from `RAC1P` and
`HISP` in the ACS 2020–2024 5-year PUMS, which are 1997-standard variables. §12.1's
instruction — build for the 1997 framework, write no migration path around a specific
arrival year — stands unchanged. A future instrument change would arrive as a new
`data_version` with its own calibration, not as a reinterpretation of this one.

**For published copy:** the approved sentence is

> The 2020–2024 5-year file is collected and tabulated under OMB's 1997 race and ethnicity
> standards, and this build works within that framework. The Census Bureau has deferred the
> 2024 SPD 15 standards on the ACS pending an implementation Action Plan, with no announced
> collection year. (Information-collection record checked 12 September 2026.)

Do **not** write that the change was withdrawn, scrapped or cancelled — the record does not
support it, and the Bureau says implementation planning is ongoing.

## Re-check trigger

OMB's extension runs one year from the 2026-03-27 announcement. Re-read the ICR history for
0607-0810 after Q1 2027, and on any new ICR for that control number. If a future ACS
instrument adopts the combined question, the affected products are the race axis definition
and every piece of methodology copy that names the standard.
