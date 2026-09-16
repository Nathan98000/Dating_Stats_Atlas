import Link from "next/link";
import { apiMeta, apiRank, RankError } from "@/lib/api";
import { decodeToken } from "@/lib/permalink";
import { bodyToPrefs, toSearchParams } from "@/lib/prefs";
import { Explorer } from "@/components/explorer";
import { Masthead } from "@/components/masthead";

export const dynamic = "force-dynamic";

/** Permalinks (§5.4/§10.1): /r/<data_version>/<model_version>/<token>
 * reproduces a ranking under both version pins. A pin mismatch is a REAL
 * page — the API's 409 means this process cannot reproduce that ranking,
 * and serving today's numbers under yesterday's link would be a silent
 * substitution. The page says so and offers the same preferences under the
 * current build instead. */
export default async function PermalinkPage({
  params,
}: {
  params: Promise<{ dv: string; mv: string; token: string }>;
}) {
  const { dv, mv, token } = await params;
  let body;
  try {
    body = decodeToken(token);
  } catch {
    return (
      <MismatchShell title="This link is not a valid permalink">
        <p className="max-w-[60ch] text-sm text-ink-2">
          The encoded preferences could not be read. If someone sent it to
          you, ask for a fresh link — every ranking page shows one.
        </p>
      </MismatchShell>
    );
  }
  const prefs = bodyToPrefs(body);
  const qs = toSearchParams(prefs).toString();
  try {
    const [meta, response] = await Promise.all([
      apiMeta(),
      apiRank({ ...body, data_version: dv, model_version: mv }),
    ]);
    return (
      <>
        <Masthead
          dataVersion={meta.data_version}
          modelVersion={meta.model_version}
          brandAsH1
        />
        <div className="mx-auto max-w-6xl px-5 pb-4">
          <p className="border-l-2 border-pass pl-3 text-sm text-ink-2">
            Reproduced exactly under its pins: data{" "}
            <span className="num">{dv}</span>, model <span className="num">{mv}</span>.
          </p>
        </div>
        <Explorer meta={meta} initialPrefs={prefs} initialResponse={response} />
      </>
    );
  } catch (e) {
    if (e instanceof RankError && e.status === 409) {
      return (
        <MismatchShell title="This link was made under a different build">
          <p className="max-w-[60ch] text-sm text-ink-2">
            It pins data <span className="num">{dv}</span> and model{" "}
            <span className="num">{mv}</span>, which this server no longer
            serves ({e.detail}). Rankings are never silently substituted
            across builds — when a metro moves between versions, the version
            pin is how you can tell why.
          </p>
          <p className="mt-3 text-sm">
            <Link
              href={`/?${qs}`}
              className="border border-accent px-3 py-1.5 font-semibold text-accent"
              data-testid="rerun-current"
            >
              Re-run these preferences under the current build
            </Link>
          </p>
        </MismatchShell>
      );
    }
    throw e;
  }
}

async function MismatchShell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  let versions = { data_version: "unavailable", model_version: "unavailable" };
  try {
    const meta = await apiMeta();
    versions = meta;
  } catch {
    /* the shell renders without version pins */
  }
  return (
    <>
      <Masthead dataVersion={versions.data_version} modelVersion={versions.model_version} />
      <main id="main" className="mx-auto max-w-4xl px-5" data-testid="pin-mismatch">
        <h1 className="font-serif text-3xl font-semibold tracking-tight">{title}</h1>
        <div className="mt-3">{children}</div>
        <p className="mt-6 text-xs text-ink-3">
          Why two pins:{" "}
          <Link href="/methodology#versions" className="text-accent underline underline-offset-2">
            a ranking can change for two unrelated reasons
          </Link>
          .
        </p>
      </main>
    </>
  );
}
