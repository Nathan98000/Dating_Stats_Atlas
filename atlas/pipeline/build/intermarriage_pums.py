"""Phase 4 Stage 4 (ADR 0016): the intermarriage check from Census PUMS.

Replaces Pew's metro table in every check and report. For each metro:
the share of people married in the past 12 months (ACS MARHM = 1) whose
spouse is of a different race or ethnicity, from the ACS 2020-2024
5-year PUMS, in Pew's category scheme, with the survey's 80-replicate
margins.

  Pew's scheme (the note under its 2017 metro table): a Hispanic married
  to a non-Hispanic, or non-Hispanic spouses of different groups among
  white, black, Asian (Pacific Islanders included), American Indian,
  multiracial and some other race. That is the kernel's race8 with the
  Asian and Pacific Islander groups merged (PEW7 below); it is asserted
  against the raw RAC1P/HISP codes, not assumed.

  The spouse is the one PUMS links: the household reference person and
  their spouse (RELSHIPP 20 with 21 or 23), households only, the couple
  table's multi-partner exclusion applied -- the same linkage the kernel
  is fitted on. A newlywed whose spouse is not the reference person or
  their spouse (a married couple living in someone else's household) is
  not observed: the standing PUMS limitation, recorded in the rate's
  coverage.

  Weights are every pool figure's: PWGTP x a_eff (the record's allocation
  to the metro), with the 80 replicates; the margin is the successive-
  difference replicate SE x 1.645 (90%). A metro is compared when its
  allocated newlywed sample is at least 200 persons, Pew's own floor.

MARHM is not in the Phase 1 extract, and the raw person files were
evicted after extraction, so the newlywed keys (SERIALNO, SPORDER, with
AGEP, RELSHIPP, RAC1P, HISP to check the join) are read from the Census
Bureau's PUMS API with MARHM = 1 as the predicate, one state at a time,
cached under data/raw/pums_marhm/.

    python -m atlas.pipeline.build.intermarriage_pums fetch
    python -m atlas.pipeline.build.intermarriage_pums rates      -> results/phase4/intermarriage_pums{.json,_metro.csv}
    python -m atlas.pipeline.build.intermarriage_pums compare    -> results/phase4/intermarriage_check.json
    python -m atlas.pipeline.build.intermarriage_pums agreement  -> results/phase4/intermarriage_pew_agreement.json

`agreement` is the one reading of Pew's table Phase 4 makes: the
correlation and median absolute difference between these rates and Pew's,
from the private copy, and never the values (ADR 0016). No check or build
calls it.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import duckdb
import numpy as np
import pandas as pd

from atlas.pipeline.build.pool import POOL_DB
from atlas.pipeline.fetch import DATA, RESULTS, api_get

P4 = RESULTS / "phase4"
RATES_JSON = P4 / "intermarriage_pums.json"
RATES_CSV = P4 / "intermarriage_pums_metro.csv"
CHECK_JSON = P4 / "intermarriage_check.json"
AGREEMENT_JSON = P4 / "intermarriage_pew_agreement.json"
CACHE = DATA / "raw" / "pums_marhm"
DATASET = "2024/acs/acs5/pums"
FIELDS = ["SERIALNO", "SPORDER", "AGEP", "RELSHIPP", "RAC1P", "HISP"]
FLOOR = 200.0          # Pew's floor: at least 200 newlyweds in sample
REPS = list(range(1, 81))
# the served opposite-sex form's leave-one-metro-out record (Phase 3d A2,
# the finished fit) -- the held-out predictions the check compares with
HELDOUT_FORM = "C1_cohorts_plus_shipped"
HELDOUT_RECORD = RESULTS / "phase3d" / "speedup" / "a2" / "lomo_forms.json"
HELDOUT_SAMPLE = "decay_h5"

# Pew's seven groups from the kernel's race8 (Asian and Pacific Islander merged)
PEW7 = {"hispanic": "hispanic", "nh_white": "white", "nh_black": "black",
        "nh_asian": "asian", "nh_nhpi": "asian", "nh_aian": "american_indian",
        "nh_twoplus": "multiracial", "nh_other": "other"}


def _pew7_sql(col: str) -> str:
    return "CASE " + " ".join(f"WHEN {col} = '{k}' THEN '{v}'" for k, v in PEW7.items()) + " END"


# ---- fetch ------------------------------------------------------------------

def fetch(states: list[str] | None = None) -> pd.DataFrame:
    """Newlywed person keys per state (cached JSON under data/raw)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    if states is None:
        con = duckdb.connect(str(POOL_DB), read_only=True)
        states = [r[0] for r in con.execute("SELECT DISTINCT st FROM contrib ORDER BY 1").fetchall()]
        con.close()
    frames = []
    for st in states:
        path = CACHE / f"{st}.json"
        if not path.exists():
            rows = api_get(DATASET, {"get": ",".join(FIELDS + ["MARHM"]),
                                     "MARHM": "1", "for": f"state:{st}"})
            path.write_text(json.dumps(rows))
        rows = json.loads(path.read_text())
        head, body = rows[0], rows[1:]
        df = pd.DataFrame(body, columns=head).loc[:, ~pd.Index(head).duplicated()]
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out = out.rename(columns=str.lower)
    for c in ("sporder", "agep", "relshipp", "rac1p", "hisp", "marhm"):
        out[c] = pd.to_numeric(out[c]).astype(int)
    assert (out["marhm"] == 1).all()
    return out


