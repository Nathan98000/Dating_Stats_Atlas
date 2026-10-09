
import { DEFAULT_FOCUS, IMAGES, onDisk, sized, usableAlt } from "@/lib/city-photos";
import { fill } from "@/lib/results";

/** Every city page gets a face. Since Phase 2e item 4 that face is a
 * real photograph wherever one CLEARED: sourced from the city's
 * Wikipedia lead image, licence read from the Commons API (public
 * domain, CC0, CC-BY, CC-BY-SA ship; NC/ND or unreadable terms refuse),
 * recorded row-by-row in the committed manifest. Its credit lives with
 * every other one in About us, Sources and credits. A photo ships ONLY
 * through the manifest: an unlisted file has no recorded licence and does
 * not render.
 *
 * Phase 5, after the report (Nathan): every city photograph is a
 * full-bleed 16:7 band, cover-cropped, credited "cropped" (public domain,
 * CC0, CC BY and CC BY-SA permit it; a photograph from elsewhere is used
 * by the permission Nathan arranges). The crop keeps more of a photograph's
 * top than its bottom (35% down, as the home page's cards do): towers and
 * domes rise, and roads, lawns and water sit low. The alt text is the
 * manifest's description unless that is a filename, a bare "image" or the
 * like — then "", since the h1 names the city. The generative fallback
 * stays aria-hidden. */

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const HUES = ["var(--tint)", "var(--sunken)", "var(--data-neutral)", "var(--good)",
  "var(--accent)", "var(--tint-border)"];

export function CityArt({ cbsa, slug, city, placeCaption }: {
  cbsa: string;
  slug: string;
  /** the city's short name and the registry's photo_place_caption, for a
   * photograph of a place elsewhere in the metro (Phase 6, F29) */
  city?: string;
  placeCaption?: string;
}) {
  const img = IMAGES[slug];
  if (img && onDisk(img)) {
    const alt = usableAlt(img);
    const s = sized("cities", slug, img.file);
    const caption = img.place_caption
      ?? (img.place && city && placeCaption ? fill(placeCaption, { place: img.place, city }) : null);
    return (
      <figure data-testid="city-photo" data-cropped="">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={s.src}
          srcSet={s.srcSet}
          sizes={s.srcSet ? "(min-width: 1120px) 1056px, calc(100vw - 32px)" : undefined}
          width={s.width}
          height={s.height}
          fetchPriority="high"
          loading="eager"
          alt={alt}
          className="aspect-[16/7] h-auto w-full rounded-lg object-cover"
          style={{ objectPosition: img.focus ?? DEFAULT_FOCUS }}
        />
        {caption && (
          <figcaption className="mt-2 text-caption text-ink-3" data-testid="photo-place">
            {caption}
          </figcaption>
        )}
      </figure>
    );
  }
  const rand = mulberry32(parseInt(cbsa, 10) * 2654435761);
  const W = 1200;
  const H = 300;
  const blobs = [];
  const n = 5 + Math.floor(rand() * 3);
  for (let i = 0; i < n; i++) {
    const cx = rand() * W;
    const cy = H * 0.35 + rand() * H * 0.75;
    const rx = 90 + rand() * 260;
    const ry = 50 + rand() * 130;
    const rot = Math.round((rand() - 0.5) * 40);
    const hue = HUES[Math.floor(rand() * HUES.length)];
    const op = 0.14 + rand() * 0.16;
    blobs.push(
      <ellipse
        key={i}
        cx={cx.toFixed(0)}
        cy={cy.toFixed(0)}
        rx={rx.toFixed(0)}
        ry={ry.toFixed(0)}
        fill={hue}
        opacity={op.toFixed(2)}
        transform={`rotate(${rot} ${cx.toFixed(0)} ${cy.toFixed(0)})`}
      />,
    );
  }
  const discX = W * (0.12 + rand() * 0.76);
  const discY = H * (0.2 + rand() * 0.25);
  const discR = 26 + rand() * 30;
  return (
    <div
      aria-hidden="true"
      data-testid="city-art"
      className="h-[200px] w-full overflow-hidden rounded-lg border border-rule max-sm:h-[140px]"
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid slice"
        className="h-full w-full"
        role="presentation"
        focusable="false"
      >
        <rect width={W} height={H} fill="var(--paper)" />
        {blobs}
        <circle cx={discX.toFixed(0)} cy={discY.toFixed(0)} r={discR.toFixed(0)}
          fill="var(--accent)" opacity="0.55" />
      </svg>
    </div>
  );
}
