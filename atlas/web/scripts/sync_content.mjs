/** Copy the rendered docs (methodology.md, crime.md) into the app root
 * (content/), verbatim, before every dev/build: the pages render the
 * versioned files, never a paraphrase, and Turbopack cannot trace files
 * outside its project root. */
import { copyFileSync, mkdirSync, readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const here = path.dirname(fileURLToPath(import.meta.url));
const destDir = path.resolve(here, "..", "content");
mkdirSync(destDir, { recursive: true });
for (const name of ["methodology.md", "crime.md"]) {
  const src = path.resolve(here, "..", "..", "docs", name);
  copyFileSync(src, path.join(destDir, name));
  const head = readFileSync(src, "utf-8").split("\n")[0];
  console.log(`synced ${name} (${head})`);
}
