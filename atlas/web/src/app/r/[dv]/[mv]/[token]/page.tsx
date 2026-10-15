import Link from "next/link";
import { apiMeta, apiRank, RankError } from "@/lib/api";
import { decodeToken } from "@/lib/permalink";
import { bodyToPrefs, describeSearchShort, toSearchParams } from "@/lib/prefs";
import { CHROME, HOME_OG_IMAGE, pageMetadata, pageTitle, resultsTitle } from "@/lib/chrome";
import { fill } from "@/lib/results";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { Home } from "@/components/home";
import { cardPhotos } from "@/lib/city-photos";

export const dynamic = "force-dynamic";

/** Phase 6 (F31): a permalink's own title and link preview — the results
 * heading of the search it carries, its own URL, the home description and
 * image. A token that doesn't decode keeps the site's. */
export async function generateMetadata({ params }: { params: Promise<{ dv: string; mv: string; token: string }> }) {
  const { dv, mv, token } = await params;
  const meta = await apiMeta();
  const ps = meta.policy_strings;
  try {
    const prefs = bodyToPrefs(decodeToken(token));
    const heading = fill(prefs.sort === "worst_first" ? ps.results_heading_worst : ps.results_heading_best,
      describeSearchShort(prefs));
    return pageMetadata(resultsTitle(ps, heading), ps.home_subtitle, `/r/${dv}/${mv}/${token}`, HOME_OG_IMAGE);
  } catch {
    return pageMetadata(pageTitle(), ps.home_subtitle, `/r/${dv}/${mv}/${token}`, HOME_OG_IMAGE);
  }
}

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
      <Shell title={CHROME.link_broken_title}>
        <p className="max-w-[60ch] text-body leading-relaxed text-ink-2">
          {CHROME.link_broken_body}
        </p>
        <StartOver />
      </Shell>
    );
  }
  const prefs = bodyToPrefs(body);
  const qs = toSearchParams(prefs).toString();
  try {
    const meta = await apiMeta();
    if (mv !== meta.model_version) {
      // decide by the pin, not by error ordering: an older token may
      // carry fields the current contract refuses (m2.0.0's size_vs_odds
      // would 422 before the version check could 409), and either way
      // the honest answer is the earlier-edition page
      throw new RankError(409, "model_version pin predates this site");
    }
    const response = await apiRank(
      { ...body, data_version: dv, model_version: mv });
    return (
      <>
        <SiteHeader />
        <Home meta={meta} initialPrefs={prefs} initialResponse={response} photos={cardPhotos()} />
      </>
    );
  } catch (e) {
    if (e instanceof RankError && e.status === 409) {
      return (
        <Shell title={CHROME.link_old_title}>
          <p className="max-w-[62ch] text-body leading-relaxed text-ink-2">
            {CHROME.link_old_body}
          </p>
          <p>
            <Link
              href={`/?${qs}`}
              className="inline-flex min-h-11 items-center rounded-md bg-accent px-5 text-body-sm font-bold text-white hover:bg-accent-hover"
              data-testid="rerun-current"
            >
              {CHROME.link_old_action}
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
        <h1 className="font-display text-h2 font-semibold leading-tight">{title}</h1>
        {children}
      </main>
      <SiteFooter />
    </>
  );
}

function StartOver() {
  return (
    <p>
      <Link
        href="/"
        className="inline-flex min-h-11 items-center rounded-md bg-accent px-5 text-body-sm font-bold text-white hover:bg-accent-hover"
      >
        {CHROME.link_start}
      </Link>
    </p>
  );
}
