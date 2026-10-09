import "server-only";
import fs from "fs";
import path from "path";
import cityImages from "@/data/city-images.json";

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

export interface CardPhoto {
  src: string;
  alt: string;
}

/** Every city photo on disk, by slug, as the home page's featured cards
 * show it (cover-cropped). After the Phase 5 report (Nathan): a card
 * always shows the city's photograph, never the locator map. */
export function cardPhotos(): Record<string, CardPhoto> {
  const out: Record<string, CardPhoto> = {};
  for (const [slug, img] of Object.entries(IMAGES)) {
    if (onDisk(img)) out[slug] = { src: `/cities/${img.file}`, alt: usableAlt(img) };
  }
  return out;
}
