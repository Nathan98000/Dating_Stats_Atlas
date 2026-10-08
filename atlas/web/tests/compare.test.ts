import { describe, expect, it } from "vitest";
import { edgeOf, parseDisplayed } from "../src/lib/compare";

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
