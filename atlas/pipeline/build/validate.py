"""Validation suite (§11), run on every build. Machine-readable report in
results/phase2/validation_report.json, stamped with the git state that
produced it (the Phase 2a face panel shipped stale against the committed
code because nothing recorded which code rendered it); HARD gates fail the
build (nonzero exit), SOFT gates warn and are reported as measured.

  hard  interval calibration     Gate 0 Option 2 coverage/overstatement
  hard  suppression goldens      the 12 pinned vectors, exact; only the
                                 n-only reason strings may appear (ADR 0002)
  hard  cube vs SQL differential randomized filtered query shapes computed
                                 both through the cube mask path and by SQL
                                 over the contribution table — the check
                                 that would have caught the Phase 1 mask
                                 bug the day it was written; since m3.0.0
                                 the same shapes also run the KERNEL-
                                 WEIGHTED sum both ways (the weighted
                                 path's mask-axis sibling)
  hard  rank stability           ADR 0011 (Phase 3c): the total WOBBLE of
                                 the test searches (stability_gate.py —
                                 personas, the effects grid, the same-sex
                                 grid; mean rank move of the cities in
                                 either top 10 over the 80 replicates) must
                                 not exceed 1.10 x the fixed reference's
                                 (m3.2.0, results/phase3c/
                                 stability_reference.json) over the
                                 searches the build touches
  soft  rank stability (old)     the >= 8-of-10 top-10 overlap in >= 80% of
                                 replicates per persona, reported beside
                                 the new reading
  hard  kernel face validity     a 30-year-old's age weight peaks within
                                 three years of 30; the education matrix
                                 is diagonal-dominant; every race group's
                                 own-group multiplier beats its
                                 off-diagonals, both sexes (ADR 0009)
  hard  pew never shipped        the Pew table is a build-time reference
                                 read outside any adapter (Phase 3c A3):
                                 its licence is non-shippable, no feature
                                 traces to it, and nothing in manifest.json
                                 or kernel.json names it or its US rate
  hard  explanation invariants   no rendered string carries the §12.3
                                 banned vocabulary; the lead phrase is
                                 position-unique (the Phase 2a panel defect,
                                 found by hand, checked by machine since)
  hard  adversarial artifacts    college/military/prison metros in any
                                 top-10 must not be there for a
                                 GQ-traceable reason
  soft  face validity            12 personas, now with pool, served margin
                                 and n in every row so the magnitude check
                                 can be done from the report
  soft  weight sensitivity       each pillar weight +/-20%, Kendall tau
                                 vs baseline (target >= 0.85)
  soft  external correlation     score/ratio vs B09021 living-alone share
                                 and B12007 (state fallback, finding)
  soft  pew reproduction         the Phase 3 out-of-sample Pew comparison
                                 (results/phase3/kernel_report.json): the
                                 shrunk kernel must beat national-only and
                                 raw per-metro; reported as measured
  soft  served-region true CV    the ADR 0002 evidence, recomputed from the
                                 480-shape battery when the file is present
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, pearsonr, spearmanr

from atlas import model as engine
from atlas.model.preferences import (ALLOWED_MARITAL, EDU_LEVELS, RACE_LEVELS,
                                     SELECTABLE_RACES, SEX_LEVELS,
                                     resolve_race_levels, seeker_weights)
from atlas.model.scoring import match_index, score_vector
from atlas.model.suppression import POLICY_STRINGS
from atlas.pipeline.build import stability_gate as SG
from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.fetch import DATA, RESULTS, api_get

P2 = RESULTS / "phase2"

STABILITY_OVERLAP = 8      # of top 10
STABILITY_SHARE = 0.80
KENDALL_MIN = 0.85
GQ_POOL_SHARE_LIMIT = 0.15
DIFF_SHAPES = 40
DIFF_SEED = 2026
DIFF_REL_TOL = 1e-3        # float32 cube accumulation vs float64 SQL
ALLOWED_REASONS = {"n_below_100", "empty_pool"}
BANNED = re.compile(r"\b(odds|rivals?|markets?|supply|inventory|competitors?)\b",
                    re.IGNORECASE)
PEW_CSV = RESULTS / "reference" / "pew_intermarriage_2015.csv"
KERNEL_REPORT = RESULTS / "phase3" / "kernel_report.json"
CUBE_TO_SPEC = {v: k for k, v in engine.SPEC_RACE.items()}


def _git_stamp() -> dict:
    def run(*args):
        return subprocess.run(["git", *args], capture_output=True,
                              text=True).stdout.strip()
    return {"git_sha": run("rev-parse", "HEAD"),
            "git_dirty": bool(run("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "engine_model_version": engine.MODEL_VERSION}


def _replicate_sums(con, where: str) -> pd.DataFrame:
    reps = ", ".join(f"sum(pwgtp{i} * a_eff)" for i in range(1, 81))
    rows = con.execute(
        f"SELECT cbsa, sum(pwgtp * a_eff), {reps} FROM contrib "
        f"WHERE gq <> 2 AND ({where}) GROUP BY 1").fetchall()
    return pd.DataFrame([{"cbsa": r[0],
                          "est": float(r[1] or 0),
                          **{f"r{i}": float(r[2 + i - 1] or 0)
                             for i in range(1, 81)}} for r in rows])


def _kernel_weights_table(con, build, req) -> None:
    """The seeker's per-metro kernel weights over (age, edu4, race8) as a
    temp table kw(cbsa, agep, edu4, race8, w) — the SQL side of the
    weighted differential and of the replicate resampling."""
    age_vec, W = seeker_weights(build.kernel, req.self_sex, req.self_age,
                                req.self_edu, req.self_race,
                                same_sex=(req.seeking.sex == req.self_sex))
    n = len(build.metro_levels)
    full = age_vec[:, :, None, None] * W[:, None, :, :]           # (n, 53, 4, 8)
    m_i, a_i, e_i, r_i = np.indices(full.shape).reshape(4, -1)
    df = pd.DataFrame({"cbsa": np.array(build.metro_levels)[m_i],
                       "agep": a_i + 18,
                       "edu4": np.array(EDU_LEVELS)[e_i],
                       "race8": np.array(RACE_LEVELS)[r_i],
                       "w": full.ravel()})
    con.register("kw_df", df)
    con.execute("CREATE OR REPLACE TEMP TABLE kw AS SELECT * FROM kw_df")
    con.unregister("kw_df")


def _weighted_sums_sql(con, where: str, replicates: bool = False) -> pd.DataFrame:
    """Per metro: sum of kernel weight x person weight over the masked
    pool (and, optionally, per replicate)."""
    reps = (", " + ", ".join(f"sum(c.pwgtp{i} * c.a_eff * kw.w)" for i in range(1, 81))
            if replicates else "")
    # the search filter applies to contrib alone (a subquery, so its
    # unqualified column names never collide with the weight table's)
    rows = con.execute(
        f"SELECT c.cbsa, sum(c.pwgtp * c.a_eff * kw.w){reps} "
        f"FROM (SELECT * FROM contrib WHERE gq <> 2 AND ({where})) c "
        f"JOIN kw ON kw.cbsa = c.cbsa AND kw.agep = c.agep AND kw.edu4 = c.edu4 "
        f"AND kw.race8 = c.race8 GROUP BY 1").fetchall()
    cols = ["cbsa", "num"] + ([f"r{i}" for i in range(1, 81)] if replicates else [])
    return pd.DataFrame([[r[0]] + [float(x or 0) for x in r[1:]] for r in rows],
                        columns=cols)


def _spec_to_sql(seeking: dict, self_: dict) -> tuple[str, str]:
    """(pool where, rival where) in contrib SQL, mirroring the mask logic."""
    sex = seeking.get("sex") or ("male" if self_["sex"] == "female" else "female")
    sexcode = 1 if sex == "male" else 2
    lo, hi = seeking["age"]
    mar = {"never_married": "6", "previously_married": "3,4,5",
           "currently_married": "1,2"}
    msp = ",".join(mar[m] for m in seeking["marital"])
    w = f"sex = {sexcode} AND agep BETWEEN {lo} AND {hi} AND msp IN ({msp})"
    if seeking.get("education_min"):
        tail = {"some_college": "'some_college','bachelors','graduate'",
                "bachelors": "'bachelors','graduate'",
                "graduate": "'graduate'"}[seeking["education_min"]]
        w += f" AND edu4 IN ({tail})"
    if seeking.get("income_min"):
        w += f" AND inc_adj >= {seeking['income_min']}"
    if seeking.get("race_ethnicity"):
        # the model ORs the two always-counted groups into every selection
        # (ADR 0004); the SQL mirror must do exactly the same
        cubes = resolve_race_levels(list(seeking["race_ethnicity"]))
        if cubes is not None:
            w += " AND race8 IN (" + ",".join(f"'{c}'" for c in cubes) + ")"
    # balance (ADR 0004): the plain sex ratio over the SEEKING window
    b_sex_sought = sexcode
    b_sex_seeker = 1 if self_["sex"] == "male" else 2
    bw_sought = (f"sex = {b_sex_sought} AND agep BETWEEN {lo} AND {hi} "
                 f"AND msp IN ({msp})")
    bw_seeker = (f"sex = {b_sex_seeker} AND agep BETWEEN {lo} AND {hi} "
                 f"AND msp IN ({msp})")
    return w, bw_sought, bw_seeker


def _random_body(rng: np.random.Generator) -> dict:
    """A random §8.2 request exercising partial filters on every cube axis —
    education and income floors especially, because a transposed axis pair
    only shows up under PARTIAL filters on the transposed axes."""
    self_sex = rng.choice(["male", "female"])
    seek_sex = rng.choice(["male", "female", None], p=[0.4, 0.4, 0.2])
    lo = int(rng.integers(18, 60))
    hi = min(70, lo + int(rng.integers(2, 30)))
    marital = list(rng.choice(list(ALLOWED_MARITAL), replace=False,
                              size=int(rng.integers(1, 3))))
    edu = rng.choice(["some_college", "bachelors", "graduate", None])
    inc = rng.choice(sorted(engine.INCOME_FLOORS) + [None])
    n_race = int(rng.integers(0, 4))
    race = (list(rng.choice(list(SELECTABLE_RACES),
                            replace=False, size=n_race)) if n_race else None)
    seeking = {"age": [lo, hi], "marital": marital}
    if seek_sex:
        seeking["sex"] = str(seek_sex)
    if edu:
        seeking["education_min"] = str(edu)
    if inc is not None:
        seeking["income_min"] = int(inc)
    if race:
        seeking["race_ethnicity"] = race
    return {"self": {"sex": str(self_sex), "age": int(rng.integers(18, 71))},
            "seeking": seeking}


def check_differential(build, con) -> dict:
    """Randomized cube-vs-SQL differential over the whole query path: the
    same filtered shape summed through the flattened mask (gemv) and by SQL
    over the contribution table must agree per metro. Phase 2a's mask-axis
    bug is the reason this exists as a build gate."""
    rng = np.random.default_rng(DIFF_SEED)
    midx = {c: i for i, c in enumerate(build.metro_levels)}
    worst = {"rel_err": 0.0}
    for k in range(DIFF_SHAPES):
        body = _random_body(rng)
        req = engine.parse_request(body)
        from atlas.model.preferences import pool_mask
        mask = pool_mask(req.seeking)
        est = (build.pool_flat @ mask).astype(np.float64)
        n_alloc = (build.count_flat @ mask).astype(np.float64)
        pw, bws, bwk = _spec_to_sql(body["seeking"], body["self"])
        from atlas.model.preferences import balance_masks
        m_sought, m_seeker = balance_masks(req)
        cube_bs = (build.pool_flat @ m_sought).astype(np.float64)
        cube_bk = (build.pool_flat @ m_seeker).astype(np.float64)
        rels = []
        # m3.0.0: the kernel-weighted numerator and its denominator through
        # the reduced cubes vs the same sums by SQL over contrib joined to
        # the seeker's weight table — the weighted path's own differential
        mt = match_index(build, req)
        _kernel_weights_table(con, build, req)
        wsql = _weighted_sums_sql(con, pw).set_index("cbsa")["num"]
        sql_num = np.zeros(len(build.metro_levels))
        for cbsa, v in wsql.items():
            sql_num[midx[cbsa]] = v
        rels.append(np.abs(mt["num"] - sql_num) / np.maximum(sql_num, 1.0))
        rels.append(np.abs(mt["den"] - est) / np.maximum(est, 1.0))
        for where, cube_vals, with_n in ((pw, est, True), (bws, cube_bs, False),
                                         (bwk, cube_bk, False)):
            rows = con.execute(
                f"SELECT cbsa, sum(pwgtp * a_eff), sum(a_eff) FROM contrib "
                f"WHERE gq <> 2 AND ({where}) GROUP BY 1").fetchall()
            sql_est = np.zeros(len(build.metro_levels))
            sql_n = np.zeros(len(build.metro_levels))
            for cbsa, w, na in rows:
                sql_est[midx[cbsa]] = float(w or 0)
                sql_n[midx[cbsa]] = float(na or 0)
            rels.append(np.abs(cube_vals - sql_est) / np.maximum(sql_est, 1.0))
            if with_n:
                rels.append(np.abs(n_alloc - sql_n) / np.maximum(sql_n, 1.0))
        rel = rels[0]
        m = float(max(r.max() for r in rels))
        if m > worst["rel_err"]:
            worst = {"rel_err": m, "shape": body,
                     "metro": build.metro_levels[int(np.argmax(rel))]}
    ok = worst["rel_err"] < DIFF_REL_TOL
    return {"pass": bool(ok), "shapes": DIFF_SHAPES, "seed": DIFF_SEED,
            "tolerance": DIFF_REL_TOL,
            "worst_rel_err": round(worst["rel_err"], 9),
            "worst_detail": None if ok else worst}


def check_explanations(build, persona_results) -> dict:
    """No rendered string carries the banned vocabulary; the lead phrase is
    position-unique. The Phase 2a panel said 'Its biggest edge is …' twice
    on 23 of 33 rows because a pre-commit renderer keyed phrasing on the
    magnitude bucket alone — found by reading the panel by hand, checked by
    machine ever since."""
    problems = []
    for s in POLICY_STRINGS.values():
        if BANNED.search(s):
            problems.append({"where": "policy_strings", "text": s})
    for fid, e in build.legend.items():
        for k in ("display_name", "unit", "definition"):
            if BANNED.search(str(e.get(k, ""))):
                problems.append({"where": f"legend:{fid}.{k}",
                                 "text": e.get(k)})
    for d in build.descriptions:
        if BANNED.search(d):
            problems.append({"where": "city_description", "text": d})
    for k, s in build.manifest.get("strings", {}).items():
        if BANNED.search(s):
            problems.append({"where": f"registry_strings:{k}", "text": s})
    n_expl = 0
    floor = float(build.manifest["crime"]["coverage_floor"])
    for name, res in persona_results.items():
        for r in res["ranked"]:
            n_expl += 1
            for text in (r["summary_line"], r["balance"].get("display", "")):
                if BANNED.search(text):
                    problems.append({"where": f"{name}:{r['cbsa']}",
                                     "text": text})
            if r["summary_line"].count("Biggest pluses:") > 1:
                problems.append({"where": f"{name}:{r['cbsa']}",
                                 "defect": "lead phrase repeated",
                                 "text": r["summary_line"]})
            # crime (item 5): figures only ever render beside their
            # coverage and caution, and only above the registry floor
            blk = r.get("crime")
            if not blk:
                problems.append({"where": f"{name}:{r['cbsa']}",
                                 "defect": "row missing crime block"})
                continue
            for text in (blk.get("caution", ""), blk.get("note", ""),
                         blk.get("coverage_line", "")):
                if text and BANNED.search(text):
                    problems.append({"where": f"{name}:{r['cbsa']}:crime",
                                     "text": text})
            if blk["available"]:
                if not blk.get("coverage_line") or len(blk.get("stats", [])) != 2:
                    problems.append({"where": f"{name}:{r['cbsa']}:crime",
                                     "defect": "figures without coverage"})
                if blk.get("coverage_pct", 0) < floor * 100:
                    problems.append({"where": f"{name}:{r['cbsa']}:crime",
                                     "defect": "figures below the coverage floor"})
            elif not blk.get("note"):
                problems.append({"where": f"{name}:{r['cbsa']}:crime",
                                 "defect": "blank state without its note"})
    return {"pass": not problems, "explanations_checked": n_expl,
            "problems": problems[:20]}


def check_kernel_face(build) -> dict:
    """The three face-validity checks on the SHIPPED kernel (ADR 0009):
    a 30-year-old's age weight peaks within three years of 30, the
    education matrix is diagonal-dominant, and every race group's
    own-group multiplier exceeds each of its off-diagonals, both sexes.
    Any failure is a finding."""
    k = build.kernel
    out: dict = {"peak_age_at_30": {}, "edu_rows_diagonal_dominant": {},
                 "race_rows_diagonal_max": {}}
    ok = True
    c30 = int(k.cohort_of_age[30 - 18])
    for si, name in enumerate(SEX_LEVELS):
        gaps = np.arange(53) - (30 - 18) + k.gap_offset
        peak = int(np.argmax(k.f_age[si, c30][gaps])) + 18
        out["peak_age_at_30"][name] = peak
        ok &= abs(peak - 30) <= 3
        rows = {}
        for r in range(8):
            row = k.f_race[si, r]
            rows[RACE_LEVELS[r]] = bool(row[r] > np.delete(row, r).max())
        out["race_rows_diagonal_max"][name] = rows
        ok &= all(rows.values())
        # m3.2.0: the education matrix is per seeker sex
        d = [bool(k.f_edu[si, e, e] == k.f_edu[si, e].max()) for e in range(4)]
        out["edu_rows_diagonal_dominant"][name] = d
        ok &= all(d)
    # m3.2.0: the same checks on the same-sex terms that ship (B3)
    ss = k.same_sex
    if ss is not None:
        rec = {"components": list(ss.components)}
        for si, name in enumerate(SEX_LEVELS):
            gaps = np.arange(53) - (30 - 18) + k.gap_offset
            if "age" in ss.components:
                peak = int(np.argmax(ss.f_age[si, ss.cohort_of_age[30 - 18]][gaps])) + 18
                rec[f"peak_age_at_30_{name}"] = peak
                ok &= abs(peak - 30) <= 3
            if "edu" in ss.components:
                d = [bool(ss.f_edu[si, e, e] == ss.f_edu[si, e].max()) for e in range(4)]
                rec[f"edu_diagonal_dominant_{name}"] = d
                ok &= all(d)
            if "race" in ss.components:
                rows = {RACE_LEVELS[r]: bool(ss.f_race[si, r, r] > np.delete(ss.f_race[si, r], r).max())
                        for r in range(8)}
                rec[f"race_diagonal_max_{name}"] = rows
                ok &= all(rows.values())
        out["same_sex_terms"] = rec
    out["pass"] = bool(ok)
    return out


def check_pew_never_shipped(build_dir: Path) -> dict:
    """Hard (Phase 3c A3). The Pew intermarriage table is a validation
    reference read directly by build.kernel, build.kernel_refine and the
    soft check below — outside any adapter — so the provenance assertion
    that guards adapter-fed fields (contracts.provenance.assert_all_shippable)
    cannot see it. This check guards the artifact itself: the licence
    registry carries the source marked non-shippable, no feature in the
    manifest traces to it, and no key or string value in manifest.json or
    kernel.json names Pew, the table, or the level offset derived from its
    US row. Any failure is a leak, not a finding to report."""
    from atlas.pipeline.adapters.base import LICENSES
    build_dir = Path(build_dir)
    out: dict = {"licence_registered_non_shippable": False,
                 "features_tracing_to_pew": [], "hits": {}}
    lic = LICENSES.get("pew_intermarriage")
    out["licence_registered_non_shippable"] = bool(lic is not None and not lic.shippable)
    manifest = json.loads((build_dir / "manifest.json").read_text())
    kernel = json.loads((build_dir / "kernel.json").read_text())
    out["features_tracing_to_pew"] = sorted(
        fid for fid, f in manifest.get("features_block", {}).items()
        if (f.get("provenance") or {}).get("source") == "pew_intermarriage")
    needles = ("pew", "intermarriage_2015", "level_offset")

    def walk(node, path, hits):
        if isinstance(node, dict):
            for k, v in node.items():
                if any(n in str(k).lower() for n in needles):
                    hits.append(path + "/" + str(k))
                walk(v, path + "/" + str(k), hits)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]", hits)
        elif isinstance(node, str):
            if any(n in node.lower() for n in needles):
                hits.append(path + " (value)")

    for name, doc in (("manifest.json", manifest), ("kernel.json", kernel)):
        hits: list[str] = []
        walk(doc, "", hits)
        out["hits"][name] = hits
    out["pass"] = bool(out["licence_registered_non_shippable"]
                       and not out["features_tracing_to_pew"]
                       and not any(out["hits"].values()))
    return out


def check_pew_reproduction() -> dict:
    """The Phase 3 out-of-sample Pew comparison as the kernel run recorded
    it: three models' corrected error distributions and whether the
    shrunk kernel beat national-only AND raw per-metro (the item 11 bar).
    Soft here — reported as measured; the kernel run is where it gates."""
    # m3.2.0 (Phase 3b): the shipped FORM's own leave-one-metro-out record
    # when the refinement run wrote one; else the Phase 3 sample record
    refine = RESULTS / "phase3b" / "refine_heldout.json"
    if refine.exists() and "shipped" in json.loads(refine.read_text()).get("forms", {}):
        rec = json.loads(refine.read_text())
        pew = rec["forms"]["shipped"]["pew"]
        ship = f"{rec['sample']} (shipped form, results/phase3b/refine_heldout.json)"
        source = "results/phase3b/refine_heldout.json (leave-one-metro-out on the shipped form)"
        metros = 124
    else:
        if not KERNEL_REPORT.exists():
            return {"skipped": "results/phase3/kernel_report.json not on this machine"}
        rep = json.loads(KERNEL_REPORT.read_text())
        ship = rep["shipped"]["sample"]
        pew = rep["samples"][ship]["pew"]
        metros = pew["metros_matched"]
        source = ("results/phase3/kernel_report.json (leave-one-metro-out, "
                  "level offset from Pew's US row only)")
    ce = pew["corrected_errors"]
    return {"fitting_sample": ship, "metros": metros,
            "level_offset_ratio": pew["level_offset_ratio_ours_over_pew"],
            "median_abs_pts": {m: ce[m]["median_abs_pts"] for m in
                               ("national_only", "raw_dial", "shrunk_dial")},
            "p90_abs_pts": {m: ce[m]["p90_abs_pts"] for m in
                            ("national_only", "raw_dial", "shrunk_dial")},
            "shrunk_beats_both": bool(
                ce["shrunk_dial"]["median_abs_pts"] < ce["national_only"]["median_abs_pts"]
                and ce["shrunk_dial"]["median_abs_pts"] < ce["raw_dial"]["median_abs_pts"]),
            "tie_accepted": "ADR 0009 §4 (amended, m3.1.0): the tie against the raw per-metro "
                            "dial clears the bar on Nathan's decision",
            "source": source}


def measure_served_region_cv() -> dict:
    """ADR 0002's evidence, recomputed when the battery file is on disk."""
    path = DATA / "variance_points2.parquet"
    if not path.exists():
        return {"skipped": "variance_points2.parquet not on this machine"}
    df = pd.read_parquet(path)
    df["n_gate"] = np.minimum(df["n_alloc"], df["n_kish"])
    served = df[(df["n_gate"] >= 100) & (df["est"] > 0)]
    cv = served["rse"]
    return {"points": int(len(served)),
            "p50": round(float(cv.quantile(.50)), 4),
            "p99": round(float(cv.quantile(.99)), 4),
            "max": round(float(cv.max()), 4),
            "points_above_20pct": int((cv > 0.20).sum()),
            "note": "true 81-replicate CV over the 480-shape battery where "
                    "intervals display (n_gate >= 100); the removed CV tiers "
                    "could not have fired (ADR 0002)"}


