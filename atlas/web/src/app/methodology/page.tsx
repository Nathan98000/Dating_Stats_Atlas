import { promises as fs } from "fs";
import path from "path";
import { marked } from "marked";
import { apiMeta } from "@/lib/api";
import { Masthead } from "@/components/masthead";

export const dynamic = "force-dynamic";

/** The methodology page renders docs/methodology.md — versioned with
 * model_version — rather than paraphrasing it, then the provenance
 * register straight from the build manifest (gate 2: every number reaches
 * its provenance record in one click; the drill-down is a record, not
 * prose somebody typed). Attribution strings arrive from the typed license
 * registry through the manifest, so the counsel memo can change the
 * wording in one place. */

const ANCHORS: [RegExp, string][] = [
  [/margins of error/i, "margins"],
  [/^suppression/i, "suppression"],
  [/couples here actually pair/i, "pairing"],
  [/allocation purity/i, "purity"],
  [/terminology/i, "terminology"],
  [/findings the spec/i, "findings"],
  [/provenance/i, "provenance"],
];

function renderMarkdown(md: string): string {
  const renderer = new marked.Renderer();
  renderer.heading = ({ text, depth }) => {
    const plain = text.replace(/<[^>]+>/g, "");
    const anchor = ANCHORS.find(([re]) => re.test(plain))?.[1];
    const id = anchor ? ` id="${anchor}"` : "";
    return `<h${depth}${id}>${text}</h${depth}>`;
  };
  return marked.parse(md, { renderer, async: false }) as string;
}

export default async function MethodologyPage() {
  const meta = await apiMeta();
  // synced verbatim from docs/methodology.md by scripts/sync_content.mjs
  // (predev/prebuild) — the page renders the versioned file, not a copy
  // someone edited by hand
  const mdPath = path.join(process.cwd(), "content", "methodology.md");
  const md = await fs.readFile(mdPath, "utf-8");
  const html = renderMarkdown(md);
  const features = meta.pillar_order
    .flatMap((p) =>
      Object.entries(meta.features).filter(([, e]) => e.pillar === p),
    )
    .concat(
      Object.entries(meta.features).filter(
        ([, e]) => !meta.pillar_order.includes(e.pillar),
      ),
    );

  return (
    <>
      <Masthead dataVersion={meta.data_version} modelVersion={meta.model_version} />
      <main id="main" className="mx-auto max-w-4xl px-5">
        <article
          className="prose-method"
          // the versioned methodology text, rendered verbatim from the repo
          dangerouslySetInnerHTML={{ __html: html }}
        />

        <section id="versions" className="mt-10 border-t border-rule pt-6">
          <h2 className="font-serif text-2xl font-semibold">
            Two version numbers, both in every permalink
          </h2>
          <p className="mt-2 max-w-[68ch] text-sm text-ink-2">
            A ranking can change for two unrelated reasons, and telling them
            apart is the point. <strong className="text-ink">data_version</strong>{" "}
            (<span className="num">{meta.data_version}</span>) is the immutable
            build ID pinning every source vintage;{" "}
            <strong className="text-ink">model_version</strong>{" "}
            (<span className="num">{meta.model_version}</span>) versions the
            scoring model, pillar set, weights and suppression policy. A
            permalink carries both plus the preference vector, so any ranking
            this site ever produced can be reproduced exactly — or refused
            with an explanation, never silently substituted.
          </p>
        </section>

        <section className="mt-10 border-t border-rule pt-6">
          <h2 className="font-serif text-2xl font-semibold">
            Provenance register
          </h2>
          <p className="mt-2 max-w-[68ch] text-sm text-ink-2">
            Every stat on the site, with the exact record the build manifest
            carries for it. These are rendered from the manifest of build{" "}
            <span className="num">{meta.data_version}</span>, not written by
            hand.
          </p>
          <dl className="mt-4 flex flex-col gap-6">
            {features.map(([id, f]) => {
              const lic = meta.licenses[f.provenance.source];
              return (
                <div key={id} id={`f-${id}`} className="border-l-2 border-rule pl-4">
                  <dt className="font-semibold text-ink">
                    {f.display_name}
                    <span className="ml-2 text-xs font-normal text-ink-3">
                      {f.unit}
                      {f.status !== "active" ? ` · ${f.status.replace("_", " ")}` : ""}
                    </span>
                  </dt>
                  <dd className="mt-1 text-sm text-ink-2">
                    <p className="max-w-[68ch]">{f.definition}</p>
                    <table className="num mt-2 text-xs">
                      <caption className="sr-only">Provenance record for {f.display_name}</caption>
                      <tbody>
                        {(
                          [
                            ["source", f.provenance.source],
                            ["dataset", f.provenance.dataset],
                            ["table", f.provenance.table],
                            ["variables", f.provenance.variables.join(", ") || "—"],
                            ["geography", f.provenance.geography],
                            ["vintage", f.provenance.vintage],
                            ["transform", f.provenance.transform_id],
                            ["tier", f.provenance.tier],
                          ] as const
                        ).map(([k, v]) => (
                          <tr key={k}>
                            <th scope="row" className="pr-4 text-left font-semibold text-ink-3">
                              {k}
                            </th>
                            <td>{String(v)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {lic && (
                      <p className="mt-1 text-xs text-ink-3">
                        {lic.attribution ?? lic.name} ·{" "}
                        <a className="text-accent underline underline-offset-2" href={lic.url} rel="noopener">
                          license
                        </a>
                        {lic.notes ? ` — ${lic.notes}` : ""}
                      </p>
                    )}
                  </dd>
                </div>
              );
            })}
          </dl>
        </section>
      </main>
    </>
  );
}
