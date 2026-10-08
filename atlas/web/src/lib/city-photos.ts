import "server-only";
import fs from "fs";
import path from "path";
import cityImages from "@/data/city-images.json";

/** Phase 5: which city photographs may be cropped, and their alt text.
 *
 * A crop is an adaptation, and an adapted CC-BY-SA photograph would drag
 * its licence onto the page — so a photo is cover-cropped (a featured
 * card, the city page's band) ONLY where it is public domain or CC0, the
 * rule hero.tsx applied; every other photo shows unmodified, or not at
 * all. A photo ships only through the committed manifest and only while
 * its file is on disk ("no file, no photo"). */

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

export function croppable(license: string): boolean {
  return /public domain|cc0/i.test(license);
}

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
  /** cover: cropped to the card (public domain or CC0 only); contain:
   * shown whole, unmodified, on --sunken (any other licence) */
  fit: "cover" | "contain";
}

/** Every city photo on disk, by slug, as the home page's featured cards
 * show it. After the Phase 5 report (Nathan): a card always shows the
 * city's photograph, never the locator map — cover-cropped where the
 * licence allows (every ranked city has such a photo since then), shown
 * whole otherwise. */
export function cardPhotos(): Record<string, CardPhoto> {
  const out: Record<string, CardPhoto> = {};
  for (const [slug, img] of Object.entries(IMAGES)) {
    if (onDisk(img)) {
      out[slug] = { src: `/cities/${img.file}`, alt: usableAlt(img),
                    fit: croppable(img.license) ? "cover" : "contain" };
    }
  }
  return out;
}
