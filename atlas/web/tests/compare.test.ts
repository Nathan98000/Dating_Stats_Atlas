import { describe, expect, it } from "vitest";
import { edgeOf, leadOf, noEdgeText, parseDisplayed } from "../src/lib/compare";
import { fill } from "../src/lib/results";

describe("the Edge decision (Phase 5)", () => {
  it("names the left city when d x direction > 0, the right when < 0", () => {
    expect(edgeOf("120", "100", 1)).toBe(1);
    expect(edgeOf("100", "120", 1)).toBe(-1);
    // rent: lower is better (direction -1)
    expect(edgeOf("1,500", "2,100", -1)).toBe(1);
    expect(edgeOf("2,100", "1,500", -1)).toBe(-1);
    // spot in the results: a smaller rank is better
    expect(edgeOf("3", "12", -1)).toBe(1);
  });
  it("judges nothing when grey, without a direction, equal or missing", () => {
    expect(edgeOf("120", "100", 1, true)).toBe(0);
    expect(edgeOf("120", "100", 0)).toBe(0);
    expect(edgeOf("100", "100", 1)).toBe(0);
    expect(edgeOf(undefined, "100", 1)).toBe(0);
    expect(edgeOf("100", undefined, 1)).toBe(0);
  });
  it("reads displayed values as the visitor sees them", () => {
    expect(parseDisplayed("1,010,198")).toBe(1010198);
    expect(parseDisplayed("4.6 million")).toBe(4600000);
    expect(parseDisplayed("$2,907")).toBe(2907);
    expect(edgeOf("4.6 million", "5 million", 1)).toBe(-1);
  });
});

describe("the size of the lead (Phase 6, F07)", () => {
  it("is the absolute value of the same subtraction, formatted as the values are", () => {
    expect(fill("by {diff}", { diff: leadOf("234,507", "266,309", 0) })).toBe("by 31,802");
    expect(fill("by {diff}", { diff: leadOf("$1,712", "$1,186", 0, true) })).toBe("by $526");
    expect(fill("by {diff}", { diff: leadOf("12.4", "9.8", 1) })).toBe("by 2.6");
    expect(fill("by {n} places", { n: leadOf("11", "9", 0) })).toBe("by 2 places");
  });
  it("never carries a sign, whichever side leads", () => {
    expect(leadOf("100", "120", 0)).toBe(leadOf("120", "100", 0));
    expect(leadOf("4.6 million", "5 million", 0)).toBe("400,000");
  });
});

describe("rows with no edge (Phase 7, R14)", () => {
  const names: [string, string] = ["Austin", "Denver"];
  it("a tie reads Same", () => {
    expect(noEdgeText("125", "125", 0, names, "Same", "{city}, by {diff}")).toBe("Same");
    expect(noEdgeText("$1,186", "$1,186", 0, names, "Same", "{city}, by {diff}", true)).toBe("Same");
  });
  it("an unjudged row names the larger city and the gap, the absolute value of the same subtraction", () => {
    expect(noEdgeText("2.4 million", "3 million", 0, names, "Same", "{city}, by {diff}")).toBe("Denver, by 600,000");
    expect(noEdgeText("3 million", "2.4 million", 0, names, "Same", "{city}, by {diff}")).toBe("Austin, by 600,000");
    expect(noEdgeText("234,507", "266,309", 0, names, "Same", "{city}, by {diff}")).toBe("Denver, by 31,802");
  });
  it("a value that doesn't parse reads nothing", () => {
    expect(noEdgeText("—", "12", 0, names, "Same", "{city}, by {diff}")).toBe("");
  });
});
