/** The shared permalink test (acceptance gate 5): the frontend's decode of
 * /r/<data_version>/<model_version>/<state> must equal model.permalink's
 * encode — asserted against cases the Python model emitted through the
 * API's own pydantic path (scripts/gen_permalink_cases.py), not by
 * inspection. Byte equality both ways: decode inverts, encode reproduces. */
import { describe, expect, it } from "vitest";
import cases from "./permalink_cases.json";
import {
  decodePermalink,
  encodePermalink,
  type RankBody,
} from "../src/lib/permalink";
import { bodyToPrefs, toRankBody } from "../src/lib/prefs";

describe("permalink round-trip against the Python model", () => {
  for (const c of cases.cases) {
    const label = JSON.stringify(c.body).slice(0, 70);
    it(`decodes and re-encodes ${label}`, () => {
      const { dataVersion, modelVersion, body } = decodePermalink(c.permalink);
      expect(dataVersion).toBe(cases.data_version);
      expect(modelVersion).toBe(cases.model_version);
      // decode inverts the encode (numeric equality: 1.0 === 1 in JS)
      expect(body).toEqual(c.body as RankBody);
      // encode reproduces Python's bytes exactly, integral floats included
      const re = encodePermalink(dataVersion, modelVersion, body);
      expect(re).toBe(c.permalink);
    });
  }

  it("prefs round-trip through a decoded body without loss", () => {
    for (const c of cases.cases) {
      const { body } = decodePermalink(c.permalink);
      const prefs = bodyToPrefs(body as RankBody);
      const rebuilt = toRankBody(prefs);
      // weights arrive from pydantic with all five pillars; prefs preserve that
      expect(rebuilt.seeking.age).toEqual(body.seeking.age);
      expect(rebuilt.seeking.marital).toEqual(body.seeking.marital);
      expect(rebuilt.seeking.race_ethnicity).toEqual(body.seeking.race_ethnicity);
      expect(rebuilt.size_vs_odds).toEqual(body.size_vs_odds);
      expect(rebuilt.weights).toEqual(body.weights);
    }
  });
});
