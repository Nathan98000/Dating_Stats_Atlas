
import { croppable, IMAGES, onDisk, usableAlt } from "@/lib/city-photos";

/** Every city page gets a face. Since Phase 2e item 4 that face is a
 * real photograph wherever one CLEARED: sourced from the city's
 * Wikipedia lead image, licence read from the Commons API (public
 * domain, CC0, CC-BY, CC-BY-SA ship; NC/ND or unreadable terms refuse),
 * recorded row-by-row in the committed manifest. Its credit lives with
 * every other one in About us, Sources and credits. A photo ships ONLY
 * through the manifest: an unlisted file has no recorded licence and does
 * not render.
 *
 * Phase 5: a public-domain or CC0 photograph may be cropped — a full-
 * bleed 16:7 band, cover-cropped (credited "cropped"); any other licence
 * shows the photograph UNMODIFIED, at its own width up to 380px tall,
 * centred on --sunken, with no card around it and no bars beside it (an
 * adapted CC-BY-SA image would drag its licence onto the adaptation). The
 * alt text is the manifest's description unless that is a filename, a
 * bare "image" or the like — then "", since the h1 names the city. The
 * generative fallback stays aria-hidden. */

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

export function CityArt({ cbsa, slug }: { cbsa: string; slug: string }) {
  const img = IMAGES[slug];
  if (img && onDisk(img)) {
    const alt = usableAlt(img);
    return croppable(img.license) ? (
      <figure data-testid="city-photo" data-cropped="">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/cities/${img.file}`}
          alt={alt}
          className="aspect-[16/7] w-full rounded-lg object-cover"
        />
      </figure>
    ) : (
      <figure data-testid="city-photo" className="flex justify-center rounded-lg bg-sunken">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/cities/${img.file}`}
          alt={alt}
          className="max-h-[380px] w-auto max-w-full"
        />
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
