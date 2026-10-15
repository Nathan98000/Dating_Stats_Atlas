/** Phase 8 (the round-4 review's remaining findings, Nathan's go of 15
 * October 2026). */
import { describe, expect, it } from "vitest";
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
