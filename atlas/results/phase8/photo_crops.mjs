// Phase 8 (R20): one photograph as the site crops it — the desk card (16:10), the phone
// card and city band (16:7) and the link preview (1200x630) — at a focus (object-position),
// beside the whole frame. The crop math is the review's photo_sheets.mjs's.
//   node crops.mjs <file> <focus "X% Y%"> <out.png> [label]
// (copy it into atlas/web/scripts first, so sharp resolves from atlas/web's packages; it wrote
// results/phase8/screens/photos-*-crops, then converted to JPEG)
import sharp from "sharp";
const [file, focus = "50% 35%", out, label = ""] = process.argv.slice(2);
const [fx, fy] = focus.split(" ").map((p) => parseFloat(p) / 100);
const im = sharp(file); const { width: W, height: H } = await im.metadata();
async function crop(aspect, w) {
  let box;
  if (W / H > aspect) { const nw = Math.round(H * aspect); box = { left: Math.round((W - nw) * fx), top: 0, width: nw, height: H }; }
  else { const nh = Math.round(W / aspect); box = { left: 0, top: Math.round((H - nh) * fy), width: W, height: nh }; }
  return sharp(file).extract(box).resize(w, Math.round(w / aspect)).toBuffer();
}
const TW = 420, GAP = 10, LAB = 26;
const whole = await sharp(file).resize({ width: TW }).toBuffer();
const wholeH = (await sharp(whole).metadata()).height;
const tiles = [["whole " + W + "x" + H, whole, wholeH], ["card 16:10", await crop(1.6, TW), Math.round(TW / 1.6)],
  ["band 16:7", await crop(16 / 7, TW), Math.round(TW / (16 / 7))], ["preview 1200x630", await crop(1200 / 630, TW), Math.round(TW / (1200 / 630))]];
const sheetW = tiles.length * (TW + GAP) + GAP, sheetH = LAB + Math.max(...tiles.map((t) => t[2])) + 2 * GAP + LAB;
const comps = [{ input: Buffer.from(`<svg width="${sheetW}" height="${LAB}"><text x="${GAP}" y="18" font-family="Helvetica" font-size="15" font-weight="bold">${label} · focus ${focus}</text></svg>`), left: 0, top: 0 }];
tiles.forEach(([name, buf], i) => {
  const x = GAP + i * (TW + GAP);
  comps.push({ input: Buffer.from(`<svg width="${TW}" height="${LAB}"><text x="0" y="18" font-family="Helvetica" font-size="13">${name}</text></svg>`), left: x, top: LAB });
  comps.push({ input: buf, left: x, top: 2 * LAB });
});
await sharp({ create: { width: sheetW, height: sheetH, channels: 3, background: "#FDF7F3" } }).composite(comps).png().toFile(out);
console.log(out);
