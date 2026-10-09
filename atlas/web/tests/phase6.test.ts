/** Phase 6 (the round-3 review): the search's plain words. */
import { describe, expect, it } from "vitest";
import { DEFAULT_PREFS, describeSearch, type Prefs } from "../src/lib/prefs";

const prefs = (over: Partial<Prefs>): Prefs => ({ ...DEFAULT_PREFS, ...over });

describe("describeSearch's marital phrase (F34)", () => {
  it("names both statuses in brackets after the single sought sex and ages", () => {
    expect(describeSearch(prefs({}))).toBe("Single men 28–40 (never married, divorced or widowed)");
  });
  it("names one status alone", () => {
    expect(describeSearch(prefs({ seekSex: "female", ageMin: 25, ageMax: 35, marital: ["never_married"] })))
      .toBe("Single women 25–35 (never married)");
    expect(describeSearch(prefs({ marital: ["previously_married"] })))
      .toBe("Single men 28–40 (divorced or widowed)");
  });
  it("keeps education and income after the brackets", () => {
    expect(describeSearch(prefs({ educationMin: "graduate", incomeMin: 100000 })))
      .toBe("Single men 28–40 (never married, divorced or widowed), with a graduate degree, earning $100,000 or more");
  });
});
