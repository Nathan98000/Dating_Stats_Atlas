import { promises as fs } from "fs";
import path from "path";
import { marked } from "marked";
import { apiMeta } from "@/lib/api";
import { SiteHeader } from "@/components/chrome";

export const dynamic = "force-dynamic";

/** "How it works": docs/methodology.md rendered verbatim (synced at
 * build), plus the sources with their attributions from the typed license
 * registry through the manifest — the whole honesty story in plain
 * language, with no figure of any kind invented here. */
export default async function HowItWorksPage() {
  const meta = await apiMeta();
  const mdPath = path.join(process.cwd(), "content", "methodology.md");
  const md = await fs.readFile(mdPath, "utf-8");
  const html = marked.parse(md, { async: false }) as string;
  const sources = Object.entries(meta.licenses);

  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto max-w-3xl px-6 pb-16 pt-10 sm:px-12">
        <article
          className="prose-method"
          dangerouslySetInnerHTML={{ __html: html }}
        />
        <section className="mt-12 border-t border-rule pt-8">
          <h2 className="font-display text-[26px] font-semibold">Sources</h2>
          <ul className="mt-3 flex flex-col gap-2">
            {sources.map(([key, lic]) => (
              <li key={key} className="text-sm text-ink-2">
                {lic.attribution ?? lic.name}
                {" · "}
                <a
                  className="font-semibold text-accent hover:text-accent-hover"
                  href={lic.url}
                  rel="noopener"
                >
                  terms
                </a>
                {lic.notes ? (
                  <span className="text-ink-3"> — {lic.notes}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      </main>
    </>
  );
}
