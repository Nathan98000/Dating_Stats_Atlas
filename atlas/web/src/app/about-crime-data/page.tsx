import { promises as fs } from "fs";
import path from "path";
import { marked } from "marked";
import { SiteHeader } from "@/components/chrome";

export const dynamic = "force-dynamic";

/** The crime explainer (item 9): the subtle callout made permanent —
 * what the figures are, why the reporting panel makes cities not
 * comparable, what coverage means. Renders docs/crime.md verbatim
 * (synced at build), the same pattern as How it works. Crime gets this
 * page INSTEAD of a ranking page, deliberately. */
export default async function AboutCrimeDataPage() {
  const mdPath = path.join(process.cwd(), "content", "crime.md");
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