# ---- rates ------------------------------------------------------------------

def rates() -> dict:
    t0 = time.time()
    keys = fetch()
    con = duckdb.connect(str(POOL_DB), read_only=True)
    con.execute("SET enable_progress_bar=false")
    con.register("nw_keys", keys)
    # the join: every newlywed the API returns in a PUMA the extract kept
    qc_join = con.execute("""
WITH k AS (SELECT DISTINCT serialno, sporder, agep, relshipp, rac1p, hisp FROM nw_keys),
c AS (SELECT DISTINCT serialno, sporder, agep, relshipp, rac1p, hisp, race8 FROM contrib)
SELECT count(*) AS api_newlyweds,
       sum(CASE WHEN c.serialno IS NOT NULL THEN 1 ELSE 0 END) AS in_extract,
       sum(CASE WHEN c.serialno IS NOT NULL AND (c.agep <> k.agep OR c.relshipp <> k.relshipp
                OR c.rac1p <> k.rac1p OR c.hisp <> k.hisp) THEN 1 ELSE 0 END) AS field_mismatch
FROM k LEFT JOIN c USING (serialno, sporder)""").df().iloc[0].to_dict()
    qc_join = {k: int(v) for k, v in qc_join.items()}
    assert qc_join["field_mismatch"] == 0, qc_join
    # PEW7 from race8, asserted against the raw codes: Hispanic is HISP >= 2;
    # otherwise RAC1P 1 white, 2 black, 3-5 American Indian and Alaska
    # Native, 6-7 Asian and Pacific Islander, 8 other, 9 two or more
    bad = con.execute(f"""
SELECT count(*) FROM (SELECT DISTINCT race8, rac1p, hisp FROM contrib) WHERE
  {_pew7_sql('race8')} <> CASE WHEN hisp >= 2 THEN 'hispanic'
    WHEN rac1p = 1 THEN 'white' WHEN rac1p = 2 THEN 'black'
    WHEN rac1p IN (3, 4, 5) THEN 'american_indian' WHEN rac1p IN (6, 7) THEN 'asian'
    WHEN rac1p = 8 THEN 'other' WHEN rac1p = 9 THEN 'multiracial' END""").fetchone()[0]
    assert bad == 0, f"{bad} race8 x RAC1P x HISP combinations disagree with Pew's scheme"
    w_reps = ", ".join(f"sum(p.pwgtp{i} * p.a_eff) AS w{i}" for i in REPS)
    o_reps = ", ".join(f"sum(CASE WHEN out7 THEN p.pwgtp{i} * p.a_eff ELSE 0 END) AS o{i}" for i in REPS)
    con.execute(f"""
CREATE TEMP TABLE multi_partner AS
SELECT serialno FROM (SELECT DISTINCT serialno, sporder FROM contrib WHERE relshipp IN (21, 22, 23, 24))
GROUP BY serialno HAVING count(*) > 1""")
    con.execute(f"""
CREATE TEMP TABLE nw AS
SELECT p.*, s.race8 AS race8_sp, s.sex AS sex_sp,
       ({_pew7_sql('p.race8')} <> {_pew7_sql('s.race8')}) AS out7,
       (p.race8 <> s.race8) AS out8,
       (p.sex <> s.sex) AS opposite_sex
FROM contrib p
JOIN (SELECT DISTINCT serialno, sporder FROM nw_keys) k USING (serialno, sporder)
JOIN contrib s ON s.serialno = p.serialno AND s.cbsa = p.cbsa
WHERE p.gq = 0 AND s.gq = 0
  AND ((p.relshipp = 20 AND s.relshipp IN (21, 23)) OR (p.relshipp IN (21, 23) AND s.relshipp = 20))
  AND p.serialno NOT IN (SELECT serialno FROM multi_partner)""")
    # coverage: newlyweds in the extract's households whose spouse is linked
    cov = con.execute("""
WITH allnw AS (
  SELECT sum(c.pwgtp * c.a_eff) AS w FROM contrib c
  JOIN (SELECT DISTINCT serialno, sporder FROM nw_keys) k USING (serialno, sporder)
  WHERE c.gq = 0)
SELECT (SELECT sum(pwgtp * a_eff) FROM nw) / (SELECT w FROM allnw) AS linked_share,
       (SELECT sum(CASE WHEN NOT opposite_sex THEN pwgtp * a_eff ELSE 0 END) FROM nw)
         / (SELECT sum(pwgtp * a_eff) FROM nw) AS same_sex_share""").df().iloc[0].to_dict()
    per = con.execute(f"""
SELECT p.cbsa, count(*) AS n_records, sum(p.a_eff) AS n_alloc,
       sum(p.pwgtp * p.a_eff) AS w,
       sum(CASE WHEN out7 THEN p.pwgtp * p.a_eff ELSE 0 END) AS o,
       sum(CASE WHEN out8 THEN p.pwgtp * p.a_eff ELSE 0 END) AS o8,
       sum(CASE WHEN opposite_sex THEN p.pwgtp * p.a_eff ELSE 0 END) AS w_os,
       sum(CASE WHEN opposite_sex AND out7 THEN p.pwgtp * p.a_eff ELSE 0 END) AS o_os,
       {w_reps}, {o_reps}
FROM nw p GROUP BY p.cbsa ORDER BY p.cbsa""").df()
    nat = con.execute(f"""
SELECT count(*) AS n_records, sum(p.a_eff) AS n_alloc, sum(p.pwgtp * p.a_eff) AS w,
       sum(CASE WHEN out7 THEN p.pwgtp * p.a_eff ELSE 0 END) AS o,
       sum(CASE WHEN out8 THEN p.pwgtp * p.a_eff ELSE 0 END) AS o8,
       {w_reps}, {o_reps}
FROM nw p""").df().iloc[0]
    con.close()

    def moe(df_or_row, o, w):
        wr = np.array([df_or_row[f"w{i}"] for i in REPS], float).T
        orr = np.array([df_or_row[f"o{i}"] for i in REPS], float).T
        with np.errstate(invalid="ignore", divide="ignore"):
            p = o / w
            pr = orr / wr
        se = np.sqrt(4.0 / 80.0 * np.nansum((pr - np.asarray(p)[..., None]) ** 2, axis=-1))
        return p, 1.645 * se

    rate, moe90 = moe(per, per["o"].to_numpy(float), per["w"].to_numpy(float))
    names = pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})[["cbsa", "cbsa_title"]]
    out = pd.DataFrame({"cbsa": per["cbsa"].astype(str),
                        "n_records": per["n_records"].astype(int),
                        "n_alloc": per["n_alloc"].round(1),
                        "rate": np.round(rate, 5), "moe90": np.round(moe90, 5),
                        "rate_race8": np.round(per["o8"] / per["w"], 5),
                        "rate_opposite_sex": np.round(per["o_os"] / per["w_os"], 5),
                        "meets_floor": per["n_alloc"] >= FLOOR})
    out = names.merge(out, on="cbsa", how="right")[["cbsa", "cbsa_title", "n_records", "n_alloc",
                                                    "rate", "moe90", "rate_race8",
                                                    "rate_opposite_sex", "meets_floor"]]
    nrate, nmoe = moe(nat, float(nat["o"]), float(nat["w"]))
    rec = {
        "definition": ("share of people married in the past 12 months (ACS MARHM = 1) whose "
                       "spouse is of a different race or ethnicity, Pew's scheme (Hispanic of "
                       "any race; non-Hispanic white, black, Asian incl. Pacific Islander, "
                       "American Indian, multiracial, some other race); spouse = the household "
                       "reference person's spouse link (RELSHIPP 20 with 21/23), households only; "
                       "weights PWGTP x a_eff with 80 replicates; MOE = 1.645 x replicate SE"),
        "source": "ACS 2020-2024 5-year PUMS: the Phase 1 extract (pool.duckdb contrib) joined to "
                  f"the MARHM = 1 keys from the Census PUMS API ({DATASET})",
        "join": qc_join,
        "coverage": {"linked_share_of_newlyweds": round(float(cov["linked_share"]), 4),
                     "same_sex_share_of_linked": round(float(cov["same_sex_share"]), 4),
                     "note": "PUMS links only the reference person's spouse; newlywed couples "
                             "living in someone else's household are not observed"},
        "national_metro_universe": {"n_records": int(nat["n_records"]),
                                    "n_alloc": round(float(nat["n_alloc"]), 1),
                                    "rate": round(float(nrate), 5), "moe90": round(float(nmoe), 5),
                                    "rate_race8": round(float(nat["o8"] / nat["w"]), 5)},
        "floor_newlyweds_in_sample": FLOOR,
        "metros_with_rate": int(len(out)),
        "metros_meeting_floor": int(out["meets_floor"].sum()),
        "rate_p10_p50_p90_meeting_floor": [round(float(v), 4) for v in
                                           np.percentile(out.loc[out["meets_floor"], "rate"],
                                                         [10, 50, 90])],
        "moe90_median_meeting_floor": round(float(out.loc[out["meets_floor"], "moe90"].median()), 4),
        "seconds": round(time.time() - t0, 1),
    }
    P4.mkdir(parents=True, exist_ok=True)
    out.to_csv(RATES_CSV, index=False)
    RATES_JSON.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("join", "coverage", "national_metro_universe",
                                          "metros_meeting_floor")}, indent=1))
    return rec


