"""Interim cross-group pairing rate (Phase 2b item 5) — the §4.3/§10.4
counterweight, from real couples in PUMS households, replaced by the Phase 3
assortative kernel (whose gate is reproducing the Pew intermarriage table).

Couples are spouse/partner links to the household reference person:
RELSHIPP 20 (reference person) paired with 21/22/23/24 (opposite- and
same-sex spouses and unmarried partners), codes ASSERTED against the pinned
2020-2024 dictionary the way `pums verify` does, never assumed. PUMS links
only the reference person's partner, so couples in subfamilies are not
observed — recorded as a limitation, not corrected for.

For each metro x sex x race group: the share of partnered people (18-70,
households only) whose partner is outside their own group, weighted by
PWGTP x a_eff like every pool figure. The margin is the survey's own
80-replicate successive-difference MOE, computed per cell and stored as
replicate sums so serve-time aggregations over race selections carry an
EXACT measured margin. The Gate 0 one-sided model does not extend here —
it was trained on weighted totals, not ratios — and it does not need to:
the replicate machinery it was calibrated against is computable directly
for this fixed feature, so served equals measured by construction.

Outputs (interim cells, unchanged since m1.2.0):
  data/pairing_cells.parquet          per (cbsa, sex, race8) cell sums
  results/phase2/pairing_metro.csv    metro-level composition (all groups)
  results/phase2/pairing_report.json  QC + national sanity numbers

Phase 3 (m3.0.0) — the couple table the assortative kernel is fitted on.
The linkage above is reused as is; only the grain changes. A `couples`
table in pool.duckdb holds one row per couple SIDE (each member once as
the "seeker" with the other as the "partner"), carrying the member's own
PWGTP x a_eff and 80 replicates, both members' age/edu4/race8, the union
clock (the reference person's MARHYP for married couples; unmarried
partners have no formation year in PUMS) and the survey year. From it:

  data/couple_table_national_<sample>.parquet
      (sex_s, age_s, edu_s, race_s) x (age_c, edu_c, race_c), weighted
      count + n_alloc + sumw2 + 80 replicate sums, opposite-sex couples
      with both members 18-70; one file per fitting sample
      (recent = unions formed since 2019 plus all unmarried partners;
       stock = every union; decay_h<H> = every union weighted
       0.5^((survey year - union year)/H), unmarried partners at 1)
  data/couple_table_metro_<sample>.parquet
      the same grain by metro, without replicates (the per-metro dial
      fits and leave-one-metro-out refits read this)
  data/couple_marginals_metro_<sample>.parquet
      per metro x sex_s: same-race, same-education and |age gap|<=3
      shares with n_alloc, Kish n and 80-replicate MOE — the measured
      precision that weights each metro's dial (item 3), no new data
  results/phase3/couple_table_report.json
      counts, discordance and the standing limitation, per sample

Standing limitation, recorded here and in the report: PUMS links only the
reference person's spouse/partner, so couples in subfamilies are not
observed.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.build.pums_extract import load_dictionary
from atlas.pipeline.fetch import DATA, RESULTS

P2 = RESULTS / "phase2"
P3 = RESULTS / "phase3"
CELLS_PATH = DATA / "pairing_cells.parquet"
PARTNER_CODES = (21, 22, 23, 24)
MARRIED_CODES = (21, 23)
SAME_SEX_CODES = (23, 24)
N_GATE_MIN = 100.0
# Phase 3 fitting-sample clock: a union "formed in the last five years"
# is one whose MARHYP is at or after this year (the 5-year file runs
# 2020-2024, so 2019 is one to five years before each record's survey).
RECENT_SINCE = 2019
REPS = list(range(1, 81))


def verify_relshipp() -> dict[str, str]:
    """Assert the couple-link codes against the pinned dictionary."""
    names, vals = load_dictionary()
    assert "relationship" in names["RELSHIPP"].lower(), names["RELSHIPP"]
    want = {
        "20": "reference person",
        "21": "opposite-sex husband/wife/spouse",
        "22": "opposite-sex unmarried partner",
        "23": "same-sex husband/wife/spouse",
        "24": "same-sex unmarried partner",
    }
    seen = {}
    for code, expect in want.items():
        labels = [lab for lo, hi, lab in vals["RELSHIPP"] if lo == code]
        assert labels, f"RELSHIPP={code} not in dictionary"
        assert labels[0].lower() == expect, (
            f"RELSHIPP={code} label {labels[0]!r} != expected {expect!r}")
        seen[code] = labels[0]
    return seen


def _side_sql(member: str, partner: str) -> str:
    """Aggregate one member of each couple into (cbsa, sex, race8) cells.
    Weights are the member's own PWGTP (and replicates) x a_eff, the same
    convention as every pool figure."""
    out = f"(CASE WHEN {member}.race8 <> {partner}.race8 THEN 1 ELSE 0 END)"
    reps = ",\n  ".join(
        f"sum({member}.pwgtp{i} * {member}.a_eff * {out}) AS num_r{i}, "
        f"sum({member}.pwgtp{i} * {member}.a_eff) AS den_r{i}"
        for i in range(1, 81))
    return f"""
