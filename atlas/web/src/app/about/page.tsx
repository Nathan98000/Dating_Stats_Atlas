import { promises as fs } from "fs";
import fsSync from "fs";
import path from "path";
import { marked } from "marked";
import { apiMeta } from "@/lib/api";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { CHROME, pageMetadata, pageTitle, SITE_DESCRIPTION } from "@/lib/chrome";
import cityImages from "@/data/city-images.json";
import statImages from "@/data/stat-images.json";

export const dynamic = "force-dynamic";

export function generateMetadata() {
  return pageMetadata(pageTitle(CHROME.about_title), SITE_DESCRIPTION, "/about");
}

/** One photograph's credit, as the licence asks: the title, the author,
 * the licence (linked to its deed), a link to the source file, and
 * "cropped" where the site shows it cropped. */
interface PhotoCredit {
  file: string;
  title?: string | null;
  author: string | null;
  license: string;
  license_url: string | null;
  source_url: string;
  cropped?: boolean;
}

/** Only photographs the site actually shows are credited: the file must be
 * on disk where its page reads it (the same test the pages apply). */
function shipped(dir: string, img: PhotoCredit | undefined): img is PhotoCredit {
  return Boolean(img && fsSync.existsSync(path.join(process.cwd(), "public", dir, img.file)));
}

/** About us (m4.0.0, Nathan's decisions 7-9; "How it works" until then):
 * the privacy page and the terms of use linked near the top, the
 * plain-language account of how the numbers are made (docs/methodology.md,
 * synced at build), and the ONE place every source and photograph credit
 * lives — Sources and credits: the data citations and notices from the
 * typed licence registry through the manifest, and each photograph's
 * credit from the committed image manifests. After Phase 4e (Nathan,
 * 2026-10-06): What we measure and About crime data are no longer buttons
 * here — the account links them in its own words (its last section, and
 * the Reported crime row of its sources table); the data citations
 * collapse like the photographs. Phase 5: the home page photograph's
 * credit left with its band. The Census API notice
 * folds into the collapsed list with the citations it belongs to (Nathan,
 * 2026-10-06; ADR 0012: it appears with the citations). Every label comes
 * from the registry. */
export default async function AboutPage() {
  const meta = await apiMeta();
  const policy = meta.policy_strings;
  const mdPath = path.join(process.cwd(), "content", "methodology.md");
  const md = await fs.readFile(mdPath, "utf-8");
  const html = marked.parse(md, { async: false }) as string;

  const licences = Object.values(meta.licenses);
  const citations = [...new Set(licences.flatMap((l) => l.citations ?? []))];
  const notices = [...new Set(licences.flatMap((l) => (l.notice ? [l.notice] : [])))];
  const stats = Object.values(statImages as unknown as Record<string, PhotoCredit>)
    .filter((img) => shipped("stats", img));
  // after the Phase 5 report: every city photograph is shown cropped (the
  // home page's cards, the city page's band), and says so; the home
  // page's own photograph left with its band (Nathan's decision 1)
  const cities = Object.values(cityImages as unknown as Record<string, PhotoCredit>)
    .filter((img) => shipped("cities", img))
    .map((img) => ({ ...img, cropped: true }));
  const photos = [...stats, ...cities];

  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto max-w-3xl px-4 pb-16 pt-10 sm:px-12">
        {/* Phase 5: "How it works" (decision 2); Privacy and Terms left the
            top of the page for the footer every page carries */}
        <h1 className="font-display text-display-1">
          {policy.about_title}
        </h1>
        <article
          className="prose-method mt-8"
          dangerouslySetInnerHTML={{ __html: html }}
        />
        <section
          id="sources-and-credits"
          className="mt-12 border-t border-rule pt-8"
          data-testid="sources-and-credits"
        >
          <h2 className="font-display text-h2 font-semibold">{policy.credits_heading}</h2>
          <h3 className="mt-5 text-title font-semibold">{policy.credits_data_heading}</h3>
          {citations.length > 0 && (
            <details className="mt-2" data-testid="credits-data-more">
              <summary className="cursor-pointer text-body-sm font-semibold text-accent hover:text-accent-hover">
                {policy.credits_data_more.replace("{n}", citations.length.toLocaleString("en-US"))}
              </summary>
              <ul className="mt-3 flex flex-col gap-2" data-testid="credits-data">
                {citations.map((c) => (
                  <li key={c} className="text-body-sm leading-relaxed text-ink-2">{c}</li>
                ))}
              </ul>
              {notices.map((n) => (
                <p key={n} className="mt-3 text-body-sm leading-relaxed text-ink-2" data-testid="credits-notice">
                  {n}
                </p>
              ))}
            </details>
          )}
          <h3 className="mt-7 text-title font-semibold">{policy.credits_photos_heading}</h3>
          {photos.length > 0 && (
            <details className="mt-2" data-testid="credits-photos-more">
              <summary className="cursor-pointer text-body-sm font-semibold text-accent hover:text-accent-hover">
                {policy.credits_photos_more.replace("{n}", photos.length.toLocaleString("en-US"))}
              </summary>
              <ul className="mt-3 flex flex-col gap-2" data-testid="credits-photos">
                {photos.map((img) => (
                  <Credit key={img.file} img={img} policy={policy} />
                ))}
              </ul>
            </details>
          )}
        </section>
      </main>
      <SiteFooter />
    </>
  );
}

function Credit({ img, policy }: { img: PhotoCredit; policy: Record<string, string> }) {
  return (
    <li className="text-caption leading-relaxed text-ink-2" data-credit={img.file}>
      {img.title ? <>{img.title} · </> : null}
      {img.author ? <>{img.author} · </> : null}
      {img.license_url ? (
        <a href={img.license_url} rel="noopener" className="underline underline-offset-2 hover:text-ink">
          {img.license}
        </a>
      ) : (
        img.license
      )}
      {" · "}
      <a href={img.source_url} rel="noopener" className="underline underline-offset-2 hover:text-ink">
        {policy.credits_source}
      </a>
      {img.cropped ? <> · {policy.credits_cropped}</> : null}
    </li>
  );
}
