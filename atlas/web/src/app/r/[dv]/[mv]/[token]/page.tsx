import Link from "next/link";
import { apiMeta, apiRank, RankError } from "@/lib/api";
import { decodeToken } from "@/lib/permalink";
import { bodyToPrefs, toSearchParams } from "@/lib/prefs";
import { SiteHeader } from "@/components/chrome";
import { Home } from "@/components/home";

export const dynamic = "force-dynamic";

/** Reproducibility routes survive m2.0.0 even though no permalink renders
 * anywhere: an old link either reproduces exactly under its pins or lands
 * on a plain page offering the same search on the current site — never a
 * silent substitution, and never a version number in the copy (gate 2). */
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
      <Shell title="That link didn't survive the trip">
        <p className="max-w-[60ch] text-[15px] leading-relaxed text-ink-2">
          It looks cut short or altered. Ask whoever sent it for a fresh one,
          or start a search of your own.
        </p>
        <StartOver />
      </Shell>
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
        <SiteHeader />
        <Home meta={meta} initialPrefs={prefs} initialResponse={response} />
      </>
    );
  } catch (e) {
    if (e instanceof RankError && e.status === 409) {
      return (
        <Shell title="This link came from an earlier edition of the site">
          <p className="max-w-[62ch] text-[15px] leading-relaxed text-ink-2">
            The way we count has been improved since it was made, and we
            don&rsquo;t quietly swap new numbers under old links. Run the same
            search on the current site instead — it may rank cities
            differently, and that difference is real.
          </p>
          <p>
            <Link
              href={`/?${qs}`}
              className="inline-flex min-h-[46px] items-center rounded-lg bg-accent px-5 text-[14.5px] font-bold text-white hover:bg-accent-hover"
              data-testid="rerun-current"
            >
              Run this search on the current site
            </Link>
          </p>
        </Shell>
      );
    }
    throw e;
  }
}

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto flex max-w-3xl flex-col gap-4 px-6 pb-16 pt-12 sm:px-12" data-testid="pin-mismatch">
        <h1 className="font-display text-[34px] font-semibold leading-tight">{title}</h1>
        {children}
      </main>
    </>
  );
}

function StartOver() {
  return (
    <p>
      <Link
        href="/"
        className="inline-flex min-h-[46px] items-center rounded-lg bg-accent px-5 text-[14.5px] font-bold text-white hover:bg-accent-hover"
      >
        Start a search
      </Link>
    </p>
  );
}
