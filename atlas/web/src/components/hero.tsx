import fs from "fs";
import path from "path";

/** The home hero (HomeV3): a full-bleed image band over the headline.
 * The image is Nathan's to supply — drop it at web/public/hero.jpg
 * (about 2560×680, shown ~1280×340, wide crop, faces small, documentary
 * not stock). Until it exists, the board's labelled placeholder ships;
 * this component never sources an image itself. */
export function Hero() {
  const heroExists = fs.existsSync(
    path.join(process.cwd(), "public", "hero.jpg"),
  );
  return (
    <section>
      {heroExists ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src="/hero.jpg"
          alt=""
          className="h-[340px] w-full object-cover max-sm:h-[220px]"
        />
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
        <h1 className="max-w-[24ch] text-balance font-display text-[44px] font-semibold leading-[1.08] tracking-tight max-sm:text-[32px]">
          Where would you meet more people you&rsquo;d actually click with?
        </h1>
        <p className="max-w-[64ch] text-[16.5px] leading-relaxed text-ink-2">
          Tell us who you&rsquo;re looking for and what matters to you.
          We&rsquo;ll count how many of them live in each US city — using the
          same Census survey the government uses to count everyone.
        </p>
      </div>
    </section>
  );
}