# ---- the reference the kernel's held-out predictions are compared with ------

def reference(metro_levels: list[str]) -> pd.DataFrame:
    """msa_code, metro_name, ref_rate for the metros meeting the floor."""
    df = pd.read_csv(RATES_CSV, dtype={"cbsa": str})
    df = df[df["meets_floor"] & df["cbsa"].isin(set(metro_levels))]
    return pd.DataFrame({"msa_code": df["cbsa"], "metro_name": df["cbsa_title"],
                         "ref_rate": df["rate"].astype(float)}).reset_index(drop=True)


def reference_national() -> float:
    return float(json.loads(RATES_JSON.read_text())["national_metro_universe"]["rate"])


# ---- how much of the fit the reference's newlyweds are ------------------------

def fitting_overlap() -> dict:
    """The newlywed couples' share of the kernel's fitting weight (the
    decay_h5 sample, the kernel universe): the reference comes from the
    same survey as the fit, and a metro's dials are fitted on all of its
    own couples -- newlyweds among them -- so the dial predictions are not
    independent of the reference, while the national-only prediction (the
    kernel refitted without the metro, and the metro's own singles) is."""
    from atlas.pipeline.build import pairing
    where, wt = pairing.decay_sample(5.0)
    keys = fetch()
    con = duckdb.connect(str(POOL_DB), read_only=True)
    con.execute("SET enable_progress_bar=false")
    con.register("nw_keys", keys)
    con.execute("""
CREATE TEMP TABLE nw_households AS
SELECT DISTINCT c.serialno FROM contrib c
JOIN (SELECT DISTINCT serialno, sporder FROM nw_keys) k USING (serialno, sporder)
WHERE c.relshipp IN (20, 21, 23) AND c.gq = 0""")
    per = con.execute(f"""
SELECT cbsa,
       sum(CASE WHEN married AND serialno IN (SELECT serialno FROM nw_households)
                THEN pwgtp * a_eff * {wt} ELSE 0 END) / sum(pwgtp * a_eff * {wt}) AS share
FROM couples WHERE {pairing.KERNEL_UNIVERSE} AND ({where}) GROUP BY cbsa""").df()
    nat = con.execute(f"""
SELECT sum(CASE WHEN married AND serialno IN (SELECT serialno FROM nw_households)
                THEN pwgtp * a_eff * {wt} ELSE 0 END) / sum(pwgtp * a_eff * {wt})
FROM couples WHERE {pairing.KERNEL_UNIVERSE} AND ({where})""").fetchone()[0]
    con.close()
    return {"sample": HELDOUT_SAMPLE,
            "newlywed_share_of_fitting_weight_national": round(float(nat), 4),
            "newlywed_share_of_fitting_weight_by_metro_p10_p50_p90":
                [round(float(v), 4) for v in np.percentile(per["share"], [10, 50, 90])],
            "what": "the newlywed couples' share of the kernel's decay-weighted fitting "
                    "weight: the part of each metro's own couples -- on which its dials are "
                    "fitted -- that the reference also counts"}


