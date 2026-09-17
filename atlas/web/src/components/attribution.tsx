/** The licence-required attribution line (Phase 2e item 4), rendered as
 * the licence asks: author, licence name, a link to the licence deed,
 * and a link to the source file. The parts come from the committed image
 * manifest via the build JSON — the page renders them, never recomposes
 * or paraphrases them. Small but real. */
export function Attribution({
  image,
}: {
  image: { author: string | null; license: string;
           license_url: string | null; source_url: string };
}) {
  return (
    <span className="text-[11.5px] leading-snug text-ink-3">
      {image.author ? <>{image.author} · </> : null}
      {image.license_url ? (
        <a
          href={image.license_url}
          rel="noopener"
          className="underline underline-offset-2 hover:text-ink-2"
        >
          {image.license}
        </a>
      ) : (
        image.license
      )}
      {" · "}
      <a
        href={image.source_url}
        rel="noopener"
        className="underline underline-offset-2 hover:text-ink-2"
      >
        source
      </a>
    </span>
  );
}
