import "server-only";
import fs from "fs";
import path from "path";
import cityImages from "@/data/city-images.json";
import photoSizes from "@/data/photo-sizes.json";

/** Phase 5: the city photographs, how they may be shown, and their alt
 * text.
 *
 * Phase 5 cropped only public-domain or CC0 photographs (an adapted
 * CC-BY-SA photograph must itself stay CC-BY-SA). After the Phase 5 report
 * (Nathan, 2026-10-08: the most representative photograph of each city,
 * from any source, with the permissions he arranges) every city photograph
 * may be cropped — the home page's cards and the city page's band — and
 * its credit says "cropped": public domain, CC0, CC BY and CC BY-SA each
 * permit the adaptation, and a photograph from elsewhere is used by
 * permission. A photo ships only through the committed manifest and only
 * while its file is on disk ("no file, no photo"). */

export interface CityImage {
  file: string;
  alt: string | null;
  author: string | null;
  license: string;
  license_url: string | null;
  source_url: string;
  title?: string;
  /** Phase 6 (§I): the photo's focal point, an object-position value, used
   * by the card, the band and the link-preview crop; default "50% 35%" */
  focus?: string;
  /** Phase 6 (F29): the place the photograph shows, when that is
   * elsewhere in its metro ("Daytona Beach" for Deltona), and a caption
   * that is not the registry's template (Santa Maria's vineyards) */
  place?: string;
  place_caption?: string;
}
export const IMAGES = cityImages as unknown as Record<string, CityImage>;

export function onDisk(img: CityImage): boolean {
  return fs.existsSync(path.join(process.cwd(), "public", "cities", img.file));
}

/** The manifest's alt text, unless it says nothing: a filename, "image",
 * or the file's own title — then "" (the page's heading names the city). */
export function usableAlt(img: CityImage): string {
  const alt = (img.alt ?? "").trim();
  if (!alt || /^(image|photo|picture|img)$/i.test(alt)) return "";
  if (!/\s/.test(alt) && /[\d_-]/.test(alt)) return "";          // a filename
  if (/\.(jpe?g|png|gif|tiff?|webp)$/i.test(alt)) return "";
  if (img.title && alt.toLowerCase() === img.title.toLowerCase() && !/\s/.test(alt)) return "";
  return alt;
}

/** Phase 6 (commit A, F03): what photo_sizes.mjs wrote for a photograph —
 * its natural size and the widths of its WebP copies (public/<group>/w/
 * <slug>-<w>.webp), from src/data/photo-sizes.json. */
interface PhotoSize {
  width: number;
  height: number;
  widths: number[];
}
const SIZES = photoSizes as unknown as Record<string, Record<string, PhotoSize>>;
export const DEFAULT_FOCUS = "50% 35%";

/** The <img> attributes that deliver a photograph at the size it is shown:
 * the original as src, the WebP copies as srcset, and its natural width
 * and height. A slug missing from photo-sizes.json renders as before (the
 * original alone): the CI case, where there are no photographs. */
export interface Sized {
  src: string;
  srcSet?: string;
  width?: number;
  height?: number;
}
export function sized(group: "cities" | "stats", slug: string, file: string): Sized {
  const src = `/${group}/${file}`;
  const s = SIZES[group]?.[slug];
  if (!s) return { src };
  // an original narrower than the largest copy (2048) and wider than its
  // own largest copy is itself the top candidate, so a wide screen never
  // gets less than the photograph has
  const cands = s.widths.map((w) => `/${group}/w/${slug}-${w}.webp ${w}w`);
  if (s.width > Math.max(0, ...s.widths) && s.width < 2048) cands.push(`${src} ${s.width}w`);
  const srcSet = s.widths.length ? cands.join(", ") : undefined;
  return { src, srcSet, width: s.width, height: s.height };
}

/** The 1200x630 link-preview crop photo_sizes.mjs wrote, if it did. */
export function ogImage(group: "cities" | "stats", slug: string): string | null {
  if (!SIZES[group]?.[slug]) return null;
  return fs.existsSync(path.join(process.cwd(), "public", group, "og", `${slug}.jpg`))
    ? `/${group}/og/${slug}.jpg` : null;
}

export interface CardPhoto extends Sized {
  alt: string;
  focus: string;
}

/** Every city photo on disk, by slug, as the home page's featured cards
 * show it (cover-cropped). After the Phase 5 report (Nathan): a card
 * always shows the city's photograph, never the locator map. */
export function cardPhotos(): Record<string, CardPhoto> {
  const out: Record<string, CardPhoto> = {};
  for (const [slug, img] of Object.entries(IMAGES)) {
    if (onDisk(img)) {
      out[slug] = { ...sized("cities", slug, img.file), alt: usableAlt(img), focus: img.focus ?? DEFAULT_FOCUS };
    }
  }
  return out;
}