# ---- compare ------------------------------------------------------------------

def compare() -> dict:
    from atlas.pipeline.build import kernel as K
    metro_levels = sorted(pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})["cbsa"])
    lomo_forms = json.loads(HELDOUT_RECORD.read_text())
    lomo = [{"cbsa": r["cbsa"], "outgroup_pred": r["forms"][HELDOUT_FORM]["pew_pred"]}
            for r in lomo_forms]
    full, _ = K.load_metro_tables(HELDOUT_SAMPLE)
    nat_ours = json.loads((RESULTS / "phase3" / "kernel_report.json").read_text())[
        "samples"][HELDOUT_SAMPLE]["national_outgroup_share"]
    rec, comp = K.outgroup_comparison(lomo, reference(metro_levels), reference_national(),
                                      nat_ours, metro_levels, full,
                                      P4 / f"outgroup_lomo_{HELDOUT_FORM}.csv")
    out = {"reference": "Census PUMS newlywed intermarriage rate (ADR 0016; "
                        "results/phase4/intermarriage_pums_metro.csv), metros with at least "
                        f"{FLOOR:.0f} newlyweds in sample",
           "predictions": f"{HELDOUT_FORM}'s leave-one-metro-out record on {HELDOUT_SAMPLE} "
                          "(Phase 3d A2, the finished fit): each metro left out, its out-group "
                          "share predicted from the national kernel refitted without it and its "
                          "own composition",
           "comparison": rec, "composition_check": comp,
           "overlap_with_the_fit": fitting_overlap()}
    CHECK_JSON.write_text(json.dumps(out, indent=1, default=float) + "\n")
    ce = rec["corrected_errors"]
    print(f"metros {rec['metros_matched']}; offset {rec['level_offset_ratio_ours_over_reference']}; "
          + ", ".join(f"{m}={ce[m]['median_abs_pts']}" for m in ("national_only", "raw_dial", "shrunk_dial")))
    return out


