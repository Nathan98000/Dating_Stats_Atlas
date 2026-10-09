/** Phase 6 (F32): the locator map's state outlines, simplified for the
 * static /map/<cbsa>.svg (src/app/map/[cbsa]/route.ts). Reads the full
 * geometry (src/data/us-map.json, written by build_us_map.mjs from the
 * Census cartographic boundary file), simplifies each ring with
 * Douglas-Peucker at TOLERANCE map units (the map is 620x400 and is shown at
 * 300px or less), drops rings smaller than MIN_AREA (specks of coast),
 * rounds to whole units and writes compact relative paths to
 * src/data/us-map-small.json. The metro dots are copied as they are.
 *
 *     node scripts/simplify_us_map.mjs [tolerance]
 */
import { readFileSync, writeFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const here = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(here, "..", "src", "data", "us-map.json");
const OUT = path.join(here, "..", "src", "data", "us-map-small.json");
const TOLERANCE = Number(process.argv[2] ?? 1.0);
const MIN_AREA = 6;

const map = JSON.parse(readFileSync(SRC, "utf8"));

function rings(d) {
  return d.split(/(?=M)/).map((sub) => sub.replace(/[MZ]/g, " ").trim().split(/L|\s+/)
    .filter(Boolean).map((p) => p.split(",").map(Number)));
}

function perp([x, y], [x1, y1], [x2, y2]) {
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  if (len === 0) return Math.hypot(x - x1, y - y1);
  return Math.abs(dy * x - dx * y + x2 * y1 - y2 * x1) / len;
}

function dp(pts, tol) {
  if (pts.length < 3) return pts;
  let max = 0, idx = 0;
  for (let i = 1; i < pts.length - 1; i++) {
    const d = perp(pts[i], pts[0], pts[pts.length - 1]);
    if (d > max) { max = d; idx = i; }
  }
  if (max <= tol) return [pts[0], pts[pts.length - 1]];
  return [...dp(pts.slice(0, idx + 1), tol).slice(0, -1), ...dp(pts.slice(idx), tol)];
}

function area(pts) {
  let a = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
    a += x1 * y2 - x2 * y1;
  }
  return Math.abs(a) / 2;
}

function encode(ring) {
  const r = ring.map(([x, y]) => [Math.round(x), Math.round(y)])
    .filter((p, i, a) => i === 0 || p[0] !== a[i - 1][0] || p[1] !== a[i - 1][1]);
  if (r.length < 3) return "";
  let s = `M${r[0][0]},${r[0][1]}l`;
  const parts = [];
  for (let i = 1; i < r.length; i++) {
    const dx = r[i][0] - r[i - 1][0], dy = r[i][1] - r[i - 1][1];
    parts.push(`${dx}${dy < 0 ? "" : ","}${dy}`);
  }
  return s + parts.join(" ").replace(/ -/g, "-") + "z";
}

const states = map.states.map(({ f, d }) => {
  const out = rings(d)
    .filter((r) => area(r) >= MIN_AREA)
    .map((r) => {
      // simplify a closed ring as two open halves, so its ends stay put
      const mid = Math.floor(r.length / 2);
      const a = dp(r.slice(0, mid + 1), TOLERANCE);
      const b = dp(r.slice(mid), TOLERANCE);
      return encode([...a.slice(0, -1), ...b]);
    })
    .join("");
  return { f, d: out };
}).filter((s) => s.d);

const small = { w: map.w, h: map.h, states, metros: map.metros };
writeFileSync(OUT, JSON.stringify(small) + "\n");
const pathBytes = states.reduce((n, s) => n + s.d.length, 0);
console.log(`us-map-small.json: ${states.length} states, ${pathBytes} bytes of path at tolerance ${TOLERANCE}`);
