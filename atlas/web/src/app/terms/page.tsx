import { promises as fs } from "fs";
import path from "path";
import { marked } from "marked";
import { SiteHeader } from "@/components/chrome";

export const dynamic = "force-dynamic";

/** The terms of use (written before launch; approved by Nathan for now):
 * docs/terms.md rendered verbatim (synced at build), the same pattern as
 * the privacy page. Linked from About us; not in the nav. */
export default async function TermsPage() {
  const mdPath = path.join(process.cwd(), "content", "terms.md");
  const md = await fs.readFile(mdPath, "utf-8");
  const html = marked.parse(md, { async: false }) as string;
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto max-w-3xl px-6 pb-16 pt-10 sm:px-12">
        <article
          className="prose-method"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </main>
    </>
  );
}
