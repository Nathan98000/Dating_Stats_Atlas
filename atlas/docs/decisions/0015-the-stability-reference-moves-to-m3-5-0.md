# ADR 0015 — The stability reference moves to m3.5.0

Date: 2026-09-25 (after Phase 3d; Nathan's call after reading PHASE3D.md)
Status: accepted. It moves ADR 0011's reference and changes nothing else
in ADR 0011's rule. Every number here is read from
`results/phase3d/gate_controls_m3_5_0.json`, written by
`results/phase3d/gate_controls_m3_5_0.py`, or from
`results/phase3d/validation_report_m3_5_0_adr0015.json`.

## Context

ADR 0011 fixed the rank-stability gate's reference at m3.2.0
(f20cb02c3af8), so that small rises could not pile up release after
release. It says the reference "moves only by Nathan's decision recorded
in an ADR". Phase 3d then scored chances of matching by its value (ADR
0013, V2) and shipped it as m3.5.0 (build 1ebeaa2dcad6). Against m3.2.0,
m3.5.0 reads **0.775**: total wobble 245.1 against 316.2 over the 516
test searches.

That leaves the gate's 10% line far above where the site now is. Against
m3.2.0 the line is 347.8 places, **41.9% above m3.5.0's total**. A later
change could make rankings about 40% shakier than m3.5.0 and still pass,
so the gate could not catch a change that undid value scoring's gains.

## Nathan's decision

Move the ADR 0011 reference to m3.5.0 (build 1ebeaa2dcad6). Against it,
the line sits 10% above today's site (269.6 places).

## What moves, and what does not

- **The reference record** is m3.5.0's per-search record, in the format
  of the m3.2.0 one: `results/phase3d/stability_reference_m3_5_0.json`,
  written by `stability_gate reference` on 1ebeaa2dcad6. It reads 516
  searches scored and 2 skipped, total wobble 245.073, median 0.3645. The
  largest is 3.370, the two searches at the slider's match end. It also
  carries the diagnostics Phase 3d B1 added to every gate record: the
  match-score spread, the steering τ and the scoring rule (V2).
- **It is m3.5.0's own reading.** Search for search, it has the same
  wobble and the same index and replicate hashes as B2's measurement of
  V2 and as the ship's validation record.
- **One constant.** `stability_gate.REFERENCE` names the record, and
  `build.validate` reads it only through that constant. A test holds
  that.
- **The m3.2.0 record stays as history.** It
  (`results/phase3c/stability_reference.json`) and its controls
  (`results/phase3c/gate_controls.json`) stay byte-identical.
  `stability_gate.REFERENCE_M3_2_0` names the record for the scripts that
  read history.
- **ADR 0011's rule is otherwise unchanged:**
  - the wobble definition;
  - the test searches (518, 516 scored);
  - "touched": any search whose index, point or replicate, differs from
    the reference's;
  - the 10% line;
  - the 25% riser flag (findings, not gates);
  - the old overlap share as a soft reading.

## The controls

Both were run before anything else was read against the new reference.

| Control | Reading | Verdict |
|---|---|---|
| The reference against itself (1ebeaa2dcad6 re-measured) | **1.0 exactly**, no search touched | passes, as it must |
| Enlarged noise: every replicate's deviation from the published estimate × 1.5 | **1.496**, all 516 searches touched | fails, as it must |

## The past builds, read against the new reference

This is for the record, not a gate, and nothing past is re-judged. Each
build's stored per-search record is read through
`stability_gate.verdict`: the m3.2.0 reference record, and m3.3.0's and
m3.4.0's validation reports.

| Build | Total wobble | Searches touched | Ratio | Would pass |
|---|---|---|---|---|
| m3.2.0 (f20cb02c3af8) | 316.2 | 516 | 1.290 | no |
| m3.3.0 (ee4f08cf33e1) | 307.1 | 516 | 1.253 | no |
| m3.4.0 (1ebeaa2dcad6, the percentile rank) | 306.7 | none (the same kernel), so all 516 are read | 1.251 | no |

m3.4.0 is m3.5.0 scored the old way: the same kernel and the same index,
with the percentile rank. It reads above 1.10, and that is the point:
going back to percentile scoring would now fail the gate.

## Consequences

- **Kernel changes are now judged against the value-scored build.**
  - A kernel change touches every search, and its total is read against
    m3.5.0's 245.1 instead of m3.2.0's 316.2.
  - The 22.5% of headroom that value scoring created is no longer there
    for a kernel change to spend.
  - A scoring-only change on this kernel touches nothing, so it is read
    over every search, as ADR 0011 says.
- **`build.validate` on 1ebeaa2dcad6.** **Ten of ten hard gates pass.**
  The ADR 0011 gate reads **1.0** against the new reference: nothing
  touched, 245.073 against 245.073
  (`validation_report_m3_5_0_adr0015.json`).
- **Nothing served changed.** There is no version bump, the goldens are
  byte-identical, and the launch config stays at 1ebeaa2dcad6.
- **`stability_gate.py`.**
  - `REFERENCE` is the m3.5.0 record.
  - The `reference` command writes it (or `--out`) and never over an
    existing record.
  - The controls are one function, `controls`, and the `controls`
    command takes `--out`, so neither command can overwrite the Phase 3c
    history.
- **Scripts that read history.** `phase3c_past_readings.py` (Phase 3c's
  readings of m3.0.0 → m3.1.0 → m3.2.0) reads the m3.2.0 record by name.
  A re-run of ADR 0013's selection reads its gate condition against
  m3.5.0.
- **ADR 0011.** Its status line says its reference is now m3.5.0 by this
  ADR; the rest of its text stays as history.
- **The old reference build.** f20cb02c3af8 stayed complete only because
  it was the reference.
  - Nothing in the code, the tests, CI or the web app reads its
    directory.
  - The one-off chain scripts of Phases 3b to 3d that named it have run,
    and their records are committed.
  - Its data files are byte-identical to 1ebeaa2dcad6's.

  It is retired to its manifest, metros and kernel record, keeping
  kernel.npz: the pattern used for ee4f08cf33e1.
