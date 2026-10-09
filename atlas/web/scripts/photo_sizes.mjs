// Phase 6 (commit A, F03): the photographs, delivered at the size they're shown.
//
// For every photograph the manifests list and the disk holds (src/data/city-images.json
// -> public/cities/, src/data/stat-images.json -> public/stats/), write:
//   - WebP copies at quality 72, at widths 480, 720, 1080, 1600 and 2048, skipping any
//     wider than the original: public/{cities,stats}/w/<slug>-<w>.webp;
//   - a 1200x630 JPEG link preview at quality 80, cover-cropped at the photo's focal
//     point (the manifest's `focus`, an object-position value; default "50% 35%"):
//     public/{cities,stats}/og/<slug>.jpg;
//   - src/data/photo-sizes.json: per group, slug -> natural width and height and the
//     widths written. The JSON is committed (small, derived from the pinned files); the
//     image files stay out of git with the originals.
// Every derivative is the same photograph, resized (and, for the preview, cropped): it
// carries the original's credit and licence (ADR 0012).
//
//   node scripts/photo_sizes.mjs            all photographs
//   node scripts/photo_sizes.mjs --only a,b  just these slugs (the manifest is merged)
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import path from "path";
import sharp from "sharp";

const WEB = path.resolve(new URL("..", import.meta.url).pathname);
export const WIDTHS = [480, 720, 1080, 1600, 2048];
export const DEFAULT_FOCUS = "50% 35%";
const OG = { w: 1200, h: 630 };
const GROUPS = [
  { name: "cities", manifest: "src/data/city-images.json", dir: "public/cities" },
  { name: "stats", manifest: "src/data/stat-images.json", dir: "public/stats" },
];
const OUT = path.join(WEB, "src/data/photo-sizes.json");

const onlyArg = process.argv.indexOf("--only");
const only = onlyArg > 0 ? new Set(process.argv[onlyArg + 1].split(",")) : null;

/** "50% 35%" -> [0.5, 0.35] (object-position percentages, x then y). */
export function parseFocus(focus) {
  const m = /^\s*(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%\s*$/.exec(focus ?? DEFAULT_FOCUS);
  if (!m) throw new Error(`focus must be "X% Y%": ${focus}`);
  return [Number(m[1]) / 100, Number(m[2]) / 100];
}

/** The box object-fit: cover with object-position (px, py) shows of a W x H image in a
 * w x h frame, in source pixels. */
export function coverBox(W, H, w, h, [px, py]) {
  const scale = Math.max(w / W, h / H);
  const cw = Math.min(W, Math.round(w / scale));
  const ch = Math.min(H, Math.round(h / scale));
  return { left: Math.round((W - cw) * px), top: Math.round((H - ch) * py), width: cw, height: ch };
}

const sizes = existsSync(OUT) ? JSON.parse(readFileSync(OUT, "utf8")) : {};
let written = 0;
for (const g of GROUPS) {
  const manifest = JSON.parse(readFileSync(path.join(WEB, g.manifest), "utf8"));
  const group = only ? { ...(sizes[g.name] ?? {}) } : {};
  mkdirSync(path.join(WEB, g.dir, "w"), { recursive: true });
  mkdirSync(path.join(WEB, g.dir, "og"), { recursive: true });
  for (const [slug, img] of Object.entries(manifest)) {
    if (only && !only.has(slug)) continue;
    const src = path.join(WEB, g.dir, img.file);
    if (!existsSync(src)) {
      delete group[slug];
      continue;
    }
    const buf = readFileSync(src);
    // .rotate() applies the EXIF orientation, as a browser does
    const md = await sharp(buf).metadata();
    const turned = (md.orientation ?? 1) >= 5;
    const W = turned ? md.height : md.width;
    const H = turned ? md.width : md.height;
    const widths = WIDTHS.filter((w) => w <= W);
    for (const w of widths) {
      await sharp(buf).rotate().resize({ width: w }).webp({ quality: 72 })
        .toFile(path.join(WEB, g.dir, "w", `${slug}-${w}.webp`));
    }
    const box = coverBox(W, H, OG.w, OG.h, parseFocus(img.focus));
    await sharp(buf).rotate().extract(box).resize(OG.w, OG.h).jpeg({ quality: 80, mozjpeg: true })
      .toFile(path.join(WEB, g.dir, "og", `${slug}.jpg`));
    group[slug] = { width: W, height: H, widths };
    written++;
  }
  sizes[g.name] = Object.fromEntries(Object.entries(group).sort(([a], [b]) => a.localeCompare(b)));
}
writeFileSync(OUT, JSON.stringify(sizes, null, 1) + "\n");
console.log(`photo sizes: ${written} photographs -> ${path.relative(WEB, OUT)}`);
