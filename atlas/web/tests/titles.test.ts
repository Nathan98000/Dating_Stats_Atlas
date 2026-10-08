import { describe, expect, it } from "vitest";
import { CHROME, pageMetadata, pageTitle } from "../src/lib/chrome";
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
    expect(pageMetadata("T", "D", "/", "/cities/x.jpg").openGraph.images).toEqual([{ url: "/cities/x.jpg" }]);
  });
});