def run_personas(build, vectors) -> dict:
    """Every golden vector ranked on this build (the personas the hard
    gates read)."""
    out = {}
    for v in vectors:
        body = {k: v[k] for k in ("self", "seeking", "weights",
                                  "pool_vs_match", "pool_vs_balance",
                                  "importance") if k in v}
        out[v["name"]] = engine.rank(build, engine.parse_request(body))
    return out


def rank_stability(build, con, vectors, persona_results: dict,
                   pool_reps: dict | None = None) -> dict:
    """The standing hard gate, one implementation: resample pool + match
    across the 80 replicates for every persona; a persona passes when its
    top-10 keeps >= 8 of 10 in >= 80% of the replicate draws. Returns the
    per-persona record (share, the index's replicate sd at the median and
    p90 — the root-cause metric — its p10-p90 spread and how bunched the
    scores are at the top-10 boundary). `pool_reps` caches the pool's
    replicate sums per persona (they do not depend on the kernel), so a
    kernel sweep pays the SQL once."""
    stab = {}
    for v in vectors:
        res = persona_results[v["name"]]
        ranked_cbsas = [r["cbsa"] for r in res["ranked"]]
        if len(ranked_cbsas) < 12:
            stab[v["name"]] = {"skipped": f"only {len(ranked_cbsas)} ranked"}
            continue
        pw, bws, bwk = _spec_to_sql(v["seeking"], v["self"])
        body = {k: v[k] for k in ("self", "seeking") if k in v}
        req = engine.parse_request(body)
        # replicate sums of the pool (every metro, for the national
        # reference) and of the kernel-weighted numerator
        if pool_reps is not None and v["name"] in pool_reps:
            P_all = pool_reps[v["name"]]
        else:
            P_all = _replicate_sums(con, pw).set_index("cbsa")
            if pool_reps is not None:
                pool_reps[v["name"]] = P_all
        _kernel_weights_table(con, build, req)
        W_all = _weighted_sums_sql(con, pw, replicates=True).set_index("cbsa")
        P = P_all.reindex(ranked_cbsas).fillna(0.0)
        W = W_all.reindex(ranked_cbsas).fillna(0.0)
        ridx = np.array([build.metro_levels.index(c) for c in ranked_cbsas])
        wts = res["weights"]
        base_top = set(ranked_cbsas[:10])
        hits = 0
        match_reps = np.zeros((80, len(ranked_cbsas)))
        for i in range(1, 81):
            est_r = P[f"r{i}"].to_numpy()
            nat_rate_r = W_all[f"r{i}"].sum() / max(P_all[f"r{i}"].sum(), 1e-9)
            match_r = 100.0 * (W[f"r{i}"].to_numpy() / np.maximum(est_r, 1e-9)) / nat_rate_r
            match_reps[i - 1] = match_r
            score_r = score_vector(build, ridx, est_r, match_r, wts)
            top_r = {ranked_cbsas[k] for k in np.argsort(-score_r)[:10]}
            if len(top_r & base_top) >= STABILITY_OVERLAP:
                hits += 1
        # m3.0.0 diagnostics, so a failure can be read from the report: the
        # index's replicate sd (successive-difference scaling), its spread
        # across the ranked set, and how bunched the scores are at the
        # top-10 boundary
        point = np.array([r["match"]["value"] for r in res["ranked"]], float)
        sd = np.sqrt(4.0 / 80.0 * ((match_reps - point[None, :]) ** 2).sum(axis=0))
        scores = np.array([r["score"] for r in res["ranked"]], float)
        stab[v["name"]] = {
            "share_replicates_with_>=8of10_overlap": hits / 80,
            "match_index_replicate_sd_median": round(float(np.median(sd)), 2),
            "match_index_replicate_sd_p90": round(float(np.percentile(sd, 90)), 2),
            "match_index_p10_p90_spread": round(float(np.percentile(point, 90)
                                                      - np.percentile(point, 10)), 1),
            "score_gap_rank10_to_rank11": round(float(scores[9] - scores[10]), 2),
            "score_span_ranks_7_to_14": round(float(scores[6] - scores[13]), 2)}
    return stab


