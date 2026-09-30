import { promises as fs } from "fs";
import fsSync from "fs";
import path from "path";
import Link from "next/link";
import { marked } from "marked";
import { apiMeta } from "@/lib/api";
import { SiteHeader } from "@/components/chrome";
import heroImage from "@/data/hero.json";
import cityImages from "@/data/city-images.json";
import statImages from "@/data/stat-images.json";

export const dynamic = "force-dynamic";

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
 * What we measure linked prominently near the top, the plain-language
 * account of how the numbers are made (docs/methodology.md, synced at
 * build), and the ONE place every source and photograph credit lives —
 * Sources and credits: the data citations and notices from the typed
 * licence registry through the manifest, and each photograph's credit
 * from the committed image manifests. The privacy page and About crime
 * data are linked from here. Every label comes from the registry. */
export default async function AboutPage() {
  const meta = await apiMeta();
  const policy = meta.policy_strings;
  const mdPath = path.join(process.cwd(), "content", "methodology.md");
  const md = await fs.readFile(mdPath, "utf-8");
  const html = marked.parse(md, { async: false }) as string;

  const licences = Object.values(meta.licenses);
  const citations = [...new Set(licences.flatMap((l) => l.citations ?? []))];
  const notices = [...new Set(licences.flatMap((l) => (l.notice ? [l.notice] : [])))];
  const hero = heroImage as unknown as PhotoCredit;
  const heroShown = fsSync.existsSync(path.join(process.cwd(), "public", "hero.jpg")) ? hero : null;
  const stats = Object.values(statImages as unknown as Record<string, PhotoCredit>)
    .filter((img) => shipped("stats", img));
  const cities = Object.values(cityImages as unknown as Record<string, PhotoCredit>)
    .filter((img) => shipped("cities", img));
  const more = [...stats, ...cities];

  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto max-w-3xl px-6 pb-16 pt-10 sm:px-12">
        <h1 className="font-display text-[38px] font-semibold leading-tight tracking-tight">
          {policy.about_title}
        </h1>
        <nav className="mt-5 flex flex-wrap gap-3" data-testid="about-links" aria-label={policy.about_title}>
          <Link
            href="/what-we-measure"
            className="inline-flex min-h-[46px] items-center rounded-lg bg-accent px-5 text-[14.5px] font-bold text-white hover:bg-accent-hover"
            data-testid="about-measure-link"
          >
            {policy.about_measure_link}
          </Link>
          <Link
            href="/about-crime-data"
            className="inline-flex min-h-[46px] items-center rounded-lg border-[1.5px] border-ink px-5 text-[14.5px] font-bold text-ink hover:bg-tint"
          >
            {policy.about_crime_link}
          </Link>
          <Link
            href="/privacy"
            className="inline-flex min-h-[46px] items-center rounded-lg border-[1.5px] border-ink px-5 text-[14.5px] font-bold text-ink hover:bg-tint"
            data-testid="about-privacy-link"
          >
            {policy.about_privacy_link}
          </Link>
          {/* the terms of use (docs/terms.md), approved by Nathan for now,
              linked beside Privacy */}
          <Link
            href="/terms"
            className="inline-flex min-h-[46px] items-center rounded-lg border-[1.5px] border-ink px-5 text-[14.5px] font-bold text-ink hover:bg-tint"
            data-testid="about-terms-link"
          >
            {policy.about_terms_link}
          </Link>
        </nav>
        <article
          className="prose-method mt-8"
          dangerouslySetInnerHTML={{ __html: html }}
        />
        <section
          id="sources-and-credits"
          className="mt-12 border-t border-rule pt-8"
          data-testid="sources-and-credits"
        >
          <h2 className="font-display text-[26px] font-semibold">{policy.credits_heading}</h2>
          <h3 className="mt-5 text-[17px] font-semibold">{policy.credits_data_heading}</h3>
          <ul className="mt-2 flex flex-col gap-2" data-testid="credits-data">
            {citations.map((c) => (
              <li key={c} className="text-sm leading-relaxed text-ink-2">{c}</li>
            ))}
          </ul>
          {notices.map((n) => (
            <p key={n} className="mt-3 text-sm leading-relaxed text-ink-2" data-testid="credits-notice">
              {n}
            </p>
          ))}
          <h3 className="mt-7 text-[17px] font-semibold">{policy.credits_photos_heading}</h3>
          <ul className="mt-2 flex flex-col gap-2" data-testid="credits-photos">
            {heroShown && <Credit img={heroShown} policy={policy} />}
          </ul>
          {more.length > 0 && (
            <details className="mt-3" data-testid="credits-photos-more">
              <summary className="cursor-pointer text-sm font-semibold text-accent hover:text-accent-hover">
                {policy.credits_photos_more.replace("{n}", more.length.toLocaleString("en-US"))}
              </summary>
              <ul className="mt-3 flex flex-col gap-2">
                {more.map((img) => (
                  <Credit key={img.file} img={img} policy={policy} />
                ))}
              </ul>
            </details>
          )}
        </section>
      </main>
    </>
  );
}

function Credit({ img, policy }: { img: PhotoCredit; policy: Record<string, string> }) {
  return (
    <li className="text-[13px] leading-relaxed text-ink-2" data-credit={img.file}>
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
