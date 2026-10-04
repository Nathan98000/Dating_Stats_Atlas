# Phase 4e halt: latency p95 over 100 ms (commit C)

The brief's stop condition: "latency p95 exceeds 100 ms". Commit C's build
(63c4e5fa51bf, m4.2.0) measured, with `api/tests/measure_latency.py <build> 400`
on Nathan's Mac, 2026-10-03 ~23:00, back to back:

| run | code / build | p50 ms | p95 ms | load before |
|---|---|---|---|---|
| m4.2.0, run 1 | this branch / 63c4e5fa51bf | 58.31 | 99.06 | 1.90 |
| m4.2.0, run 2 | this branch / 63c4e5fa51bf | 58.48 | **102.05** | 1.59 |
| m4.1.1 (live), run 1 | 6a4bd83 / 2dbd9ebfa7ff | 58.18 | 99.25 | 1.38 |
| m4.1.1 (live), run 2 | 6a4bd83 / 2dbd9ebfa7ff | 58.29 | **100.15** | 1.91 |
| m4.1.0 | a2c62ab / 2dbd9ebfa7ff | 55.65 | 94.72 | 1.86 |

(`latency_m4_2_0_run1.json`, `_run2.json`, `latency_m4_1_1_run1.json`,
`_run2.json`, `latency_m4_1_0.json`.) Phase 4 recorded 54.25 ms for m4.0.0
(results/phase4/latency_m4_0_0.json, load 1.92).

What it says:

- The new nice-day rule costs nothing measurable: it changes one column of
  features.parquet, and m4.2.0 reads the same as the live m4.1.1 (p50 58.3
  vs 58.2-58.3; p95 99-102 vs 99-100).
- The live code already sits at the line on this machine today: m4.1.1
  itself crossed 100 ms on its second run. m4.1.0's code reads ~5 ms
  faster, which points at the m4.1.1 movers-line fix (explain.mover_units /
  mover_sides) as the step that brought it to the line.
- Every run today reads far slower than Phase 4's 54 ms for m4.0.0. The
  Phase 4c, 4d and m4.1.1 releases recorded no latency figure, so whether
  the gap is code added since m4.0.0 or this machine's state today is not
  separated here.

Not done, per the brief (halt and report): no re-run until it passes, no
tuning, no commit C. Done before the halt and passing: every hard gate
(validate 11/11), and the ADR 0011 gate 0.999 (`gate_m4_2_0.json`).

## Investigation (Nathan: "investigate latency first", 2026-10-04)

**Interleaved benchmark.** Each release on its own build, in rotation, four
rounds, 300 requests each (the same seeded request mix), so every version
saw the same machine conditions (`latency_interleaved_lowpower/`):

| version | p95, rounds 1-4 (ms) | p50 (ms) |
|---|---|---|
| m4.0.0 (f4dca83, 5b780e4f2444, its own manifest) | 100.3, 96.9, 98.2, 94.3 | 60.4-61.7 |
| m4.1.0 (a2c62ab, 2dbd9ebfa7ff) | 92.1, 91.2, 92.4, 93.2 | 57.3-57.6 |
| m4.1.1, live (6a4bd83, 2dbd9ebfa7ff) | 98.7, 95.3, 96.1, 94.8 | 59.9-60.5 |
| m4.2.0 (this branch, 63c4e5fa51bf) | 101.0, 97.0, 105.2, 94.4 | 59.5-60.9 |

m4.0.0 — 54.25 ms p95 when Phase 4 shipped it — reads 94-100 ms today. No
release since added the time: every version sits in the same band, m4.1.1
and m4.2.0 within ~2-4 ms of each other (inside the round-to-round spread).

**The environment.** The Python libraries match requirements.lock, which is
unchanged since f4dca83. The Mac reports **Low Power Mode on** (`pmset -g`:
lowpowermode 1, on battery and on AC), running on battery, load 3-6 while
the benchmark ran (Chrome, WindowServer). Low Power Mode caps Apple
Silicon's CPU clocks, which fits every version slowing by the same factor.
Changing it is a system setting: Nathan's to switch.

**Next.** With Low Power Mode off and the Mac on power, re-run the same
interleaved benchmark; the stop condition reads that measurement.

## Resolved (2026-10-04, Nathan switched Low Power Mode off; Mac on AC)

The same interleaved benchmark, Low Power Mode off (`pmset -g`:
lowpowermode 0, AC power), `latency_interleaved_ac/`:

| version | p95, rounds 1-4 (ms) |
|---|---|
| m4.0.0 | 53.9, 55.4, 54.5, 56.0 |
| m4.1.0 | 53.1, 52.6, 53.3, 53.3 |
| m4.1.1 (live) | 55.0, 55.1, 55.2, 55.3 |
| m4.2.0 | 55.4, 55.2, 55.1, 55.3 |

Every release is back at Phase 4's 54 ms; m4.2.0 is within 0.3 ms of the
live m4.1.1. The standard 400-request run for m4.2.0 is
`latency_m4_2_0.json`. The stop condition reads this measurement: p95 is
far under 100 ms, so it clears. The earlier 99-102 ms readings were Low
Power Mode, not code. Note for future measurements: check `pmset -g` first.
