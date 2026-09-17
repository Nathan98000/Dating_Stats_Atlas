import usMap from "@/data/us-map.json";
import type { MetroMeta } from "@/lib/types";

/** The city page's locator (Phase 2e item 3): a real map of the United
 * States with STATE BOUNDARIES — Census cartographic boundary geometry,
 * projected to Albers USA at build time and shipped as plain SVG path
 * strings, so no mapping library ever reaches the browser. Two fills
 * and one hairline: land, the metro's state, and the metro dot in the
 * accent, placed from the build's Census internal point. Flat, in the
 * palette; no terrain, no labels, no interactivity. */

const MAP = usMap as unknown as {
  w: number;
  h: number;
  states: { f: string; d: string }[];
  metros: Record<string, [number, number, string | null]>;
};

export function LocatorMap({ focus }: { focus: MetroMeta }) {
  const dot = MAP.metros[focus.cbsa];
  const homeState = dot?.[2] ?? null;
  return (
    <div className="rounded-xl border border-rule bg-surface p-4">
      <svg
        width="100%"
        viewBox={`0 0 ${MAP.w} ${MAP.h}`}
        role="img"
        aria-label={`Map of the United States with ${focus.display_name_full} marked`}
        data-testid="locator-map"
      >
        {MAP.states.map((s) => (
          <path
            key={s.f}
            d={s.d}
            fill={s.f === homeState ? "var(--tint)" : "var(--paper)"}
            stroke="var(--rule)"
            strokeWidth="0.75"
            strokeLinejoin="round"
            data-state={s.f === homeState ? "home" : undefined}
          />
        ))}
        {dot && <circle cx={dot[0]} cy={dot[1]} r="7" fill="var(--accent)" />}
      </svg>
    </div>
  );
}
