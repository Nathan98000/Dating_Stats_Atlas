"""Phase 4 Stage 5a: the race-free form's held-out fit, for the record
(ADR 0018 §2). Reads the leave-one-metro-out store the refinement
machinery wrote (`kernel_refine lomo --only C1_cohorts_plus_shipped,
D0_race_free,C1_race_zeroed`) and states two comparisons under ADR 0014's
rule (a margin of 0.25 per 1,000 weighted couple-sides; less is a tie):

  D0 against C1              what leaving race out costs
  D0 against C1 race-zeroed  why the race-free form is refitted rather
                             than C1 with its race terms set to zero

Both on the usual held-out measure (split-half, shrunk dials) with the
national-only (no-dial) reading beside it, per-metro win counts, and the
intermarriage check's median error for each form (a race-free form cannot
predict who marries across groups; the reading says by how much).

    python -m atlas.pipeline.build.race_free_heldout [--store DIR] [--out JSON]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from atlas.pipeline.build.kernel_refine import HELDOUT_TIE_ADR, HELDOUT_TIE_MARGIN_PER_1000, beats

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "results" / "phase4" / "kernel"
OUT = ROOT / "results" / "phase4" / "race_free_heldout.json"
FORMS = {"race_free": "D0_race_free", "c1": "C1_cohorts_plus_shipped",
         "c1_race_zeroed": "C1_race_zeroed"}


def compare(lomo: list[dict], a: str, b: str) -> dict:
    """a minus b, per 1,000 weighted couple-sides of the held-out halves."""
    sides = sum(r["forms"][b]["sides"] for r in lomo)
    out = {"a": a, "b": b, "heldout_sides": sides}
    for measure in ("shrunk", "national", "raw"):
        ta = sum(r["forms"][a][measure] for r in lomo)
        tb = sum(r["forms"][b][measure] for r in lomo)
        g = (ta - tb) / sides * 1000
        out[measure] = {"gain_a_minus_b_per_1000_sides": round(g, 3),
                        "metros_where_a_better": sum(
                            1 for r in lomo if r["forms"][a][measure] > r["forms"][b][measure]),
                        "a_beats_b": beats(g), "b_beats_a": beats(-g)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", type=Path, default=STORE)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    lomo = json.loads((a.store / "lomo_forms.json").read_text())
    held = json.loads((a.store / "refine_heldout.json").read_text())
    fits = json.loads((a.store / "refine_fits.json").read_text())
    for r in lomo:
        assert all(f in r["forms"] for f in FORMS.values()), r["cbsa"]
    rf, c1, c1z = FORMS["race_free"], FORMS["c1"], FORMS["c1_race_zeroed"]
    inter = {k: {m: held["forms"][f]["intermarriage"]["corrected_errors"][m]["median_abs_pts"]
                 for m in ("national_only", "shrunk_dial", "random_pairing")}
             for k, f in FORMS.items()}
    dials = {k: {comp: v["tau"] for comp, v in fits["forms"][f]["dials"].items()}
             for k, f in FORMS.items()}
    rec = {
        "metros": len(lomo),
        "rule": {"adr": HELDOUT_TIE_ADR, "margin_per_1000_sides": HELDOUT_TIE_MARGIN_PER_1000},
        "forms": FORMS,
        "leaving_race_out_costs": compare(lomo, rf, c1),
        "refit_against_zeroed": compare(lomo, rf, c1z),
        "zeroed_against_c1": compare(lomo, c1z, c1),
        "intermarriage_median_abs_error_pts": inter,
        "dial_tau": dials,
        "note": ("ADR 0018 §2 (Nathan's decision): the race-free form is the default whatever "
                 "these readings say; they are recorded, not applied. The intermarriage "
                 "check measures who marries across racial and ethnic groups, which a form "
                 "without a race component cannot predict beyond its education and age "
                 "structure; its error is recorded, not a gate on this form."),
    }
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("leaving_race_out_costs", "refit_against_zeroed",
                                          "intermarriage_median_abs_error_pts", "dial_tau")}, indent=1))


if __name__ == "__main__":
    main()
