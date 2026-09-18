"""Phase 2f gate 1: prove m2.3.1 moved no number.

Runs every golden request vector through the CURRENT engine against the
pinned m2.3.0 fixture and the regenerated m2.3.1 fixture, then compares
the two full responses field by field. Every numeric field must be
EXACTLY equal (same data, same code — bitwise, not tolerance). Strings
must be equal except on the three surfaces this phase deliberately
changed, each classified and counted:

  band.tone            three tones widened to five (item 1); the old
                       tone must map to the new one at the same position
                       (good -> good|good_strong, poor -> poor|poor_strong,
                       neutral -> neutral)
  rent unit_line       the registry unit for median_gross_rent (item 5.1)
  crime caution /      the FBI caution boxes' registry copy
  compare_banner       (items 5.3 / 6.4)

Anything else that differs is a finding and fails the run.

Usage:
    python -m atlas.pipeline.build.display_only_diff <old_fixture> <new_fixture> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from atlas import model as engine
from atlas.model.tests.golden.make_fixture import GOLDEN_VECTORS

TONE_WIDENING = {"good": {"good", "good_strong"},
                 "poor": {"poor", "poor_strong"},
                 "neutral": {"neutral"}}


class Tally:
    def __init__(self) -> None:
        self.numeric = 0
        self.strings_equal = 0
        self.diffs = {"tone": 0, "rent_unit_line": 0, "crime_caution": 0,
                      "crime_compare_banner": 0}
        self.findings: list[str] = []


def compare(path: str, a, b, t: Tally) -> None:
    if isinstance(a, bool) or isinstance(b, bool):
        if a != b:
            t.findings.append(f"{path}: bool {a!r} != {b!r}")
        return
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        t.numeric += 1
        if not (a == b or (a != a and b != b)):   # NaN == NaN for our purposes
            t.findings.append(f"{path}: number {a!r} != {b!r}")
        return
    if isinstance(a, str) and isinstance(b, str):
        if a == b:
            t.strings_equal += 1
            return
        if path.endswith("band.tone") or path.endswith("['tone']"):
            if b in TONE_WIDENING.get(a, set()):
                t.diffs["tone"] += 1
                return
            t.findings.append(f"{path}: tone {a!r} -> {b!r} breaks the "
                              f"position map")
            return
        if "median_gross_rent" in path and path.endswith("unit_line"):
            t.diffs["rent_unit_line"] += 1
            return
        if path.endswith("crime.caution"):
            t.diffs["crime_caution"] += 1
            return
        if path.endswith("crime.compare_banner"):
            t.diffs["crime_compare_banner"] += 1
            return
        t.findings.append(f"{path}: string {a!r} != {b!r}")
        return
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            t.findings.append(f"{path}: keys {sorted(set(a) ^ set(b))} differ")
        for k in sorted(set(a) & set(b)):
            compare(f"{path}.{k}", a[k], b[k], t)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            t.findings.append(f"{path}: length {len(a)} != {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            # name list entries by their id/cbsa so a finding reads
            tag = x.get("id") or x.get("cbsa") if isinstance(x, dict) else i
            compare(f"{path}[{tag}]", x, y, t)
        return
    if a is None and b is None:
        return
    if a != b:
        t.findings.append(f"{path}: {a!r} != {b!r}")


def main(old_dir: str, new_dir: str, out_path: str) -> None:
    old = engine.load_build(old_dir, allow_model_mismatch=True)
    new = engine.load_build(new_dir)
    assert old.manifest["model_version"] == "m2.3.0", old.manifest["model_version"]
    assert new.manifest["model_version"] == engine.MODEL_VERSION
    t = Tally()
    for v in GOLDEN_VECTORS:
        body = {k: v[k] for k in ("self", "seeking", "weights",
                                  "pool_vs_balance", "importance") if k in v}
        ra = engine.rank(old, engine.parse_request(json.loads(json.dumps(body))))
        rb = engine.rank(new, engine.parse_request(json.loads(json.dumps(body))))
        compare(v["name"], ra, rb, t)
    out = {
        "old": {"build": old.manifest["data_version"],
                "model": old.manifest["model_version"]},
        "new": {"build": new.manifest["data_version"],
                "model": new.manifest["model_version"]},
        "vectors": len(GOLDEN_VECTORS),
        "numeric_fields_compared": t.numeric,
        "all_numeric_identical": not any("number" in f for f in t.findings),
        "strings_equal": t.strings_equal,
        "allowed_string_diffs": t.diffs,
        "findings": t.findings,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(GOLDEN_VECTORS)} vectors, {t.numeric:,} numeric fields "
          f"compared, diffs {t.diffs}")
    if t.findings:
        for f in t.findings[:20]:
            print("FINDING:", f)
        raise SystemExit(f"{len(t.findings)} unexplained differences — "
                         f"a number or an unapproved string moved")
    print("no number moved; every string difference is classified")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