SELECT {member}.cbsa AS cbsa, {member}.sex AS sex, {member}.race8 AS race8,
  sum({member}.pwgtp * {member}.a_eff * {out}) AS num,
  sum({member}.pwgtp * {member}.a_eff) AS den,
  sum({member}.a_eff) AS n_alloc,
  sum({member}.pwgtp * {member}.a_eff * {member}.pwgtp * {member}.a_eff) AS sumw2,
  {reps}
FROM contrib r JOIN contrib p
  ON r.serialno = p.serialno AND r.cbsa = p.cbsa
WHERE r.relshipp = 20 AND p.relshipp IN {PARTNER_CODES}
  AND r.gq = 0 AND p.gq = 0
  AND {member}.agep BETWEEN 18 AND 70
  AND r.serialno NOT IN (SELECT serialno FROM multi_partner)
GROUP BY 1, 2, 3
"""


def _replicate_moe(num: np.ndarray, den: np.ndarray, num_r: np.ndarray,
                   den_r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(rate, moe) with the successive-difference variance over 80
    replicates: V = (4/80) * sum((r_i - r)^2), MOE = 1.645 * sqrt(V)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(den > 0, num / np.maximum(den, 1e-9), np.nan)
        rr = np.where(den_r > 0, num_r / np.maximum(den_r, 1e-9),
                      rate[:, None])
    var = 4.0 / 80.0 * np.nansum((rr - rate[:, None]) ** 2, axis=1)
    return rate, 1.645 * np.sqrt(var)


def build() -> None:
    P2.mkdir(parents=True, exist_ok=True)
    report: dict = {"relshipp_labels": verify_relshipp()}

    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    # Households where more than one person claims the partner slot are a
    # data anomaly the pairing cannot disambiguate: excluded, counted.
    con.execute(f"""
