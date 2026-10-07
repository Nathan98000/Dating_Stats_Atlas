# Deploy runbook — the site is LIVE at https://dating-stats-atlas.duckdns.org

The answers to the counsel packet have returned and are kept private (never
committed); ADR 0012 records Nathan's decisions and the build encodes them.
This runbook exists so that a deploy is a checklist, not a design session.

**Where it stands (2026-10-03).** Nathan chose Topology C, one Oracle Cloud
Always Free VM, so that the site costs nothing to run (Fly.io's always-on
setup would have been about $17.50 a month). With the "Before launch" list
done, Nathan said to launch on 3 October 2026, and the site opened that day
at https://dating-stats-atlas.duckdns.org (Topology C's launch record).

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
address and no public IPs**. The names are Nathan's choice (2026-10-02):
the site is `dating-stats-atlas` (https://dating-stats-atlas.fly.dev) and
the API `dating-stats-atlas-api`. Fly's app names are shared by every Fly
user, and the first-drafted `atlas-web` and `atlas-api` belong to someone
else.

1. `fly apps create dating-stats-atlas-api && fly apps create dating-stats-atlas`
2. API artifact volume: `fly volumes create atlas_builds -a dating-stats-atlas-api --size 3`
3. Ship the build directory (`atlas/data/builds/<data_version>`) to the
   volume: `fly ssh sftp` or a release command pulling from R2 (the §8.3
   artifact store) — the image never bakes data in.
4. `fly deploy -a dating-stats-atlas-api --config atlas/api/fly.toml --no-public-ips --ha=false`
   (from repo root, `--dockerfile atlas/api/Dockerfile`). Without
   `--no-public-ips` a first deploy allocates public addresses. Allocate
   only the private one: `fly ips allocate-v6 --private -a dating-stats-atlas-api`.
   `--ha=false` keeps one machine on the one volume (a first deploy
   otherwise starts two).
5. `fly deploy -a dating-stats-atlas --config atlas/web/fly.toml` (from repo
   root, `--dockerfile atlas/web/Dockerfile`; a first deploy starts two
   machines unless `--ha=false`). The web app finds the API at
   `http://dating-stats-atlas-api.flycast:8000` (set in its `[env]`). Run
   both deploys from the repository root: flyctl uploads the directory it
   runs in and applies the `.dockerignore` there
   (`results/launch/image_check.json` lists what that sends).
6. Smoke: `fly ssh console -a dating-stats-atlas -C "curl -s http://dating-stats-atlas-api.flycast:8000/v1/health"`,
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

## Topology C — one Oracle Cloud Always Free VM (chosen 2026-10-03)

Nathan's choice, so that the site costs nothing to run: Oracle's Always
Free tier, which never charges unless the account is upgraded, holds one
Arm VM, and the whole site runs on it with Docker Compose
(`atlas/deploy/oracle/`). The two images are the ones Topology A would
ship: the same Dockerfiles and the same deny-by-default `.dockerignore`,
built on the VM. D04 holds by construction. The API publishes no port at
all, so only the web container reaches it, over the compose network. The
web app publishes to the VM's loopback only. Caddy alone faces the
internet and terminates HTTPS.

- **Account and region.** Nathan's Oracle Cloud account, home region
  `us-ashburn-1` (Always Free compute exists only in the home region). The
  CLI signs in with `oci session authenticate --profile-name DEFAULT`, a
  browser login that is Nathan's own; its sessions last an hour.
- **Network.** VCN `dating-stats-atlas-vcn` (10.0.0.0/16), an internet
  gateway, and the public subnet `dating-stats-atlas-subnet`
  (10.0.0.0/24) with its own security list `dating-stats-atlas-sl`: SSH
  (22) and ICMP path-MTU in, and, since the launch, TCP 80 and 443. Docker's
  published ports pass through its own FORWARD rules,
  ahead of the image's iptables REJECT, so the VM's iptables need no
  change.
- **VM.** `dating-stats-atlas`: VM.Standard.A1.Flex, 1 OCPU and 6 GB
  (inside the free 2 OCPU and 12 GB), Ubuntu 24.04 aarch64, a 50 GB boot
  volume, public IP 132.145.205.110, in US-ASHBURN-AD-3 (AD-1 and AD-2 had
  no free capacity). The SSH key is `~/.ssh/dating_stats_atlas_oracle` on
  Nathan's Mac (`ssh dsa-oracle`). Oracle stops an Always Free A1 VM that
  sits idle for a week (its CPU, network and memory all under 20%); the
  site's roughly 2 GB in use keeps memory above that line.
- **Upkeep.** Docker, Compose and buildx come from Ubuntu's packages.
  Unattended security upgrades run, with an automatic reboot at 04:30 UTC
  when one needs it, and every service restarts unless stopped.
- **Address.** `dating-stats-atlas.duckdns.org`. DuckDNS is on the Public
  Suffix List, so Let's Encrypt treats the name as its own. Caddy obtains
  and renews the certificate.
- **Logs.** No access log is configured anywhere. Caddy's default log
  records no visitor address, even for failed or malformed TLS
  connections (tested on the VM on 2026-10-03). Next.js logs no requests,
  and the API's access lines show only the web container's address. Each
  service's log is capped at 2 × 5 MB.

Deploy, from the repository root on Nathan's Mac:

1. The code: `git archive --format=tar <commit> | ssh dsa-oracle 'tar -x -C /srv/atlas/src'`.
2. The photographs, which git does not hold (from the main checkout):
   `rsync -a atlas/web/public/cities atlas/web/public/stats atlas/web/public/hero.jpg dsa-oracle:/srv/atlas/src/atlas/web/public/`.
3. The build, mounted read-only as the API's `BUILD_DIR`:
   `rsync -a atlas/data/builds/<data_version>/ dsa-oracle:/srv/atlas/build/`.
4. On the VM: `cd /srv/atlas/src && docker compose -f atlas/deploy/oracle/compose.yaml up -d --build api web`.
5. Check before the site is open: `ssh -N -L 3300:127.0.0.1:3000 dsa-oracle`,
   then browse http://localhost:3300.
6. Open the site, once: add ingress for TCP 80 and 443 to
   `dating-stats-atlas-sl`, point the DuckDNS name at the IP, then
   `docker compose -f atlas/deploy/oracle/compose.yaml --profile public up -d caddy`.

**New build:** rsync the new build over `/srv/atlas/build` and restart the
api service; the manifest still refuses a model mismatch. **New code:**
steps 1, 2 and 4 again.

**Launch record (2026-10-03, on Nathan's word "launch").** The security
list gained TCP 80 and 443, beside SSH and ICMP path-MTU. Caddy started
under the "public" profile and obtained its certificate through the HTTP-01
challenge: Let's Encrypt (YE2) for `dating-stats-atlas.duckdns.org`, valid
to 1 January 2027 and renewed by Caddy. The VM then served commit
fa90cf3's code: the images were built from 5a0fec1, and fa90cf3 changed
only this runbook. Checked from Nathan's Mac:

- http redirects to https (308), and HTTP/2 is served with
  `Referrer-Policy: no-referrer`;
- every page tried answered 200, in 0.1–1.0 s: home, a search, About us,
  Privacy, Terms, What we measure, compare's landing, the Fairbanks and
  Pittsburgh city pages, a compare of two cities below the floor, and two
  stat pages;
- a browser search through the site's own `/api/rank` answered 200 with 193
  ranked cities, build 2dbd9ebfa7ff, m4.1.0;
- the API stays private: port 8000 is closed from outside, and `/v1/health`
  and `/v1/meta` through the site answer 404;
- the logs hold no visitor's address after that traffic. Caddy's only
  outside addresses are Let's Encrypt's five validation servers answering
  the challenge; the web log holds none, and the API's access lines show
  only the web container (172.18.0.3).

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
- [ ] no public IPs on `dating-stats-atlas-api` (`fly ips list -a dating-stats-atlas-api`)
- [ ] the citations render in About the site, Sources and credits (`/about`; they flow from
      `adapters/base.py` LICENSES through the manifest — a wording change
      is made there, and the build regenerated)

## Before launch — what stays with Nathan

Phase 4 did everything in the repository; these are Nathan's own.

Open for Topology C (2026-10-03):

- [x] **Approve Phase 4d's political-lean wording** (PHASE4D.md §6): the
      definition, the shares text, the bar's labels and its spoken label,
      the sort control and the stat page's source line. Approved by Nathan
      on 2026-10-03 (PHASE4D.md §11).
- [x] **The Privacy page's "Our host" paragraph** named Fly.io. Nathan
      approved the Oracle paragraph on 2026-10-03, and `docs/privacy.md`
      carries it: "The site runs on a server we rent from Oracle Cloud. The
      server keeps no record of your visits — not your IP address, and not
      the pages you look at. Oracle's network carries traffic to and from
      it, and like any network it sees IP addresses, under Oracle's own
      privacy policy." (`results/launch/copy_changes.json`)
- [x] **Claim `dating-stats-atlas.duckdns.org`** at duckdns.org (signing
      in with an existing GitHub or Google login) and point it at
      132.145.205.110. Done by Nathan on 2026-10-03; Cloudflare's and
      Google's resolvers both answer 132.145.205.110.
- [ ] **Optional: Oracle's data-processing terms.** Find the data
      processing agreement within the Oracle Cloud terms Nathan accepted at
      sign-up, and save a dated copy to the counsel packet's attachments,
      as Fly's was.

- [x] **Approve the copy**: the privacy policy text and every new or
      changed sentence, listed old → new in `PHASE4.md` ("Copy for
      Nathan's approval"). Approved for now on 2026-09-29, with PHASE4B.md
      and PHASE4C.md's copy. The three sentences that still named the
      removed race switch (Privacy, and twice on About us) were reworded on
      2026-09-30 at Nathan's request, to "used only if you include it",
      and approved by him; so was nice days' new caption, "days that are
      mild and dry enough to be outside" (`PHASE4.md`, "After the phase").
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
      its own privacy policy. Nathan decided it needs no added sentence
      (2026-09-30). *[Since 2026-10-03 the host is Oracle Cloud (Topology
      C), and the paragraph says so; see the item at the top of this
      list.]*
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
