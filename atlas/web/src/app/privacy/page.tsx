import { promises as fs } from "fs";
import path from "path";
import { marked } from "marked";
import { SiteHeader } from "@/components/chrome";

export const dynamic = "force-dynamic";

/** The privacy page (m4.0.0, Nathan's decision 9): docs/privacy.md
 * rendered verbatim (synced at build), the same pattern as About us and
 * About crime data. Linked from About us; not in the nav. */
export default async function PrivacyPage() {
  const mdPath = path.join(process.cwd(), "content", "privacy.md");
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