CREATE OR REPLACE TEMP TABLE multi_partner AS
SELECT serialno FROM (
  SELECT DISTINCT serialno, sporder FROM contrib
  WHERE relshipp IN {PARTNER_CODES}
) GROUP BY serialno HAVING count(*) > 1
""")
    report["households_with_multiple_partner_records"] = int(
        con.execute("SELECT count(*) FROM multi_partner").fetchone()[0])

    ref = con.execute(_side_sql("r", "p")).df()
    prt = con.execute(_side_sql("p", "r")).df()
    for df in (ref, prt):
        df["sex"] = df["sex"].astype(int)
        df["race8"] = df["race8"].astype(str)

    num_cols = [c for c in ref.columns if c not in ("cbsa", "sex", "race8")]
    cells = (pd.concat([ref, prt])
             .groupby(["cbsa", "sex", "race8"], as_index=False)[num_cols]
             .sum())
    cells["sex"] = cells["sex"].map({1: "male", 2: "female"})
    assert cells["sex"].notna().all()

    # National sanity, reported not tuned: partnered share of the adult pool
    # and the national out-group share (Pew's newlywed figure was 17% in
    # 2015; the partnered STOCK is expected lower).
    adults = con.execute("""SELECT sum(pwgtp * a_eff) FROM contrib
                            WHERE agep BETWEEN 18 AND 70 AND gq <> 2""").fetchone()[0]
    report["partnered_weighted_total"] = float(cells["den"].sum())
    report["partnered_share_of_adult_pool"] = float(cells["den"].sum() / adults)
    assert 0.30 < report["partnered_share_of_adult_pool"] < 0.80, (
        "partnered share implausible — pairing join is wrong")
    report["national_out_group_share"] = float(
        cells["num"].sum() / cells["den"].sum())
    report["ref_vs_partner_side_weight_ratio"] = float(
        ref["den"].sum() / prt["den"].sum())
    report["cells"] = int(len(cells))
    report["limitation"] = (
        "PUMS links only the reference person's spouse/partner; couples in "
        "subfamilies are not observed. Observed couples describe who "
        "matched, not who was available — the copy says how couples here "
        "actually pair, never what people here want.")

    cells.to_parquet(CELLS_PATH, index=False)

    # Metro-level composition (both sexes, all groups) for the metro pages.
    rep_num = [f"num_r{i}" for i in range(1, 81)]
    rep_den = [f"den_r{i}" for i in range(1, 81)]
    m = cells.groupby("cbsa", as_index=False)[
        ["num", "den", "n_alloc", "sumw2"] + rep_num + rep_den].sum()
    with np.errstate(invalid="ignore", divide="ignore"):
        kish = np.where(m["sumw2"] > 0, m["den"] ** 2 / m["sumw2"], 0.0)
    gate = np.minimum(m["n_alloc"].to_numpy(), kish)
    rate, moe = _replicate_moe(m["num"].to_numpy(), m["den"].to_numpy(),
                               m[rep_num].to_numpy(), m[rep_den].to_numpy())
    below = gate < N_GATE_MIN
    rate[below] = np.nan
    moe[below] = np.nan
    out = pd.DataFrame({"cbsa": m["cbsa"],
                        "cross_group_pairing_rate": rate,
                        "cross_group_pairing_moe": moe,
                        "cross_group_pairing_n": gate})
    out.to_csv(P2 / "pairing_metro.csv", index=False)
    report["metro_level"] = {
        "metros_with_rate": int((~np.isnan(rate)).sum()),
        "metros_below_gate": int(below.sum()),
        "rate_p10_p50_p90": [round(float(x), 4) for x in
                             np.nanpercentile(rate, [10, 50, 90])],
        "median_moe": round(float(np.nanmedian(moe)), 4)}

    (P2 / "pairing_report.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: report[k] for k in
                      ("households_with_multiple_partner_records",
                       "partnered_share_of_adult_pool",
                       "national_out_group_share", "cells", "metro_level")},
                     indent=2))
    print(f"pairing cells -> {CELLS_PATH}")


# ---------------------------------------------------------------------------
# Phase 3: the couple table
# ---------------------------------------------------------------------------

def _rep_cols(prefix: str, alias: str) -> str:
    return ", ".join(f"{prefix}.pwgtp{i} AS {alias}{i}" for i in REPS)


def build_couples_table(con) -> dict:
    """One row per couple side in pool.duckdb (`couples`). Reuses the
    linkage exactly: RELSHIPP 20 joined to 21/22/23/24 within serialno
    and metro, household records only, multi-partner households out."""
    con.execute(f"""
CREATE OR REPLACE TEMP TABLE multi_partner AS
SELECT serialno FROM (
  SELECT DISTINCT serialno, sporder FROM contrib
  WHERE relshipp IN {PARTNER_CODES}
) GROUP BY serialno HAVING count(*) > 1
""")
    con.execute(f"""
