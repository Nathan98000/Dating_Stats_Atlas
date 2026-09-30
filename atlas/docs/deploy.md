# Deploy runbook — configuration committed, NOTHING DEPLOYED

**Do not deploy.** The answers to the counsel packet have returned and are
kept private (never committed); ADR 0012 records Nathan's decisions and the
build encodes them. What still stays with Nathan is the "Before launch" list
below, and no public URL exists until it is done. This runbook exists so
that the deploy is a checklist, not a design session.

## The invariant everything else serves (D04)

The FastAPI process is never public. It has no CORS headers, no public
documentation surface, and — in production — **no public address**. The
browser talks only to the Next.js server, which proxies `/api/rank` and
performs its own server-side calls over a private network. The licensing
posture (a rendered site is a Produced Work; an API is distribution) rests
on this; so does suppression, which is enforceable in a UI and not in a
feed.

## Topology A — everything on Fly.io (preferred)

Two apps in one Fly organization; the API gets a **flycast (private-only)
address and no public IPs**.

1. `fly apps create atlas-api && fly apps create atlas-web`
2. API artifact volume: `fly volumes create atlas_builds -a atlas-api --size 3`
3. Ship the build directory (`atlas/data/builds/<data_version>`) to the
   volume: `fly ssh sftp` or a release command pulling from R2 (the §8.3
   artifact store) — the image never bakes data in.
4. `fly deploy -a atlas-api --config atlas/api/fly.toml` (from repo root,
   `--dockerfile atlas/api/Dockerfile`). Allocate **no** public IPs:
   `fly ips allocate-v6 --private -a atlas-api` only.
5. `fly deploy -a atlas-web --config atlas/web/fly.toml` (from repo root,
   `--dockerfile atlas/web/Dockerfile`). The web app finds the API at
   `http://atlas-api.flycast:8000` (set in its `[env]`). Run both deploys
   from the repository root: flyctl uploads the directory it runs in and
   applies the `.dockerignore` there (`results/launch/image_check.json`
   lists what that sends).
6. Smoke: `fly ssh console -a atlas-web -C "curl -s http://atlas-api.flycast:8000/v1/health"`,
   then the site’s own `/about` (it renders only if `/v1/meta`
   answers).

**Rollback / new build:** put the new `<data_version>` directory on the
volume, flip `BUILD_DIR`, restart the API machines. The manifest is the
contract: an m-version mismatch refuses to boot rather than serving the
wrong model (loader assertion), and with more than one complete build on
the volume the API refuses to guess — `BUILD_DIR` is always explicit.

## Topology B — web on Vercel (fallback)

`atlas/web/vercel.json` is committed. Vercel functions cannot join Fly's
private network, so this topology needs one of:

- a WireGuard tunnel from Vercel's Secure Compute to the API network, or
- the API behind a bearer token (`Authorization` checked in an ASGI
  middleware — not yet written, deliberately: it only exists if this
  topology is chosen), with `ATLAS_API_URL` + `ATLAS_API_TOKEN` set as
  Vercel env vars and the token attached in `src/lib/api.ts`.

Either way the API still has no public *unauthenticated* surface and no
CORS. If neither is acceptable, use Topology A.

## Environment variables

| var | where | meaning |
|---|---|---|
| `BUILD_DIR` | API | absolute path of the ONE build to serve (no guessing) |
| `ATLAS_API_URL` | web | private base URL of the API |

## Pre-deploy checklist

- [ ] every item under "Before launch" (below) done
- [ ] `pytest atlas -q` green; `build.validate <build>` exit 0 on the exact
      artifact being shipped
- [ ] `npm test && npx playwright test` green (CI runs both)
- [ ] `data_version` + `model_version` in `/v1/health` match the artifact
      you shipped
- [ ] no public IPs on `atlas-api` (`fly ips list -a atlas-api`)
- [ ] the citations render in About us, Sources and credits (`/about`; they flow from
      `adapters/base.py` LICENSES through the manifest — a wording change
      is made there, and the build regenerated)

## Before launch — what stays with Nathan

Phase 4 did everything in the repository; these are Nathan's own.

