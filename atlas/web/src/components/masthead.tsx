import Link from "next/link";
import { Suspense } from "react";
import { SearchBox } from "./search";

export function Masthead({
  dataVersion,
  modelVersion,
  brandAsH1 = false,
}: {
  dataVersion: string;
  modelVersion: string;
  brandAsH1?: boolean;
}) {
  const Brand = brandAsH1 ? "h1" : "p";
  return (
    <header className="mx-auto max-w-6xl px-5 pb-6 pt-8">
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4 border-b-2 border-ink pb-4">
        <div>
          <Brand className="font-serif text-3xl font-semibold tracking-tight">
            <Link href="/">Dating Stats Atlas</Link>
          </Brand>
          <p className="mt-1 max-w-[56ch] text-sm text-ink-2">
            Where the people you are looking for actually live — counted from
            Census microdata, with the uncertainty on every number.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Suspense fallback={<div className="h-8 w-64" />}>
            <SearchBox />
          </Suspense>
          <p className="num text-xs text-ink-3">
            data {dataVersion} · model {modelVersion}
          </p>
        </div>
      </div>
    </header>
  );
}
