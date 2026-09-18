import crypto from "crypto";
import fs from "fs";
import path from "path";
import { Attribution } from "./attribution";

/** The home hero (HomeV3, real since Phase 2f item 4.1): a photograph
 * sourced through the Phase 2e image pipeline with its licence gate,
 * shipped at web/public/hero.jpg and recorded row-for-row in the
 * committed manifest (results/phase2f/hero_image.csv -> src/data/
 * hero.json). The hero is a cropped band, and a crop of a CC-BY-SA
 * image is an adaptation that drags ShareAlike onto the page — so the
 * band crop (object-cover) is allowed ONLY for public-domain/CC0; any
 * attributed licence would render uncropped instead. Attribution
 * renders beneath the band, exactly as the stat pages do.
 *
 * Nathan's override stays: drop a different file at public/hero.jpg and
 * it renders — but the manifest's attribution only renders while the
 * file on disk IS the manifest's file (SHA-256 match), so a swapped
 * image can never wear the sourced image's credit. No file, no photo:
 * the labelled placeholder ships. Headline and subhead arrive from the
 * registry (items 4.2/4.3) — no user-facing string lives here. */

interface HeroImage {
  file: string;
  sha256: string;
  alt: string | null;
  author: string | null;
  license: string;
  license_url: string | null;
  source_url: string;
}

const shaCache = new Map<string, string>();

function heroState(): { exists: boolean; manifest: HeroImage | null;
                        matches: boolean } {
  const file = path.join(process.cwd(), "public", "hero.jpg");
  let stat: fs.Stats;
  try {
    stat = fs.statSync(file);
  } catch {
    return { exists: false, manifest: null, matches: false };
  }
  let manifest: HeroImage | null = null;
  try {
    manifest = JSON.parse(fs.readFileSync(
      path.join(process.cwd(), "src", "data", "hero.json"), "utf-8"));
  } catch {
    manifest = null;
  }
  if (!manifest) return { exists: true, manifest: null, matches: false };
  const key = `${stat.mtimeMs}:${stat.size}`;
  let sha = shaCache.get(key);
  if (!sha) {
    sha = crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
    shaCache.clear();
    shaCache.set(key, sha);
  }
  return { exists: true, manifest, matches: sha === manifest.sha256 };
}

export function Hero({ policy }: { policy: Record<string, string> }) {
  const hero = heroState();
  // the band crop is an adaptation, permitted only where no ShareAlike
  // or attribution term can attach (public domain / CC0)
  const cropOk = hero.matches && hero.manifest !== null &&
    /public domain|cc0/i.test(hero.manifest.license);
  return (
    <section>
      {hero.exists ? (
        <figure data-testid="hero-photo">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/hero.jpg"
            alt={(hero.matches && hero.manifest?.alt) || ""}
            className={
              cropOk || !hero.matches
                ? "h-[340px] w-full object-cover max-sm:h-[220px]"
                : "max-h-[380px] w-full bg-surface object-contain"
            }
          />
          {hero.matches && hero.manifest && (
            <figcaption className="px-6 pt-1.5 text-right sm:px-12">
              <Attribution image={hero.manifest} />
            </figcaption>
          )}
        </figure>
      ) : (
        <div
          aria-hidden="true"
          className="flex h-[340px] w-full flex-col items-center justify-center gap-1.5 border-b border-t border-dashed border-tint-border bg-tint max-sm:h-[220px]"
          data-testid="hero-placeholder"
        >
          <span className="text-[13px] font-bold text-accent-hover">
            Photo to source · 1280 × 340
          </span>
          <span className="max-w-[52ch] px-6 text-center text-[12.5px] text-ink-2">
            Two people laughing on a city street — documentary-feeling, not
            glossy stock. Wide crop, faces small, city legible behind them.
          </span>
        </div>
      )}
      <div className="mx-auto flex max-w-6xl flex-col gap-3.5 px-6 pb-10 pt-10 sm:px-12">
        <h1 className="max-w-[26ch] text-balance font-display text-[44px] font-semibold leading-[1.08] tracking-tight max-sm:text-[32px]">
          {policy.home_title}
        </h1>
        <p className="max-w-[64ch] text-[16.5px] leading-relaxed text-ink-2">
          {policy.home_subtitle}
        </p>
      </div>
    </section>
  );
}
