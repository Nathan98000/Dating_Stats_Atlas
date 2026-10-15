# Phase 8 B: the measurements

All on this Mac (Low Power Mode on, as for `../before/`), against the local production
build on :3400 over the API on :8100 (build d62202fd0280, m4.3.0), with the round-4
review's scripts (`docs/design/review-2026-10-12/measure/`). Like for like with
`../before/`, not with the live site.

After commit B (the trimmed Fraunces, the starting search kept, the 3x phone's 720px
photographs):

- `m1_pages_1440_390.json`, `m1.log`: every page's weight at 1440 and 390 (`m1_pages.mjs`).
- `m2_speed_local.json`, `m2_local.log`: speed, five cold runs per width (`m2_speed.mjs`).

The streaming that was tried and not shipped (R23's suggestion; see PHASE8.md):

- `m2_speed_local_streaming.json`, `m2_local_streaming.log`: the home page streamed,
  straight from Next.
- `m2_speed_compressed_before.json`, `m2_compressed_before.log` and
  `m2_speed_compressed_streaming.json`, `m2_compressed_streaming.log`: before and
  streamed, each through a local Caddy compressing as the VM's does (caddy:2, `encode
  zstd gzip`), since compression decides when a streamed part reaches the phone.
