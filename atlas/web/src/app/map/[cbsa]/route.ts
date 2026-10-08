import usMap from "@/data/us-map.json";

/** Phase 5: the locator map as an SVG image, for the featured cards whose
 * city has no croppable photograph. The same geometry and fills as the
 * city page's LocatorMap (Census boundaries, Albers USA, the metro's state
 * tinted and its dot in the accent), served as a static file per metro so
 * the map's 160KB never enters the page's script. Built at build time.
 * An image cannot read CSS variables, so the fills are the tokens' values
 * (--tint, --paper, --rule, --accent). */

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
    `<path d="${s.d}" fill="${s.f === home ? "#F7E9EE" : "#FDF7F3"}" stroke="#EBDFD8" stroke-width="0.75" stroke-linejoin="round"/>`,
  ).join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${MAP.w} ${MAP.h}">`
    + `${paths}<circle cx="${dot[0]}" cy="${dot[1]}" r="9" fill="#9E3B57"/></svg>`;
  return new Response(svg, {
    headers: { "content-type": "image/svg+xml", "cache-control": "public, max-age=86400" },
  });
}
