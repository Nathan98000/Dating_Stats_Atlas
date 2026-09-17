# Deploy runbook — configuration committed, NOTHING DEPLOYED

**Do not deploy.** The licensing review in `docs/decisions/counsel_packet`
has not returned, and no public URL exists until it does. This runbook
exists so that when it returns, the deploy is a checklist, not a design
session.

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
5. `fly deploy -a atlas-web --config atlas/web/fly.toml`. The web app finds
   the API at `http://atlas-api.flycast:8000` (set in its `[env]`).
6. Smoke: `fly ssh console -a atlas-web -C "curl -s http://atlas-api.flycast:8000/v1/health"`,
   then the site’s own `/how-it-works` (it renders only if `/v1/meta`
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
CORS. If neither is acceptable to counsel, use Topology A.

## Environment variables

| var | where | meaning |
|---|---|---|
| `BUILD_DIR` | API | absolute path of the ONE build to serve (no guessing) |
| `ATLAS_API_URL` | web | private base URL of the API |

## Pre-deploy checklist

- [ ] counsel review returned and archived in `docs/decisions/`
- [ ] `pytest atlas -q` green; `build.validate <build>` exit 0 on the exact
      artifact being shipped
- [ ] `npm test && npx playwright test` green (CI runs both)
- [ ] `data_version` + `model_version` in `/v1/health` match the artifact
      you shipped
- [ ] no public IPs on `atlas-api` (`fly ips list -a atlas-api`)
- [ ] attribution strings render on `/how-it-works` (they flow from
      `adapters/base.py` LICENSES through the manifest — if counsel changed
      wording, it changed there and the build was regenerated)
