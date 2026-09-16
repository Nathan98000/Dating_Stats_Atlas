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

Outputs:
  data/pairing_cells.parquet          per (cbsa, sex, race8) cell sums
  results/phase2/pairing_metro.csv    metro-level composition (all groups)
  results/phase2/pairing_report.json  QC + national sanity numbers
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.build.pums_extract import load_dictionary
from atlas.pipeline.fetch import DATA, RESULTS

P2 = RESULTS / "phase2"
CELLS_PATH = DATA / "pairing_cells.parquet"
PARTNER_CODES = (21, 22, 23, 24)
N_GATE_MIN = 100.0


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


if __name__ == "__main__":
    build()
