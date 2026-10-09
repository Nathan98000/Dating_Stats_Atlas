import usMap from "@/data/us-map-small.json";

/** Phase 6 (F32): the city page's locator map as a static image per metro,
 * /map/<cbsa>.svg — Phase 5's generator (its Deviation 6, for the cards'
 * maps, retired after the report) brought back for the city page, over
 * simplified state outlines (scripts/simplify_us_map.mjs, about 6KB of
 * path), so the map's geometry never enters the page's HTML or script
 * (the review measured 304K characters of it there). The same fills as
 * before: land, the metro's state tinted, the metro's dot in the accent.
 * An image cannot read CSS variables, so the fills are the tokens' values
 * (--tint, --paper, --rule, --accent). Built at build time. */

const MAP = usMap as unknown as {
  w: number;
  h: number;
  states: { f: string; d: string }[];
  metros: Record<string, [number, number, string | null]>;
};

export const dynamic = "force-static";

export function generateStaticParams() {
  return Object.keys(MAP.metros).map((cbsa) => ({ cbsa: `${cbsa}.svg` }));
}

export async function GET(_req: Request, { params }: { params: Promise<{ cbsa: string }> }) {
  const { cbsa } = await params;
  const dot = MAP.metros[cbsa.replace(/\.svg$/, "")];
  if (!dot) return new Response("not found", { status: 404 });
  const home = dot[2];
  const paths = MAP.states.map((s) =>
    `<path d="${s.d}" fill="${s.f === home ? "#F7E9EE" : "#FDF7F3"}"/>`,
  ).join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${MAP.w} ${MAP.h}">`
    + `<g stroke="#EBDFD8" stroke-width="0.75" stroke-linejoin="round">${paths}</g>`
    + `<circle cx="${dot[0]}" cy="${dot[1]}" r="7" fill="#9E3B57"/></svg>`;
  return new Response(svg, {
    headers: { "content-type": "image/svg+xml", "cache-control": "public, max-age=86400" },
  });
}