CREATE OR REPLACE TABLE couples AS
WITH pr AS (
  SELECT r.cbsa, r.serialno, r.svy_year, p.relshipp AS partner_code,
         (p.relshipp IN {MARRIED_CODES}) AS married,
         (p.relshipp IN {SAME_SEX_CODES}) AS same_sex,
         r.marhyp AS marhyp_ref, p.marhyp AS marhyp_partner,
         r.sex AS sex_r, r.agep AS age_r, r.edu4 AS edu_r, r.race8 AS race_r,
         p.sex AS sex_p, p.agep AS age_p, p.edu4 AS edu_p, p.race8 AS race_p,
         r.a_eff AS a_eff_r, p.a_eff AS a_eff_p,
         r.pwgtp AS pwgtp_r, p.pwgtp AS pwgtp_p,
         {_rep_cols("r", "r_rep")}, {_rep_cols("p", "p_rep")}
  FROM contrib r JOIN contrib p
    ON r.serialno = p.serialno AND r.cbsa = p.cbsa
  WHERE r.relshipp = 20 AND p.relshipp IN {PARTNER_CODES}
    AND r.gq = 0 AND p.gq = 0
    AND r.serialno NOT IN (SELECT serialno FROM multi_partner)
)
SELECT 'ref' AS side, cbsa, serialno, svy_year, partner_code, married, same_sex,
       CASE WHEN married THEN marhyp_ref END AS union_year,
       marhyp_ref, marhyp_partner,
       sex_r AS sex_s, age_r AS age_s, edu_r AS edu_s, race_r AS race_s,
       sex_p AS sex_c, age_p AS age_c, edu_p AS edu_c, race_p AS race_c,
       a_eff_r AS a_eff, a_eff_p AS a_eff_other, pwgtp_r AS pwgtp,
       {", ".join(f"r_rep{i} AS pwgtp{i}" for i in REPS)}
FROM pr
UNION ALL
SELECT 'partner' AS side, cbsa, serialno, svy_year, partner_code, married, same_sex,
       CASE WHEN married THEN marhyp_ref END AS union_year,
       marhyp_ref, marhyp_partner,
       sex_p AS sex_s, age_p AS age_s, edu_p AS edu_s, race_p AS race_s,
       sex_r AS sex_c, age_r AS age_c, edu_r AS edu_c, race_r AS race_c,
       a_eff_p AS a_eff, a_eff_r AS a_eff_other, pwgtp_p AS pwgtp,
       {", ".join(f"p_rep{i} AS pwgtp{i}" for i in REPS)}
FROM pr
""")
    qc = con.execute("""
SELECT count(*) AS sides,
       count(DISTINCT serialno) AS households,
       sum(CASE WHEN a_eff <> a_eff_other THEN 1 ELSE 0 END) AS a_eff_mismatch,
       sum(CASE WHEN married AND union_year IS NULL THEN 1 ELSE 0 END) AS married_no_year,
       sum(CASE WHEN married AND marhyp_ref IS NOT NULL AND marhyp_partner IS NOT NULL
                     AND marhyp_ref <> marhyp_partner THEN 1 ELSE 0 END) AS married_discordant_year,
       sum(CASE WHEN married THEN 1 ELSE 0 END) AS married_sides,
       sum(CASE WHEN same_sex THEN 1 ELSE 0 END) AS same_sex_sides,
       sum(CASE WHEN age_s BETWEEN 18 AND 70 AND age_c BETWEEN 18 AND 70 THEN 1 ELSE 0 END) AS both_18_70,
       sum(CASE WHEN union_year > svy_year THEN 1 ELSE 0 END) AS union_after_survey
