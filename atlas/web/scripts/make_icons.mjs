// Phase 7 (R02): the site's own icon, a Fraunces "D" (weight 600, SOFT 30)
// in --surface (#FFFFFF) on --accent (#9E3B57), centred on its ink, on a
// square with corners at 22% of its side.
//
// The "D" is drawn by Playwright's Chromium from an HTML page that loads the
// site's own Fraunces file — the latin woff2 next/font put in a production
// build's static/media (no system font, no CDN) — and screenshot at 512px.
// sharp then writes:
//   src/app/icon.png        512x512, rounded corners (transparent outside)
//   src/app/apple-icon.png  180x180, square corners (iOS rounds them itself)
//   src/app/favicon.ico     16x16 and 32x32 PNG entries, written by hand
// and, for review, a sheet of the four sizes side by side (SHEET, if set).
//
//   cd atlas/web && NEXT_DIST_DIR=.next-p7 node scripts/make_icons.mjs
//   (SHEET=../results/phase7/screens/icon.png to write the sheet too)
import { chromium } from "@playwright/test";
import sharp from "sharp";
import { readFileSync, readdirSync, writeFileSync } from "fs";
import path from "path";

const WEB = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const DIST = path.resolve(WEB, process.env.NEXT_DIST_DIR || ".next");
const SIDE = 512;
const ACCENT = "#9E3B57"; // --accent
const SURFACE = "#FFFFFF"; // --surface
const RADIUS = 0.22; // corners, as a share of the side
const INK_HEIGHT = 0.56; // the D's ink, as a share of the side

/** The build's Fraunces face for basic latin: its @font-face whose
 * unicode-range starts with U+0000-00FF (minified as U+??). */
function frauncesFile() {
  const dir = path.join(DIST, "static", "chunks");
  for (const f of readdirSync(dir).filter((n) => n.endsWith(".css"))) {
    const css = readFileSync(path.join(dir, f), "utf8");
    for (const face of css.match(/@font-face\{[^}]*\}/g) ?? []) {
      if (!/font-family:\s*Fraunces[;"]/.test(face) || !/unicode-range:U\+(0+-0*FF|\?\?)[,;}]/i.test(face)) continue;
      const url = face.match(/url\(([^)]+)\)/)[1].replace(/["']/g, "");
      return path.resolve(dir, url);
    }
  }
  throw new Error(`no Fraunces latin face in ${dir}: build first (NEXT_DIST_DIR)`);
}

const font = frauncesFile();
const fontUrl = `data:font/woff2;base64,${readFileSync(font).toString("base64")}`;

const page_ = (size, dx, dy, bg, radius) => `<!doctype html><html><head><style>
@font-face { font-family: "SiteFraunces"; src: url(${fontUrl}) format("woff2"); font-weight: 100 900; }
html, body { margin: 0; background: transparent; }
#sq { width: ${SIDE}px; height: ${SIDE}px; display: flex; align-items: center; justify-content: center;
  background: ${bg}; border-radius: ${radius * 100}%; overflow: hidden; }
#d { font-family: "SiteFraunces"; font-weight: 600; font-variation-settings: "SOFT" 30;
  font-size: ${size}px; line-height: 1; color: ${SURFACE}; transform: translate(${dx}px, ${dy}px); }
</style></head><body><div id="sq"><span id="d">D</span></div></body></html>`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: SIDE, height: SIDE }, deviceScaleFactor: 1 });

/** The D's ink box inside the square: drawn alone on a transparent ground,
 * then trimmed to its pixels. */
async function ink(size) {
  await page.setContent(page_(size, 0, 0, "transparent", 0));
  await page.evaluate(() => document.fonts.ready);
  const shot = await page.locator("#sq").screenshot({ omitBackground: true });
  const { info } = await sharp(shot).trim({ threshold: 1 }).toBuffer({ resolveWithObject: true });
  return { left: -info.trimOffsetLeft, top: -info.trimOffsetTop, width: info.width, height: info.height };
}

// size the D so its ink is INK_HEIGHT of the side, then centre it on its ink
let size = 360;
for (let i = 0; i < 3; i++) size *= (INK_HEIGHT * SIDE) / (await ink(size)).height;
const box = await ink(size);
const dx = SIDE / 2 - (box.left + box.width / 2);
const dy = SIDE / 2 - (box.top + box.height / 2);

async function render(radius) {
  await page.setContent(page_(size, dx, dy, ACCENT, radius));
  await page.evaluate(() => document.fonts.ready);
  return page.locator("#sq").screenshot({ omitBackground: true });
}
const rounded = await render(RADIUS);
const square = await render(0);
await browser.close();

const png = (buf, n) => sharp(buf).resize(n, n, { kernel: "lanczos3" }).png({ compressionLevel: 9 }).toBuffer();
const icon = await png(rounded, SIDE);
const apple = await png(square, 180);
const ico16 = await png(rounded, 16);
const ico32 = await png(rounded, 32);

/** An ICO holding PNG images: a 6-byte header, one 16-byte entry per image,
 * then the PNGs. */
function ico(images) {
  const head = Buffer.alloc(6 + 16 * images.length);
  head.writeUInt16LE(0, 0); // reserved
  head.writeUInt16LE(1, 2); // type: icon
  head.writeUInt16LE(images.length, 4);
  let offset = head.length;
  images.forEach(({ n, buf }, i) => {
    const e = 6 + 16 * i;
    head.writeUInt8(n >= 256 ? 0 : n, e); // width
    head.writeUInt8(n >= 256 ? 0 : n, e + 1); // height
    head.writeUInt8(0, e + 2); // no palette
    head.writeUInt8(0, e + 3); // reserved
    head.writeUInt16LE(1, e + 4); // colour planes
    head.writeUInt16LE(32, e + 6); // bits per pixel
    head.writeUInt32LE(buf.length, e + 8);
    head.writeUInt32LE(offset, e + 12);
    offset += buf.length;
  });
  return Buffer.concat([head, ...images.map((x) => x.buf)]);
}

writeFileSync(path.join(WEB, "src/app/icon.png"), icon);
writeFileSync(path.join(WEB, "src/app/apple-icon.png"), apple);
writeFileSync(path.join(WEB, "src/app/favicon.ico"), ico([{ n: 16, buf: ico16 }, { n: 32, buf: ico32 }]));

if (process.env.SHEET) {
  // the four sizes side by side on the site's paper, each at its own pixels
  const items = [[ico16, 16], [ico32, 32], [apple, 180], [icon, 512]];
  const gap = 40;
  const width = items.reduce((w, [, n]) => w + n + gap, gap);
  const height = SIDE + 2 * gap;
  let x = gap;
  const layers = items.map(([buf, n]) => {
    const l = { input: buf, left: x, top: gap + (SIDE - n) };
    x += n + gap;
    return l;
  });
  await sharp({ create: { width, height, channels: 4, background: "#FDF7F3" } })
    .composite(layers).png().toFile(path.resolve(WEB, process.env.SHEET));
}
console.log(`icon from ${path.relative(WEB, font)}: D at ${size.toFixed(1)}px, ink ${box.width}x${box.height}, shift ${dx.toFixed(1)},${dy.toFixed(1)}`);
