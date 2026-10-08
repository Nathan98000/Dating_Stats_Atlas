/** The home hero (Phase 5, Nathan's decision 1): the headline and the
 * subhead from the registry, and the quick search beneath them — no photo
 * band any more. public/hero.jpg and src/data/hero.json stay in the repo,
 * unused; the photo's credit left Sources and credits with it. A header
 * inside the page's main landmark. */
export function Hero({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <header className="pt-5 sm:pt-10" data-testid="hero">
      <h1 className="max-w-[17ch] text-balance font-display text-display-2">{title}</h1>
      <p className="mt-3 max-w-[58ch] text-body-lg text-ink-2 max-sm:text-body">{subtitle}</p>
      {children}
    </header>
  );
}
