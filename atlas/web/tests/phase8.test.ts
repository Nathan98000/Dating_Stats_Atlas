/** Phase 8 (the round-4 review's remaining findings, Nathan's go of 15
 * October 2026). */
import { afterEach, describe, expect, it, vi } from "vitest";
import { readdirSync, readFileSync, statSync } from "fs";
import path from "path";
import ts from "typescript";
import cityImages from "../src/data/city-images.json";

const SRC = path.resolve(__dirname, "..", "src");

/** Every JSX text node with letters, and every literal user-facing
 * attribute (aria-label, placeholder, title, alt, label, closeLabel,
 * edgeLabel, menuLabel) or `label:`/`title:` property, in the files under
 * `dir`. */
function literals(dir: string): string[] {
  const ATTRS = new Set(["aria-label", "placeholder", "title", "alt", "label", "closeLabel",
    "edgeLabel", "menuLabel"]);
  const out: string[] = [];
  const scan = (file: string) => {
    const src = ts.createSourceFile(file, readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true,
      ts.ScriptKind.TSX);
    const at = (n: ts.Node) => `${path.relative(SRC, file)}:${src.getLineAndCharacterOfPosition(n.getStart()).line + 1}`;
    const visit = (n: ts.Node) => {
      if (ts.isJsxText(n)) {
        const t = n.getText().replace(/\s+/g, " ").trim();
        if (/[A-Za-z]{2,}/.test(t)) out.push(`${at(n)} ${t}`);
      } else if (ts.isJsxAttribute(n) && ATTRS.has(n.name.getText()) && n.initializer
        && ts.isStringLiteral(n.initializer) && /[A-Za-z]{2,}/.test(n.initializer.text)) {
        out.push(`${at(n)} ${n.name.getText()}="${n.initializer.text}"`);
      } else if (ts.isPropertyAssignment(n) && ["label", "title"].includes(n.name.getText())
        && ts.isStringLiteral(n.initializer) && /[A-Za-z]{2,}/.test(n.initializer.text)) {
        out.push(`${at(n)} ${n.name.getText()}: "${n.initializer.text}"`);
      }
      ts.forEachChild(n, visit);
    };
    visit(src);
  };
  const walk = (d: string) => {
    for (const f of readdirSync(d)) {
      const p = path.join(d, f);
      if (statSync(p).isDirectory()) walk(p);
      else if (p.endsWith(".tsx")) scan(p);
    }
  };
  walk(dir);
  return out;
}

describe("the registry owns every word the components show (R15)", () => {
  it("no component or page writes visible text or a label of its own", () => {
    expect([...literals(path.join(SRC, "components")), ...literals(path.join(SRC, "app"))]).toEqual([]);
  });
});

describe("every city photograph has a description a screen reader can use (R13)", () => {
  const imgs = cityImages as unknown as Record<string, { alt?: string | null }>;
  const RAW = /File:|Title:|Physical description|https?:\/\/|\bw:|\ben:|\(pop\.|\.(jpe?g|png|tiff?|webp)\b|^image$/i;

  it("no description is a file name, a catalogue record, wiki markup, a web address or a stray figure", () => {
    const bad = Object.entries(imgs).filter(([, v]) => RAW.test((v.alt ?? "").trim())).map(([k]) => k);
    expect(bad).toEqual([]);
  });

  it("no description is empty or only a few words", () => {
    // the shortest that still says what is in the picture is three words
    // ("Sidney Lanier Bridge"); a place's name alone is gone
    const short = Object.entries(imgs).filter(([, v]) => (v.alt ?? "").trim().split(/\s+/).length < 3)
      .map(([k]) => k);
    expect(short).toEqual([]);
  });

  it("the review's two ranked cities read as written for them", () => {
    expect(imgs["indianapolis-indiana"].alt).toMatch(/^Downtown Indianapolis from above/);
    expect(imgs["montgomery-alabama"].alt).toMatch(/^Downtown Montgomery from the air/);
  });
});

// ---------------------------------------------------------------- B (R23, R18)

describe("the starting search is kept once per build; every other search is asked for afresh (R23)", () => {
  /** A fresh copy of lib/api (its kept search lives as long as the server
   * process) over a stand-in API: meta answers `build`, rank answers its
   * call count, or `status` when that isn't 200. */
  async function load() {
    vi.resetModules();
    vi.doMock("server-only", () => ({}));
    const api = { build: { data_version: "d1", model_version: "m1" }, status: 200, ranks: [] as string[] };
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/v1/meta")) return Response.json(api.build);
      api.ranks.push(String(init?.body));
      if (api.status !== 200) return Response.json({ detail: "unavailable" }, { status: api.status });
      return Response.json({ call: api.ranks.length });
    }));
    const { apiRank } = await import("../src/lib/api");
    const { DEFAULT_PREFS, toRankBody } = await import("../src/lib/prefs");
    return { apiRank, api, start: toRankBody(DEFAULT_PREFS) };
  }
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.doUnmock("server-only");
  });

  it("the starting search: asked for once, however many pages want it at once; each gets its own copy", async () => {
    const { apiRank, api, start } = await load();
    const [a, b] = await Promise.all([apiRank(start), apiRank(start)]);
    const c = await apiRank(structuredClone(start));
    expect(api.ranks).toHaveLength(1);
    expect([a, b, c]).toEqual([{ call: 1 }, { call: 1 }, { call: 1 }]);
    expect(a).not.toBe(b);
  });

  it("any other search: asked for every time, never kept", async () => {
    const { apiRank, api, start } = await load();
    const other = { ...start, seeking: { ...start.seeking, age: [30, 45] as [number, number] } };
    await apiRank(other);
    await apiRank(other);
    expect(api.ranks).toHaveLength(2);
    await apiRank(start);
    await apiRank(other);
    expect(api.ranks).toHaveLength(4);
  });

  it("a failure is not kept: the next page asks again", async () => {
    const { apiRank, api, start } = await load();
    api.status = 503;
    await expect(apiRank(start)).rejects.toThrow("rank 503");
    api.status = 200;
    expect(await apiRank(start)).toEqual({ call: 2 });
    expect(await apiRank(start)).toEqual({ call: 2 });
  });

  it("a new build or model: asked for again", async () => {
    const { apiRank, api, start } = await load();
    await apiRank(start);
    api.build = { data_version: "d1", model_version: "m2" };
    expect(await apiRank(start)).toEqual({ call: 2 });
    api.build = { data_version: "d2", model_version: "m2" };
    expect(await apiRank(start)).toEqual({ call: 3 });
    expect(await apiRank(start)).toEqual({ call: 3 });
  });
});

describe("the site's Fraunces is the trimmed file (R18)", () => {
  const font = path.resolve(__dirname, "..", "src", "app", "fonts", "fraunces-latin.woff2");
  it("a woff2 under 64 KB, its licence beside it", () => {
    const bytes = readFileSync(font);
    expect(bytes.subarray(0, 4).toString("latin1")).toBe("wOF2");
    expect(bytes.length).toBeLessThan(64 * 1024);
    expect(readFileSync(path.join(path.dirname(font), "OFL.txt"), "utf8")).toMatch(/SIL OPEN FONT LICENSE Version 1\.1/);
  });
});