def main(build_dir: str) -> int:
    from atlas.model.tests.golden.make_fixture import GOLDEN_VECTORS
    build = engine.load_build(build_dir)
    report: dict = {"build": build.manifest["data_version"],
                    "model_version": engine.MODEL_VERSION,
                    "generated_by": _git_stamp(),
                    "hard": {}, "soft": {}}
    hard_fail = []

    # ---- hard: interval calibration ---------------------------------------
    im = build.manifest["interval_model"]
    ok = (im["used_by_api"] and im["validation"]["coverage"] >= 0.95
          and im["validation"]["median_overstatement"] <= 0.25)
    report["hard"]["interval_calibration"] = {
        "pass": bool(ok), **im["validation"],
        "mechanism": im["mechanism"], "copy_rule": im["copy_rule"]}
    if not ok:
        hard_fail.append("interval_calibration")

    # ---- hard: suppression goldens (full-build responses are exercised in
    # pytest against the fixture; here the same vectors run on THIS build and
    # the suppression logic must be internally consistent) -------------------
    con = open_pool()
    persona_results = run_personas(build, GOLDEN_VECTORS)
    golden_ok = True
    for v in GOLDEN_VECTORS:
        res = persona_results[v["name"]]
        if res["shown_unranked"]:
            golden_ok = False   # the middle tier cannot fire (ADR 0002)
        for row in res["suppressed"]:
            if row["reason"] not in ALLOWED_REASONS:
                golden_ok = False
        for row in res["ranked"]:
            if not row["pool_moe"] > 0:
                golden_ok = False
    report["hard"]["suppression_reasons_and_intervals"] = {
        "pass": golden_ok, "allowed_reasons": sorted(ALLOWED_REASONS)}
    if not golden_ok:
        hard_fail.append("suppression")

    # ---- hard: randomized cube-vs-SQL differential --------------------------
    report["hard"]["cube_vs_sql_differential"] = check_differential(build, con)
    if not report["hard"]["cube_vs_sql_differential"]["pass"]:
        hard_fail.append("cube_vs_sql_differential")

    # ---- hard: rank stability (ADR 0011: total wobble against the fixed
    # reference over the searches this build touches; the old overlap
    # share is reported beside it as a soft reading) -------------------------
    gate = SG.gate_record(build, con, name=f"validate:{build.manifest['data_version']}")
    ref = SG.load_reference()
    gv = SG.verdict(gate, ref)
    stab = {n: r for n, r in gate["searches"].items() if n.startswith("persona:")}
    report["hard"]["rank_stability"] = {
        "pass": bool(gv["pass"]),
        **{k: gv[k] for k in ("reference_build", "searches_compared", "searches_touched", "basis",
                               "wobble_candidate", "wobble_reference", "ratio", "tolerance",
                               "ratio_over_all_searches", "searches_wobble_rose_more_than_25pct")},
        "rule": gate["rule"], "totals": gate["totals"],
        "reference_file": str(SG.REFERENCE.relative_to(RESULTS.parent)),
        "per_search": gate["searches"]}
    if not gv["pass"]:
        hard_fail.append("rank_stability")
    report["soft"]["rank_stability_overlap_old_rule"] = {
        "min_share_personas": gv["old_rule"]["min_share_personas"],
        "would_pass_at_0_80": gv["old_rule"]["pass_at_0_80"],
        "per_persona": {n[len("persona:"):]: r["overlap_share_old_rule"] for n, r in stab.items()
                        if "skipped" not in r},
        "rule": gv["old_rule"]["reading"]}

    # ---- hard: explanation invariants ---------------------------------------
    report["hard"]["explanation_invariants"] = check_explanations(
        build, persona_results)
    if not report["hard"]["explanation_invariants"]["pass"]:
        hard_fail.append("explanation_invariants")

    # ---- hard: kernel face validity (ADR 0009) ------------------------------
    report["hard"]["kernel_face_validity"] = check_kernel_face(build)
    if not report["hard"]["kernel_face_validity"]["pass"]:
        hard_fail.append("kernel_face_validity")

    # ---- hard: the Pew reference never reaches the artifact (Phase 3c A3) --
    report["hard"]["pew_never_shipped"] = check_pew_never_shipped(Path(build_dir))
    if not report["hard"]["pew_never_shipped"]["pass"]:
        hard_fail.append("pew_never_shipped")

    # ---- hard: adversarial artifacts ---------------------------------------
    quality = pd.read_csv(RESULTS / "phase1" / "metro_quality.csv",
                          dtype={"cbsa": str}).set_index("cbsa")
    adversarial = set(quality.nlargest(6, "noninst_gq_share_18_70").index) | \
        set(quality.nlargest(4, "inst_gq_share").index)
    findings = []
    for name, res in persona_results.items():
        for row in res["ranked"][:10]:
            if row["cbsa"] in adversarial:
                body = next(v for v in GOLDEN_VECTORS if v["name"] == name)
                pw, _, _ = _spec_to_sql(body["seeking"], body["self"])
                tot, hh_only = con.execute(
                    f"SELECT sum(pwgtp * a_eff) FILTER (WHERE gq <> 2), "
                    f"sum(pwgtp * a_eff) FILTER (WHERE gq = 0) "
                    f"FROM contrib WHERE cbsa = ? AND ({pw})",
                    [row["cbsa"]]).fetchone()
                gq_share = 1 - (hh_only or 0) / tot if tot else 0
                findings.append({"persona": name, "cbsa": row["cbsa"],
                                 "rank": row["rank"],
                                 "pool_share_noninst_gq": round(gq_share, 4),
                                 "gq_traceable": gq_share > GQ_POOL_SHARE_LIMIT})
    ok = not any(f["gq_traceable"] for f in findings)
    report["hard"]["adversarial_artifacts"] = {
        "pass": bool(ok), "watchlist": sorted(adversarial),
        "top10_appearances": findings,
        "rule": f"a watchlist metro in a top-10 fails if > "
                f"{GQ_POOL_SHARE_LIMIT:.0%} of that persona's pool there is "
                f"noninstitutional GQ"}
    if not ok:
        hard_fail.append("adversarial_artifacts")

    # ---- soft: face validity ------------------------------------------------
    # Every row carries pool, served margin and n so the magnitude check —
    # the one that would have caught the mask bug — can be done from here.
    face = []
    for name, res in persona_results.items():
        for row in res["ranked"][:3]:
            top_pillar = max(row["contributions"], key=lambda c: c["value"])
            face.append({"persona": name, "cbsa": row["cbsa"],
                         "rank": row["rank"], "score": row["score"],
                         "pool": row["pool"], "pool_moe": row["pool_moe"],
                         "n_unweighted": row["n_unweighted"],
                         "balance": (row["balance"]["display"]
                                     if row["balance"]["available"]
                                     else None),
                         "top_pillar": top_pillar["pillar"],
                         "explanation": row["summary_line"],
                         "flags": row["flags"]})
    report["soft"]["face_validity"] = {
        "note": "reviewed by hand each build; every result must be "
                "explainable from its attribution",
        "rows": face}

    # ---- soft: weight sensitivity -------------------------------------------
    baseline = persona_results["A_woman32_ba_men_75k"]
    base_order = [r["cbsa"] for r in baseline["ranked"]]
    taus = {}
    for pillar in engine.PILLARS:
        for direction in (+0.2, -0.2):
            defaults = dict(build.manifest["model_defaults"]["pillar_weights"])
            defaults[pillar] = max(defaults[pillar] * (1 + direction), 0.0)
            body = dict(GOLDEN_VECTORS[0])
            body = {k: body[k] for k in ("self", "seeking") if k in body}
            body["weights"] = defaults
            res = engine.rank(build, engine.parse_request(body))
            order = [r["cbsa"] for r in res["ranked"]]
            common = [c for c in base_order if c in set(order)]
            tau = kendalltau([common.index(c) for c in common],
                             [order.index(c) for c in common]).statistic
            taus[f"{pillar}{'+' if direction > 0 else '-'}20%"] = round(float(tau), 4)
    report["soft"]["weight_sensitivity"] = {
        "kendall_tau": taus, "target": KENDALL_MIN,
        "default_weights": dict(build.manifest["model_defaults"]["pillar_weights"]),
        "note": "six pillars since m2.1.0. Read tau AGAINST the weight: "
                "students (0.04) and weather (0.06) clear the bar largely "
                "because ±20% of a small weight moves few ranks — that is "
                "arithmetic, not robustness, and is reported as such.",
        "pass": all(t >= KENDALL_MIN for t in taus.values())}

    # ---- hard: pleasant-days sanity (item 11) -------------------------------
    # The Normals defect served San Francisco 365; these assertions make
    # the recomputation's two headline claims machine-checked on every
    # build: nobody at 365, and the wettest and coldest metros in the set
    # sit in the bottom half / bottom decile respectively.
    pdays = build.static["pleasant_days"]
    aux = pd.read_csv(RESULTS / "phase2d" / "pleasant_days_ghcn.csv",
                      dtype={"cbsa": str}).set_index("cbsa")
    aux = aux.reindex(build.metro_levels)
    order = pd.Series(pdays, index=build.metro_levels).rank(ascending=False)
    # The brief's "wettest metro near the bottom" guess is DISPROVED by
    # the climate under the approved thresholds: the drizzle belt's wet
    # days are mostly cold days already excluded by temperature (Longview
    # WA, most rain-days, sits mid-pack on real data), and the most
    # inches fall on the warm Gulf coast in storms that leave plenty of
    # mild dry days. What must actually hold is the MECHANISM: the rain
    # term only ever removes days, and removes most where wet days are
    # mild ones. Both wetness measures and the removed-days figure ship
    # so the report can tell that story with numbers.
    coldest = aux["winter_tmin_f"].idxmin()
    n = int(np.isfinite(pdays).sum())
    removed = aux["pleasant_days_no_rain"] - aux["pleasant_days"]
    fin = removed.notna()
    from scipy.stats import spearmanr as _sp
    rain_corr = float(_sp(removed[fin], aux.loc[fin, "rainy_days"]).statistic)
    checks = {
        "max_pleasant_days": round(float(np.nanmax(pdays)), 1),
        "no_metro_at_365": bool(np.nanmax(pdays) < 364.5),
        "rain_term_only_removes": bool((removed[fin] >= -1e-9).all()),
        "median_days_removed_by_rain": round(float(removed[fin].median()), 1),
        "max_days_removed_by_rain": [aux.index[removed.idxmax() == aux.index][0]
                                     if fin.any() else None,
                                     round(float(removed[fin].max()), 1)],
        "removed_vs_rainy_days_spearman": round(rain_corr, 3),
        "wettest_by_rain_days": [aux["rainy_days"].idxmax(),
                                 int(order[aux["rainy_days"].idxmax()])],
        "wettest_by_inches": [aux["annual_precip_in"].idxmax(),
                              int(order[aux["annual_precip_in"].idxmax()])],
        "coldest_metro": coldest,
        "coldest_rank_of_n": [int(order[coldest]), n],
        "coldest_in_bottom_decile": bool(order[coldest] > n * 0.9),
        "metros_with_value": n,
    }
    ok = (checks["no_metro_at_365"] and checks["rain_term_only_removes"]
          and rain_corr > 0.5 and checks["coldest_in_bottom_decile"])
    report["hard"]["pleasant_days_sanity"] = {"pass": bool(ok), **checks}
    if not ok:
        hard_fail.append("pleasant_days_sanity")

    # ---- hard: crime consistency (item 5, D01) ------------------------------
    # Never scored (the scored set carries no crime feature), coverage in
    # [0,1], and property > violent essentially everywhere — the reverse
    # is so rare in US data that more than 5% of metros violating it means
    # the aggregation is broken, not the country.
    from atlas.model.scoring import scored_features
    scored_ids = {f["id"] for f in scored_features(build)}
    v_ = build.crime["violent_crime_rate"]
    p_ = build.crime["property_crime_rate"]
    c_ = build.crime["crime_coverage"]
    have = np.isfinite(v_) & np.isfinite(p_) & np.isfinite(c_)
    viol = [build.metro_levels[i] for i in np.where(have & (v_ >= p_))[0]]
    cov_ok = bool(np.all((c_[np.isfinite(c_)] >= 0)
                         & (c_[np.isfinite(c_)] <= 1.0)))
    crime_checks = {
        "crime_in_scored_set": sorted(x for x in scored_ids if "crime" in x),
        "metros_with_figures": int(have.sum()),
        "metros_above_floor": int(
            (c_[np.isfinite(c_)] >= float(
                build.manifest["crime"]["coverage_floor"])).sum()),
        "coverage_in_unit_interval": cov_ok,
        "violent_ge_property_metros": viol,
    }
    ok = (not crime_checks["crime_in_scored_set"] and cov_ok
          and have.sum() > 300
          and len(viol) <= 0.05 * max(int(have.sum()), 1))
    report["hard"]["crime_consistency"] = {"pass": bool(ok), **crime_checks}
    if not ok:
        hard_fail.append("crime_consistency")

    # ---- soft: external correlation ----------------------------------------
    geo = "metropolitan statistical area/micropolitan statistical area"
    rows = api_get("2024/acs/acs5", {"get": "B09021_001E,B09021_002E",
                                     "for": f"{geo}:*"})
    ext = pd.DataFrame(rows[1:], columns=rows[0]).rename(
        columns={rows[0][-1]: "cbsa"})
    for c in ["B09021_001E", "B09021_002E"]:
        ext[c] = pd.to_numeric(ext[c], errors="coerce")
        ext.loc[ext[c] <= -111111111, c] = np.nan
    ext["alone_share"] = ext["B09021_002E"] / ext["B09021_001E"]
    # B12007 (median age at first marriage) is NOT published at CBSA level in
    # 2024 acs/acs5 — every metro value returns an annotation jam. Verified
    # 2026-09-12; recorded as a finding. Fallback: state medians mapped
    # through each metro's primary state (coarse, flagged as such).
    srows = api_get("2024/acs/acs5", {"get": "B12007_001E,B12007_002E",
                                      "for": "state:*"})
    st = pd.DataFrame(srows[1:], columns=srows[0])
    for c in ["B12007_001E", "B12007_002E"]:
        st[c] = pd.to_numeric(st[c], errors="coerce")
        st.loc[st[c] <= -111111111, c] = np.nan
    st["med_age_marry_state"] = (st["B12007_001E"] + st["B12007_002E"]) / 2
    state_med = dict(zip(st["state"], st["med_age_marry_state"]))
    metros_df = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})
    primary_state = {r["cbsa"]: str(r["states"]).split("+")[0]
                     for _, r in metros_df.iterrows()}
    b_res = persona_results["B_man28_women_never"]
    ours = pd.DataFrame([{"cbsa": r["cbsa"], "score": r["score"],
                          "ratio": (r["balance"]["value"]
                                    if r["balance"]["available"] else None)}
                         for r in b_res["ranked"]])
    ours["med_age_marry_state"] = ours["cbsa"].map(
        lambda c: state_med.get(primary_state.get(c)))
    m = ours.merge(ext[["cbsa", "alone_share"]], on="cbsa")
    corr = {}
    for a in ("score", "ratio"):
        for b in ("alone_share", "med_age_marry_state"):
            mm = m[[a, b]].dropna()
            if len(mm) < 2:
                corr[f"{a}_vs_{b}"] = {"n": int(len(mm)),
                                       "pearson": None, "spearman": None}
                continue
            corr[f"{a}_vs_{b}"] = {
                "n": int(len(mm)),
                "pearson": round(float(pearsonr(mm[a], mm[b]).statistic), 3),
                "spearman": round(float(spearmanr(mm[a], mm[b]).statistic), 3)}
    report["soft"]["external_correlation"] = {
        "n_metros": int(len(m)), "correlations": corr,
        "b12007_finding": "B12007 returns annotation jams for every CBSA in "
                          "2024 acs/acs5 — median age at first marriage is "
                          "not published at metro level; state-level medians "
                          "used through each metro's primary state",
        "framing": "the index measures opportunity, not outcome; partnership "
                   "outcomes reflect decades of sorting and migration, so "
                   "weak correlation is expected and reported as measured "
                   "(§11)"}

    # ---- soft: the Phase 3 Pew reproduction, as recorded -------------------
    report["soft"]["pew_reproduction"] = check_pew_reproduction()

    # ---- soft: ADR 0002 evidence -------------------------------------------
    report["soft"]["served_region_true_cv"] = measure_served_region_cv()

    report["hard_failures"] = hard_fail
    P2.mkdir(parents=True, exist_ok=True)
    (P2 / "validation_report.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"hard_failures": hard_fail,
                      "differential": report["hard"]["cube_vs_sql_differential"],
                      "explanations": {k: v for k, v in
                                       report["hard"]["explanation_invariants"].items()
                                       if k != "problems"},
                      "rank_stability": {k: report["hard"]["rank_stability"][k] for k in
                                         ("pass", "ratio", "searches_touched", "basis")},
                      "rank_stability_old_rule_min_share": gv["old_rule"]["min_share_personas"],
                      "weight_sensitivity": report["soft"]["weight_sensitivity"]["kendall_tau"],
                      "pew": report["soft"]["pew_reproduction"],
                      "kernel_face": report["hard"]["kernel_face_validity"]["pass"],
                      "external": corr}, indent=2))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
