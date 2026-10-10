import { describe, expect, it } from "vitest";
import {
  balanceDots, divergingBar, fill, INITIAL_VISIBLE, showMore, visibleSlice, visibleToInclude,
} from "../src/lib/results";
import { DEFAULT_PREFS, describeChange, describeSearchShort, filtersSummary } from "../src/lib/prefs";

const rows = Array.from({ length: 193 }, (_, i) => i + 1);

describe("visible slicing (Phase 5)", () => {
  it("opens with three featured cards and seven rows", () => {
    const { featured, rest } = visibleSlice(rows, INITIAL_VISIBLE);
    expect(featured).toEqual([1, 2, 3]);
    expect(rest).toEqual([4, 5, 6, 7, 8, 9, 10]);
  });
  it("adds ten at a time and stops at the end", () => {
    expect(showMore(10, 193)).toBe(20);
    expect(showMore(190, 193)).toBe(193);
    expect(visibleSlice(rows, showMore(10, 193)).rest).toHaveLength(17);
  });
  it("a short list shows what there is", () => {
    expect(visibleSlice([1, 2], 10)).toEqual({ featured: [1, 2], rest: [] });
  });
  it("finding a city widens the list to include it, never narrows it", () => {
    expect(visibleToInclude(10, 41)).toBe(42);
    expect(visibleToInclude(50, 4)).toBe(50);
  });
});

describe("balance dots (2026-10-10)", () => {
  it("draws one dot for every ten, the last filled to the fraction", () => {
    expect(balanceDots(100)).toEqual({ full: 10, part: 0, beyond: false });
    expect(balanceDots(118)).toEqual({ full: 11, part: 0.8, beyond: false });
    expect(balanceDots(85)).toEqual({ full: 8, part: 0.5, beyond: false });
  });
  it("clamps to four and sixteen dots, marking a figure past the row", () => {
    expect(balanceDots(20)).toEqual({ full: 4, part: 0, beyond: false });
    expect(balanceDots(160)).toEqual({ full: 16, part: 0, beyond: false });
    expect(balanceDots(240)).toEqual({ full: 16, part: 0, beyond: true });
  });
});

describe("diverging bars", () => {
  it("draws plus to the right and minus to the left, ±25 points to the edge", () => {
    expect(divergingBar(12.5)).toEqual({ left: 0.5, width: 0.25 });
    expect(divergingBar(-12.5)).toEqual({ left: 0.25, width: 0.25 });
    expect(divergingBar(40)).toEqual({ left: 0.5, width: 0.5 });
    expect(divergingBar(-40)).toEqual({ left: 0, width: 0.5 });
  });
});

describe("describeSearchShort and the summaries", () => {
  it("names the sought sex and the ages", () => {
    expect(describeSearchShort(DEFAULT_PREFS)).toEqual({ sought: "men", ages: "28\u2060–\u206040" });
    expect(describeSearchShort({ ...DEFAULT_PREFS, seekSex: "female", ageMin: 25, ageMax: 33 }))
      .toEqual({ sought: "women", ages: "25\u2060–\u206033" });
  });
  it("fills the results heading", () => {
    expect(fill("Top cities for single {sought}, {ages}", describeSearchShort(DEFAULT_PREFS)))
      .toBe("Top cities for single men, 28\u2060–\u206040");
    expect(fill("{n} metro areas", { n: "193" })).toBe("193 metro areas");
    expect(fill("{a} and {missing}", { a: 1 })).toBe("1 and {missing}");
  });
  it("summarises the partner filters", () => {
    expect(filtersSummary(DEFAULT_PREFS)).toBe(
      "Single: never married or divorced/widowed · Any education · Any income · All races");
    expect(filtersSummary({ ...DEFAULT_PREFS, marital: ["never_married"], educationMin: "graduate",
      incomeMin: 75000, race: ["hispanic", "white_nh"] })).toBe(
      "Single: never married · Graduate degree · Earning $75,000+ · 2 of 8 groups");
  });
  it("names the change for the live region", () => {
    expect(describeChange(DEFAULT_PREFS, { ...DEFAULT_PREFS, ageMax: 45 })).toBe("ages 28–45");
    expect(describeChange(DEFAULT_PREFS, { ...DEFAULT_PREFS, sort: "worst_first" })).toBe("worst first");
    expect(describeChange(DEFAULT_PREFS, DEFAULT_PREFS)).toBe("your search");
  });
});
