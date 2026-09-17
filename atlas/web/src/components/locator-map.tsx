import type { MetroMeta } from "@/lib/types";

/** The city page's locator (MetroV3): every one of the 387 metros as a
 * faint dot at its real coordinates — the dots themselves draw the
 * country — with this city in accent. Pure presentation geometry over
 * positions the build carries; Alaska and Hawaii sit in the customary
 * insets. */
const W = 300;
const H = 180;
const CONUS = { latMin: 24.3, latMax: 49.5, lonMin: -125.0, lonMax: -66.5 };

function project(lat: number, lon: number): { x: number; y: number } | null {
  // Alaska inset (bottom left)
  if (lat > 50 && lon < -125) {
    const x = 8 + ((lon + 170) / 40) * 52;
    const y = 128 + ((72 - lat) / 22) * 44;
    return { x, y };
  }
  // Hawaii inset (next to Alaska)
  if (lat < 24 && lon < -150) {
    const x = 72 + ((lon + 161) / 7) * 30;
    const y = 150 + ((23 - lat) / 5) * 22;
    return { x, y };
  }
  if (lat < CONUS.latMin || lat > CONUS.latMax) return null;
  const kx = W / (CONUS.lonMax - CONUS.lonMin);
  const ky = (H - 24) / (CONUS.latMax - CONUS.latMin);
  return {
    x: (lon - CONUS.lonMin) * kx,
    y: (CONUS.latMax - lat) * ky + 4,
  };
}

export function LocatorMap({
  metros,
  focus,
}: {
  metros: MetroMeta[];
  focus: MetroMeta;
}) {
  const focusPt = project(focus.lat, focus.lon);
  return (
    <div className="rounded-xl border border-rule bg-surface p-4">
      <svg
        width="100%"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Map of the United States with ${focus.display_name_full} marked`}
      >
        {metros.map((m) => {
          if (m.cbsa === focus.cbsa) return null;
          const p = project(m.lat, m.lon);
          if (!p) return null;
          return (
            <circle key={m.cbsa} cx={p.x} cy={p.y} r="1.9" fill="var(--rule)" />
          );
        })}
        {focusPt && (
          <circle cx={focusPt.x} cy={focusPt.y} r="6" fill="var(--accent)" />
        )}
      </svg>
    </div>
  );
}
