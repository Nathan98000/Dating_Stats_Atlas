/** Phase 4b (ADR 0018 amended): race is one select whose default, "Prefer
 * not to say", stores nothing — a stored race means race is on. m4.0.0
 * stored the race switch beside the race ({raceOn, race}), and the race
 * counted only with the switch on and a group chosen; such an object
 * reads as exactly that choice without the switch, and is rewritten in the
 * current shape the first time it is read. */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  ABOUT_YOU_KEY,
  parseAboutYou,
  raceUsed,
  readAboutYou,
  writeAboutYou,
} from "../src/lib/about-you";

const RACES = ["hispanic", "white_nh", "black_nh", "asian_nh", "aian_nh",
  "nhpi_nh", "two_or_more_nh", "other_nh"];

class MemoryStorage {
  private items = new Map<string, string>();
  getItem(k: string): string | null {
    return this.items.has(k) ? (this.items.get(k) as string) : null;
  }
  setItem(k: string, v: string): void {
    this.items.set(k, v);
  }
  removeItem(k: string): void {
    this.items.delete(k);
  }
}

const g = globalThis as unknown as { window?: { localStorage: MemoryStorage } };
let store: MemoryStorage;

beforeEach(() => {
  store = new MemoryStorage();
  g.window = { localStorage: store };
});
afterEach(() => {
  delete g.window;
});

describe("the stored details", () => {
  it("a stored race means race is on; none means Prefer not to say", () => {
    expect(parseAboutYou({ sex: "male", race: "hispanic" })).toEqual({ sex: "male", race: "hispanic" });
    expect(raceUsed(parseAboutYou({ race: "hispanic" }))).toBe("hispanic");
    expect(raceUsed(parseAboutYou({ sex: "female", edu: "graduate" }))).toBeUndefined();
  });

  it("drops values the site does not offer", () => {
    expect(parseAboutYou({ sex: "other", edu: "phd", race: "martian" })).toEqual({});
    expect(parseAboutYou(null)).toEqual({});
    expect(parseAboutYou("female")).toEqual({});
  });

  it("an m4.0.0 object reads as the same choice without the switch", () => {
    expect(parseAboutYou({ sex: "female", edu: "graduate", raceOn: true, race: "asian_nh" }))
      .toEqual({ sex: "female", edu: "graduate", race: "asian_nh" });
    // switched on with no group chosen: the figure stayed race-free
    expect(parseAboutYou({ sex: "male", raceOn: true })).toEqual({ sex: "male" });
    // a switch that is off never carried a race into the figure
    expect(parseAboutYou({ raceOn: false, race: "asian_nh" })).toEqual({});
  });

  it("every m4.0.0 shape selects the race m4.0.0 used", () => {
    // m4.0.0's rule: the race counted only with the switch on and a group
    // chosen (lib/about-you at m4.0.0: raceOn && race)
    const m4 = (o: { raceOn?: unknown; race?: unknown }) =>
      o.raceOn === true && RACES.includes(o.race as string) ? o.race : undefined;
    for (const raceOn of [true, false, undefined, "yes"]) {
      for (const race of [...RACES, undefined, "martian"]) {
        const legacy: Record<string, unknown> = { sex: "female", raceOn };
        if (race !== undefined) legacy.race = race;
        expect(raceUsed(parseAboutYou(legacy)), JSON.stringify(legacy)).toBe(m4(legacy));
      }
    }
  });

  it("migrates a stored m4.0.0 object on read, rewriting it without the switch", () => {
    store.setItem(ABOUT_YOU_KEY,
      JSON.stringify({ sex: "female", edu: "graduate", raceOn: true, race: "asian_nh" }));
    expect(readAboutYou()).toEqual({ sex: "female", edu: "graduate", race: "asian_nh" });
    expect(JSON.parse(store.getItem(ABOUT_YOU_KEY) as string))
      .toEqual({ sex: "female", edu: "graduate", race: "asian_nh" });

    store.setItem(ABOUT_YOU_KEY, JSON.stringify({ raceOn: true }));
    expect(readAboutYou()).toEqual({});
    expect(store.getItem(ABOUT_YOU_KEY)).toBeNull();
  });

  it("leaves a current object as it is", () => {
    const current = JSON.stringify({ sex: "male", race: "black_nh" });
    store.setItem(ABOUT_YOU_KEY, current);
    expect(readAboutYou()).toEqual({ sex: "male", race: "black_nh" });
    expect(store.getItem(ABOUT_YOU_KEY)).toBe(current);
  });

  it("Prefer not to say removes the race from storage", () => {
    writeAboutYou({ sex: "female", race: "white_nh" });
    expect(JSON.parse(store.getItem(ABOUT_YOU_KEY) as string)).toEqual({ sex: "female", race: "white_nh" });
    writeAboutYou({ sex: "female", race: undefined });
    expect(JSON.parse(store.getItem(ABOUT_YOU_KEY) as string)).toEqual({ sex: "female" });
    writeAboutYou({});
    expect(store.getItem(ABOUT_YOU_KEY)).toBeNull();
  });
});