FROM couples""").df().iloc[0].to_dict()
    qc = {k: int(v) for k, v in qc.items()}
    assert qc["a_eff_mismatch"] == 0, "household members carry different a_eff"
    assert qc["union_after_survey"] == 0, "MARHYP after the survey year"
    return qc


# sample -> (row filter, weight expression); the decay samples are built by
# decay_sample(h)
SAMPLES = {
    "recent": (f"(NOT married OR union_year >= {RECENT_SINCE})", "1.0"),
    "stock": ("TRUE", "1.0"),
}


def decay_sample(half_life: float) -> tuple[str, str]:
    """Every union, weighted 0.5^(years since formation / half_life);
    unmarried partners carry no formation year and weight 1 (treated as
    current unions — a stated choice, not a measurement)."""
    return ("TRUE",
            f"(CASE WHEN married THEN power(0.5, (svy_year - union_year) / "
            f"{float(half_life)}) ELSE 1.0 END)")


KERNEL_UNIVERSE = ("NOT same_sex AND age_s BETWEEN 18 AND 70 "
                   "AND age_c BETWEEN 18 AND 70 "
                   "AND edu_s IS NOT NULL AND edu_c IS NOT NULL "
                   "AND NOT (married AND union_year IS NULL)")


def _agg_cols(wt: str, replicates: bool) -> str:
    cols = [f"sum(pwgtp * a_eff * {wt}) AS w",
            f"sum(a_eff * {wt}) AS n_alloc",
            f"sum(pwgtp * a_eff * {wt} * pwgtp * a_eff * {wt}) AS sumw2",
            "count(*) AS n_rows"]
    if replicates:
        cols += [f"sum(pwgtp{i} * a_eff * {wt}) AS w_r{i}" for i in REPS]
    return ",\n       ".join(cols)


def national_table(con, sample: str, spec: tuple[str, str] | None = None,
                   replicates: bool = True) -> pd.DataFrame:
    """The national couple table at the kernel grain for one sample."""
    where, wt = spec or SAMPLES[sample]
    df = con.execute(f"""
SELECT sex_s, age_s, edu_s, race_s, age_c, edu_c, race_c,
       {_agg_cols(wt, replicates)}
FROM couples
WHERE {KERNEL_UNIVERSE} AND ({where})
GROUP BY 1, 2, 3, 4, 5, 6, 7
""").df()
    df["sex_s"] = df["sex_s"].map({1: "male", 2: "female"})
    assert df["sex_s"].notna().all()
    return df


def metro_table(con, sample: str, spec: tuple[str, str] | None = None) -> pd.DataFrame:
    """The same grain by metro, no replicates, with a split-half `fold`
    keyed on the household serial (both sides of a couple land in the
    same half) for the leave-one-metro-out dial test."""
    where, wt = spec or SAMPLES[sample]
    df = con.execute(f"""
SELECT cbsa, hash(serialno) % 2 AS fold, sex_s, age_s, edu_s, race_s, age_c, edu_c, race_c,
       {_agg_cols(wt, False)}
