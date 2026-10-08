// Contact sheets for reviewing photographs: a grid of labelled thumbnails,
// each cropped the way a home-page card crops it (16:10, cover), rendered
// by Playwright's Chromium to a PNG.
//
//   node scripts/contact_sheet.mjs <items.json> <out-prefix> [per-sheet]
//     items.json: [{ "label": "...", "path": "/abs/file.jpg" }, ...]
//     -> <out-prefix>_01.png, _02.png, ...
import { chromium } from "@playwright/test";
import { readFileSync, writeFileSync } from "fs";
import { pathToFileURL } from "url";

const [itemsPath, prefixArg, perArg] = process.argv.slice(2);
const prefix = (await import("path")).resolve(prefixArg);
const items = JSON.parse(readFileSync(itemsPath, "utf8"));
const per = Number(perArg ?? 16);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
for (let s = 0; s * per < items.length; s++) {
  const chunk = items.slice(s * per, (s + 1) * per);
  const cells = chunk.map((it) => `<figure><div class="ph" style="background-image:url('${pathToFileURL(it.path).href}')"></div><figcaption>${it.label}</figcaption></figure>`).join("");
  const html = `${prefix}_${String(s + 1).padStart(2, "0")}.html`;
  writeFileSync(html, `<!doctype html><style>
    body{margin:12px;font:13px/1.3 -apple-system,Helvetica,Arial;background:#fff}
    main{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
    figure{margin:0}.ph{aspect-ratio:16/10;background:#eee center/cover no-repeat;border-radius:6px}
    figcaption{padding:3px 2px 0;height:34px;overflow:hidden}</style><main>${cells}</main>`);
  await page.goto(pathToFileURL(html).href);
  await page.waitForLoadState("load");
  await page.waitForTimeout(300);
  const n = String(s + 1).padStart(2, "0");
  await page.screenshot({ path: `${prefix}_${n}.png`, fullPage: true });
  console.log(`${prefix}_${n}.png`);
}
await browser.close();
