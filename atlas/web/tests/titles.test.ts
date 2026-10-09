import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import path from "path";
import { CHROME, pageMetadata, pageTitle, resultsTitle } from "../src/lib/chrome";
import { fill } from "../src/lib/results";

describe("page titles (Phase 5)", () => {
  it("names the page, then the site", () => {
    expect(pageTitle("San Francisco, CA")).toBe("San Francisco, CA · Dating Stats Atlas");
    expect(pageTitle(fill(CHROME.title_compare_pair, { a: "Boston, MA", b: "Austin, TX" })))
      .toBe("Boston, MA vs Austin, TX · Dating Stats Atlas");
    expect(pageTitle(fill(CHROME.title_stat, { stat: "Rent" }))).toBe("Rent by city · Dating Stats Atlas");
    expect(pageTitle(CHROME.about_title)).toBe("How it works · Dating Stats Atlas");
    expect(pageTitle(CHROME.title_privacy)).toBe("Privacy · Dating Stats Atlas");
    expect(pageTitle(CHROME.title_terms)).toBe("Terms · Dating Stats Atlas");
    expect(pageTitle()).toBe("Dating Stats Atlas");
  });
  it("carries Open Graph tags, an image only when given", () => {
    const m = pageMetadata("T", "D", "/city/x");
    expect(m.openGraph).toMatchObject({ title: "T", description: "D", url: "/city/x" });
    expect("images" in m.openGraph).toBe(false);
    // Phase 6 (F31): every image is a 1200x630 link preview, shown large
    const withImage = pageMetadata("T", "D", "/", "/cities/og/x.jpg");
    expect(withImage.openGraph.images).toEqual([{ url: "/cities/og/x.jpg", width: 1200, height: 630 }]);
    expect(withImage.twitter).toMatchObject({ card: "summary_large_image", images: ["/cities/og/x.jpg"] });
    expect(m.twitter).toMatchObject({ card: "summary" });
  });
});

describe("a shared result's title (Phase 6, F31)", () => {
  // the registry's own template, read from features.yaml
  const yaml = readFileSync(path.resolve(__dirname, "..", "..", "pipeline", "registry", "features.yaml"), "utf8");
  const template = yaml.match(/^\s*title_results: "(.*)"$/m)![1];
  it("is the results heading, then the site, without the heading's word joiners", () => {
    expect(template).toBe("{heading} · Dating Stats Atlas");
    expect(resultsTitle({ title_results: template }, "Top cities for single men, 28\u2060–\u206040"))
      .toBe("Top cities for single men, 28–40 · Dating Stats Atlas");
    expect(resultsTitle({ title_results: template }, "Lowest-scoring cities for single women, 25\u2060–\u206035"))
      .toBe("Lowest-scoring cities for single women, 25–35 · Dating Stats Atlas");
  });
});
