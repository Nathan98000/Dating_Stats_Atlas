/** Build the locator map's static geometry (Phase 2e item 3): state
 * outlines from the Census Bureau's generalized (cartographic boundary)
 * TIGERweb service, projected here with d3-geo's Albers USA — Alaska and
 * Hawaii in their customary insets — and emitted as plain SVG path
 * strings. The browser gets paths, never a projection engine: d3-geo is
 * a devDependency of THIS script and must not appear in the bundle
 * (asserted by e2e via the import graph staying JSON-only).
 *
 * Metro dots come from each metro's internal point as the build carries
 * it (metros.json lat/lon — Census place/county internal points, the
 * same geography source the station matching uses), never a hand-placed
 * guess.
 *
 *     node scripts/build_us_map.mjs [build_dir]
 */
import { execFileSync } from "child_process";
import { geoAlbersUsa, geoPath } from "d3-geo";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import path from "path";
import * as shapefile from "shapefile";
import { fileURLToPath } from "url";

const here = path.dirname(fileURLToPath(import.meta.url));
const buildDir = process.argv[2]
  ? path.resolve(process.argv[2])
  : null;
if (!buildDir) {
  console.error("usage: node scripts/build_us_map.mjs <build_dir>");
  process.exit(1);
}

const W = 620;
const H = 400;
// the cartographic boundary file itself, 1:20,000,000 — already the
// simplified cartographic rendition (TIGERweb's generalized layers
// refuse geometry over their query API, checked 2026-09-17)
const CB_URL =
  "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_20m.zip";
const TERRITORIES = new Set(["60", "66", "69", "72", "78"]);

const cacheDir = path.resolve(here, "..", "..", "data", "raw", "cb_state_20m");
const zipPath = path.join(cacheDir, "cb_2023_us_state_20m.zip");
if (!existsSync(path.join(cacheDir, "cb_2023_us_state_20m.shp"))) {
  mkdirSync(cacheDir, { recursive: true });
  const res = await fetch(CB_URL, {
    headers: { "User-Agent": "DatingStatsAtlas/0.1 (research build)" },
  });
  if (!res.ok) throw new Error(`cartographic boundary fetch: ${res.status}`);
  writeFileSync(zipPath, Buffer.from(await res.arrayBuffer()));
  execFileSync("unzip", ["-o", "-q", zipPath, "-d", cacheDir]);
}
const geo = await shapefile.read(
  path.join(cacheDir, "cb_2023_us_state_20m.shp"),
  path.join(cacheDir, "cb_2023_us_state_20m.dbf"),
);
const states = geo.features.filter(
  (f) => !TERRITORIES.has(f.properties.GEOID),
);
if (states.length !== 51) {
  throw new Error(`expected 50 states + DC, got ${states.length}`);
}

const projection = geoAlbersUsa().fitSize([W, H], {
  type: "FeatureCollection",
  features: states,
});
const toPath = geoPath(projection).digits(1);

const out = {
  w: W,
  h: H,
  states: states
    .map((f) => ({ f: f.properties.GEOID, d: toPath(f) }))
    .filter((s) => s.d),
};

const metros = JSON.parse(
  readFileSync(path.join(buildDir, "metros.json"), "utf-8"),
);
const metrosCsv = readFileSync(
  path.resolve(here, "..", "..", "results", "metros.csv"), "utf-8");
const primaryState = {};
for (const line of metrosCsv.split("\n").slice(1)) {
  const m = line.match(/^(\d{5}),.*?,(\d+),"?([0-9+]+)"?,/);
  if (m) primaryState[m[1]] = m[3].split("+")[0];
}

out.metros = {};
let missed = 0;
for (const m of metros) {
  const p = projection([m.lon, m.lat]);
  if (!p) {
    missed++;
    continue;
  }
  out.metros[m.cbsa] = [
    Math.round(p[0] * 10) / 10,
    Math.round(p[1] * 10) / 10,
    primaryState[m.cbsa] ?? null,
  ];
}
if (missed > 0) throw new Error(`${missed} metros fell outside the projection`);

const dest = path.resolve(here, "..", "src", "data", "us-map.json");
const payload = JSON.stringify(out);
writeFileSync(dest, payload + "\n");
console.log(
  `${dest}: ${out.states.length} states, ${Object.keys(out.metros).length} ` +
  `metros, ${(payload.length / 1024).toFixed(0)} KB`,
);
