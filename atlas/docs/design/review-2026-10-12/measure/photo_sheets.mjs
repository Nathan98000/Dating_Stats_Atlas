// Round 4 (12 October 2026): a Node/sharp port of round 3's photo_sheets.py (no PIL on
// this Mac). Contact sheets of every ranked city's photograph as the site crops it:
// the desk card (16:10) and the phone card / city band (16:7), each at the manifest's
// `focus` (object-position) or the default 50% 35%, in the default search's rank order.
// Labels carry the rank, the city and the source's pixel size.
//   RANK_JSON=<rank response> node photo_sheets.mjs  -> ../screens/photos/sheet-NN.jpg, photos.json
// Run from this folder (node_modules links to atlas/web's).
import sharp from "sharp";
import { readFileSync, writeFileSync, mkdirSync } from "fs";

const WEB = new URL("../../../../web/", import.meta.url).pathname;
const OUT = new URL("../screens/photos/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const imgs = JSON.parse(readFileSync(WEB + "src/data/city-images.json", "utf8"));
const rank = JSON.parse(readFileSync(process.env.RANK_JSON, "utf8"));
const cities = rank.ranked.map((r, i) => ({ rank: i + 1, name: r.display_name, slug: r.slug }));

const TW = 300, CARD_H = Math.round(TW / 1.6), BAND_H = Math.round(TW / (16 / 7)), LABEL = 34, GAP = 8;
const COLS = 5, PER = 20;
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

async function crop(file, aspect, w, fx, fy) {
  const im = sharp(file); const { width: W, height: H } = await im.metadata();
  let box;
  if (W / H > aspect) { const nw = Math.round(H * aspect); box = { left: Math.round((W - nw) * fx), top: 0, width: nw, height: H }; }
  else { const nh = Math.round(W / aspect); box = { left: 0, top: Math.round((H - nh) * fy), width: W, height: nh }; }
  return { buf: await sharp(file).extract(box).resize(w, Math.round(w / aspect)).toBuffer(), W, H };
}

const meta = [];
for (let s = 0; s * PER < cities.length; s++) {
  const group = cities.slice(s * PER, (s + 1) * PER);
  const rows = Math.ceil(group.length / COLS);
  const tileH = LABEL + CARD_H + 4 + BAND_H;
  const sheetW = COLS * TW + (COLS + 1) * GAP, sheetH = rows * tileH + (rows + 1) * GAP;
  const comps = [];
  for (const [i, c] of group.entries()) {
    const img = imgs[c.slug];
    const x = GAP + (i % COLS) * (TW + GAP), y = GAP + Math.floor(i / COLS) * (tileH + GAP);
    if (!img) { meta.push({ ...c, file: null }); continue; }
    const [fx, fy] = (img.focus || "50% 35%").split(" ").map((p) => parseFloat(p) / 100);
    const file = WEB + "public/cities/" + img.file;
    const card = await crop(file, 1.6, TW, fx, fy);
    const band = await crop(file, 16 / 7, TW, fx, fy);
    meta.push({ ...c, file: img.file, px: `${card.W}x${card.H}`, focus: img.focus || null });
    const label = `<svg width="${TW}" height="${LABEL}"><text x="0" y="14" font-family="Helvetica" font-size="13" font-weight="bold" fill="#201B1D">#${c.rank} ${esc(c.name)}</text><text x="0" y="29" font-family="Helvetica" font-size="11" fill="#5A5257">${card.W}×${card.H}${img.focus ? " · focus " + img.focus : ""}</text></svg>`;
    comps.push({ input: Buffer.from(label), left: x, top: y });
    comps.push({ input: card.buf, left: x, top: y + LABEL });
    // the rank medallion where it sits on the card (top left, 40px at 1x on a ~250px card)
    if (c.rank <= 3) comps.push({ input: Buffer.from(`<svg width="30" height="30"><circle cx="15" cy="15" r="14" fill="#F2B544"/></svg>`), left: x + 10, top: y + LABEL + 10 });
    comps.push({ input: band.buf, left: x, top: y + LABEL + CARD_H + 4 });
  }
  const name = `sheet-${String(s + 1).padStart(2, "0")}.jpg`;
  await sharp({ create: { width: sheetW, height: sheetH, channels: 3, background: "#FDF7F3" } }).composite(comps).jpeg({ quality: 80 }).toFile(OUT + name);
  console.log(name, group[0].rank, "–", group.at(-1).rank);
}
writeFileSync("photos.json", JSON.stringify(meta, null, 1));
