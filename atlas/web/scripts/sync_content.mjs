/** Copy docs/methodology.md into the app root (content/), verbatim, before
 * every dev/build: the page renders the versioned file, never a paraphrase,
 * and Turbopack cannot trace files outside its project root. */
import { copyFileSync, mkdirSync, readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(here, "..", "..", "docs", "methodology.md");
const destDir = path.resolve(here, "..", "content");
mkdirSync(destDir, { recursive: true });
copyFileSync(src, path.join(destDir, "methodology.md"));
const head = readFileSync(src, "utf-8").split("\n")[0];
console.log(`synced methodology.md (${head})`);