FROM couples
WHERE {KERNEL_UNIVERSE} AND ({where})
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
""").df()
    df["fold"] = df["fold"].astype(int)
    df["sex_s"] = df["sex_s"].map({1: "male", 2: "female"})
    return df


def metro_marginals(con, sample: str, spec: tuple[str, str] | None = None) -> pd.DataFrame:
    """Per metro x seeker sex: the three components' homophily shares —
    same race8, same edu4, |age gap| <= 3 — each with n_alloc, Kish n and
    the 80-replicate MOE of the share. These are the replicate margins
    that weight each metro's dial (item 3)."""
    where, wt = spec or SAMPLES[sample]
    parts = []
    for name, ind in (("race", "race_s = race_c"), ("edu", "edu_s = edu_c"),
                      ("age", "abs(age_c - age_s) <= 3")):
        parts.append(f"sum(pwgtp * a_eff * {wt} * (CASE WHEN {ind} THEN 1 ELSE 0 END)) AS num_{name}")
        parts += [f"sum(pwgtp{i} * a_eff * {wt} * (CASE WHEN {ind} THEN 1 ELSE 0 END)) AS num_{name}_r{i}"
                  for i in REPS]
    df = con.execute(f"""
SELECT cbsa, sex_s,
       sum(pwgtp * a_eff * {wt}) AS den,
       sum(a_eff * {wt}) AS n_alloc,
       sum(pwgtp * a_eff * {wt} * pwgtp * a_eff * {wt}) AS sumw2,
       {", ".join(f"sum(pwgtp{i} * a_eff * {wt}) AS den_r{i}" for i in REPS)},
       {", ".join(parts)}
FROM couples
WHERE {KERNEL_UNIVERSE} AND ({where})
GROUP BY GROUPING SETS ((cbsa, sex_s), (cbsa))
""").df()
    df["sex_s"] = df["sex_s"].map({1: "male", 2: "female"}).fillna("all")
    den = df["den"].to_numpy()
    den_r = df[[f"den_r{i}" for i in REPS]].to_numpy()
    out = df[["cbsa", "sex_s", "den", "n_alloc", "sumw2"]].copy()
    with np.errstate(invalid="ignore", divide="ignore"):
        out["n_kish"] = np.where(df["sumw2"] > 0, den ** 2 / df["sumw2"], 0.0)
    for name in ("race", "edu", "age"):
        num = df[f"num_{name}"].to_numpy()
        num_r = df[[f"num_{name}_r{i}" for i in REPS]].to_numpy()
        rate, moe = _replicate_moe(num, den, num_r, den_r)
        out[f"share_{name}"] = rate
        out[f"moe_{name}"] = moe
    return out


def build_couple_tables(samples: dict[str, tuple[str, str]] | None = None,
                        rebuild_couples: bool = True) -> dict:
    """Build `couples` (unless it exists and rebuild_couples is False) and
    write the national / metro / marginal tables for each fitting sample.
    Returns the report dict (also written; merged into an existing report
    so the sample entries accumulate)."""
    P3.mkdir(parents=True, exist_ok=True)
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    t0 = time.time()
    have = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    path = P3 / "couple_table_report.json"
    report: dict = json.loads(path.read_text()) if path.exists() else {}
    if rebuild_couples or "couples" not in have:
        report.update({"relshipp_labels": verify_relshipp(),
                       "recent_since": RECENT_SINCE,
                       "linkage_qc": build_couples_table(con)})
        report["seconds_couples_table"] = round(time.time() - t0, 1)
    report["limitation"] = (
        "PUMS links only the reference person's spouse/partner; couples in "
        "subfamilies are not observed. Opposite-sex couples with both "
        "members aged 18-70 enter the kernel table; same-sex couples are "
        "counted and excluded from the fit (the kernel is applied to every "
        "search, including same-sex ones, without a separately modelled "
        "same-sex pairing pattern).")
    report.setdefault("samples", {})
    for name, spec in (samples or SAMPLES).items():
        t1 = time.time()
        nat = national_table(con, name, spec)
        nat.to_parquet(DATA / f"couple_table_national_{name}.parquet", index=False)
        met = metro_table(con, name, spec)
        met.to_parquet(DATA / f"couple_table_metro_{name}.parquet", index=False)
        mar = metro_marginals(con, name, spec)
        mar.to_parquet(DATA / f"couple_marginals_metro_{name}.parquet", index=False)
        w = nat["w"].to_numpy(); s2 = nat["sumw2"].to_numpy()
        report["samples"][name] = {
            "where": spec[0], "weight": spec[1],
            "national_cells": int(len(nat)),
            "couple_sides_rows": int(nat["n_rows"].sum()),
            "n_alloc": round(float(nat["n_alloc"].sum()), 1),
            "n_kish": round(float(w.sum() ** 2 / s2.sum()), 1),
            "weighted_sides": round(float(w.sum()), 1),
            "metros": int(met["cbsa"].nunique()),
            "metro_rows": int(len(met)),
            "seconds": round(time.time() - t1, 1),
        }
        print(f"[{name}] {report['samples'][name]}", flush=True)
    path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"couple tables -> {DATA} ({time.time() - t0:.0f}s)")
    return report


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["couples"]:
        build_couple_tables()
    else:
        build()
