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
      // decode inverts the encode (numeric equality: 1.0 === 1 in JS) —
      // up to the m3.0.0 canonicalisation: a body sent with the
      // deprecated pool_vs_balance name encodes as pool_vs_match, exactly
      // as the Python model does, so the decoded body carries the
      // canonical name (ADR 0009)
      const canonicalBody = { ...(c.body as RankBody) };
      if (canonicalBody.pool_vs_balance !== undefined) {
        canonicalBody.pool_vs_match = canonicalBody.pool_vs_balance;
        delete canonicalBody.pool_vs_balance;
      }
      expect(body).toEqual(canonicalBody);
      // encode reproduces Python's bytes exactly, integral floats included
      const re = encodePermalink(dataVersion, modelVersion, body);
      expect(re).toBe(c.permalink);
    });
  }

  it("prefs round-trip through a decoded body without losing the search", () => {
    for (const c of cases.cases) {
      const { body } = decodePermalink(c.permalink);
      const prefs = bodyToPrefs(body as RankBody);
      const rebuilt = toRankBody(prefs);
      expect(rebuilt.seeking.age).toEqual(body.seeking.age);
      expect(rebuilt.seeking.marital).toEqual(body.seeking.marital);
      // race compares RESOLVED (m2.2.0): all eight ticked IS no filter,
      // so a token listing all eight round-trips to the absent spelling
      const resolveRace = (r?: string[]) =>
        r && r.length > 0 && r.length < 8 ? [...r].sort() : undefined;
      expect(resolveRace(rebuilt.seeking.race_ethnicity)).toEqual(
        resolveRace(body.seeking.race_ethnicity));
      // the deprecated names re-express as pool_vs_match (ADR 0009 over
      // ADR 0004); the slider VALUE survives, the old name does not, and
      // explicit m1.x weight vectors reproduce on the /r/ render itself
      // (server-side, from the decoded body) rather than in edit state.
      const slider = body.pool_vs_match ?? body.pool_vs_balance ?? body.size_vs_odds;
      if (slider !== undefined) {
        expect(rebuilt.pool_vs_match).toEqual(slider);
      }
      // the seeker's optional attributes survive the round trip
      expect(rebuilt.self.education).toEqual(body.self.education);
      expect(rebuilt.self.race_ethnicity).toEqual(body.self.race_ethnicity);
      // importance compares RESOLVED: a partial m2.1.0 body defaults its
      // missing controls to "some", and the one-version lifestyle alias
      // lands on both split pillars — the semantics survive, the spelling
      // need not (ADR 0005)
      const resolve = (imp?: Record<string, string>) => {
        const out: Record<string, string> = {
          cost: "some", reach: "some", students: "some", weather: "some",
        };
        for (const [k, v] of Object.entries(imp ?? {})) {
          if (k === "lifestyle") {
            out.weather = v;
            out.students = v;
          } else if (k in out) {
            out[k] = v;
          }
        }
        return out;
      };
      if (body.importance || rebuilt.importance) {
        expect(resolve(rebuilt.importance)).toEqual(resolve(body.importance));
      }
    }
  });
});
