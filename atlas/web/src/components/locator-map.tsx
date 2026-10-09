import type { MetroMeta } from "@/lib/types";

/** The city page's locator (Phase 2e item 3): a real map of the United
 * States with STATE BOUNDARIES — Census cartographic boundary geometry,
 * projected to Albers USA at build time. Two fills and one hairline:
 * land, the metro's state, and the metro dot in the accent, placed from
 * the build's Census internal point. Flat, in the palette; no terrain, no
 * labels, no interactivity.
 *
 * Phase 6 (F32): an image of the static /map/<cbsa>.svg (simplified
 * outlines, src/app/map), no longer inline SVG — the page's HTML carried
 * the map's path data twice, as markup and again in its script payload. */
export function LocatorMap({ focus, thumb = false }: { focus: MetroMeta; thumb?: boolean }) {
  return (
    <div className={thumb ? "rounded-md border border-rule bg-surface p-1" : "rounded-lg border border-rule bg-surface p-4"}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/map/${focus.cbsa}.svg`}
        width={620}
        height={400}
        alt={`Map of the United States with ${focus.display_name_full} marked`}
        className="h-auto w-full"
        data-testid={thumb ? "locator-map-thumb" : "locator-map"}
      />
    </div>
  );
}