# ---- the one reading of Pew's table (private copy; aggregates only) ---------

def agreement() -> dict:
    from atlas.pipeline.build import pew_guard
    table = pew_guard.require_pew_table()
    pew = pd.read_csv(table, comment="#", dtype={"msa_code": str})
    pew = pew[pew["msa_code"] != "1"]
    pew_rate = pd.to_numeric(pew["total"], errors="coerce") / 100.0
    pew = pd.DataFrame({"cbsa": pew["msa_code"], "p": pew_rate}).dropna()
    ours = pd.read_csv(RATES_CSV, dtype={"cbsa": str})
    m = pew.merge(ours, on="cbsa")
    out = {"what": "agreement between the PUMS newlywed intermarriage rates (2020-2024) and "
                   "Pew's metro table (2011-2015), read once from the private copy; the "
                   "correlation and median absolute difference only, never the values (ADR 0016)"}
    for label, sub in (("all_matched_metros", m), ("matched_and_meeting_floor", m[m["meets_floor"]])):
        x, y = sub["rate"].to_numpy(float), sub["p"].to_numpy(float)
        out[label] = {"metros": int(len(sub)),
                      "pearson_r": round(float(np.corrcoef(x, y)[0, 1]), 3),
                      "median_abs_difference_pts": round(float(np.median(np.abs(x - y)) * 100), 2)}
    AGREEMENT_JSON.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "rates", "compare", "agreement"])
    a = ap.parse_args()
    if a.cmd == "fetch":
        k = fetch()
        print(f"{len(k):,} newlywed person records across {k['state'].nunique()} states")
    elif a.cmd == "rates":
        rates()
    elif a.cmd == "compare":
        compare()
    else:
        agreement()


if __name__ == "__main__":
    sys.exit(main())