- [x] **Approve the copy**: the privacy policy text and every new or
      changed sentence, listed old → new in `PHASE4.md` ("Copy for
      Nathan's approval"). Approved for now on 2026-09-29, with PHASE4B.md
      and PHASE4C.md's copy. The three sentences that still named the
      removed race switch (Privacy, and twice on About us) were reworded on
      2026-09-30 at Nathan's request, to "used only if you include it"
      (`PHASE4.md`, "After the phase").
- [x] **Terms of use** for the site. Written 2026-09-29 in `docs/terms.md`
      (the `/terms` page, linked from About us) and approved by Nathan for
      now: run by Nathan Nguyen, contact dating.stats.atlas@gmail.com,
      New York law, dated October 1, 2026, the planned launch.
- [x] **Fly.io's data processing agreement.** Signed by Nathan on
      2026-09-30 through Dropbox Sign (Fly.io pre-signs it); the signed
      copy is `docs/decisions/counsel_packet/attachments/fly-dpa_2026-09-30.pdf`
      (out of git), listed in the attachments' `MANIFEST.md`.
- [x] **Confirming that Fly's edge does not log query strings** (search
      settings travel in the query). Fly.io support answered Nathan on
      2026-09-30: a request is logged in detail only when the client sends
      a special debugging header, and then the query string's values are
      redacted (`foo=<redacted>`); when something fails between Fly's proxy
      and a machine, the request's path, without its query, goes to a
      system log; no log holds request headers or cookies. Those logs are
      kept by size, about two to three weeks at present, seen by Fly's
      engineering and support staff, and can't be turned off. `fly logs`
      is separate: it carries what the two apps print. The web server logs
      no requests, and the API's access lines read `POST /v1/rank` from
      the web app's private address (the search travels in the request
      body), so neither holds a search or a visitor's address
      (`results/launch/image_check.json`, "run_together"). The
      Privacy page's "Our host" paragraph still holds: it says Fly.io
      keeps technical logs such as IP addresses and page addresses, under
      its own privacy policy.
- [x] **Look inside both images before the first deploy**: `fly deploy`
      uploads the build context (the repository root) to a remote builder.
      Since Phase 4 a deny-by-default `.dockerignore` keeps the data, the
      results, private folders and key files out of it, and the API image
      copies only `atlas/api` and `atlas/model`; build both images locally
      once and list their files to confirm. Done 2026-09-30
      (`results/launch/image_check.py`, `image_check.json`: clean). The
      upload is 477 files, 365 of them the city photographs; the API image
      adds only its 15 files, each byte-identical to the repository's; the
      web image holds the built site, its packages, the four pages' texts
      (identical to `docs/`) and the public images. No data, results,
      pipeline, decision records, git, private folder, key file, secret,
      API key value, personal detail or anything of Pew's table in any of
      them. Run together on a private network with the test build, the two
      images answer every page, and neither app's log holds a search or a
      visitor's address. Built here for linux/arm64; Fly builds
      linux/amd64, which changes compiled packages, not which files go in.
- [x] **A trademark clearance search** on the name. Done by Nathan: no
      trademark for "Dating Stats Atlas" (recorded 2026-09-30).
- [x] **HUD's terms**: save the dated snapshot of HUD's terms page to
      `docs/decisions/counsel_packet/attachments/`, as the other sources'
      are. Saved 2026-09-30 as `hud-terms_2026-09-30.pdf` (the rent
      dataset page, HUD User's API terms and its site disclaimer), listed
      in the attachments' `MANIFEST.md`.
- [ ] **Optional: an email to ASARB** (the 2020 US Religion Census)
      confirming commercial use, before that source is ever started.
- [ ] **Foursquare's Places Portal terms**, when venues are un-deferred
      (ADR 0012).
- [x] **The force-push and the GitHub purge from Phase 4 Stage 1**: re-add
      `origin`, force-push every branch and tag, ask GitHub Support to purge
      cached views of the old commits, and check for forks — the exact
      commands are in `PHASE4.md` §1. Done 2026-09-29 another way: GitHub
      Support's form had no fitting category, so Nathan deleted the
      repository and recreated it clean; the old commits no longer resolve,
      and the new repository has no forks (whether the old one had any
      before it was deleted is not recorded).
