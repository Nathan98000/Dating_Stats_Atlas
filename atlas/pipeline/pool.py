"""Pool queries, Phase 1: GQ-aware allocation weights and precise respondent
counts.

Each person record contributes PWGTP * a_eff(p, c) to metro c, where a_eff is
a_hh for household records, a_gq_noninst for noninstitutional GQ and
a_gq_inst for institutional GQ (correction 5). Replicates use PWGTPr the
same way:

    V(est) = (4/80) * sum_r (est_r - est)^2
    MOE    = 1.645 * sqrt(V)
    CV     = (MOE / 1.645) / est

Respondent support (correction 2) — a record with a_eff = 0.4 is not a whole
respondent in c:

    n_raw    contributing records (Phase 0's inflated definition, reported only)
    n_alloc  sum of a_eff over contributing records
    n_kish   (sum w)^2 / sum w^2 with w = PWGTP * a_eff  (Kish effective
             sample size: allocation fractions and weight variability)
    n_gate   min(n_alloc, n_kish) — the suppression gate input

Institutional GQ (gq=2) is excluded from pool queries by default and included
for calibration, whose published universes contain it.
"""
from __future__ import annotations

import math

import duckdb
import pandas as pd

from fetch import DATA, RESULTS

POOL_DB = DATA / "pool.duckdb"
REP_SUMS = ", ".join(f"sum(pwgtp{i} * a_eff)" for i in range(1, 81))
H_REP_SUMS = ", ".join(f"sum(wgtp{i} * a_hh)" for i in range(1, 81))

QUERY_LOG: list[dict] = []


def open_pool(rebuild: bool = False) -> duckdb.DuckDBPyConnection:
    """Connection to the joined person x metro contribution table (built once).

    contrib carries a_eff (the record's own weight family) so every downstream
    query is a plain filtered sum. hcontrib is the household-record analogue
    used only for the B19001 calibration.
    """
    con = duckdb.connect(str(POOL_DB))
    con.execute("SET preserve_insertion_order=false")
    have = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    if rebuild or "contrib" not in have:
        n_files = len(list((DATA / "pums").glob("*.parquet")))
        assert n_files == 51, f"person extract incomplete: {n_files}/51 states"
        con.execute(f"""
            CREATE OR REPLACE TABLE contrib AS
            SELECT p.*, b.cbsa,
                   CASE p.gq WHEN 0 THEN b.a_hh
                             WHEN 1 THEN b.a_gq_noninst
                             ELSE b.a_gq_inst END AS a_eff
            FROM read_parquet('{DATA / "pums"}/*.parquet') p
            JOIN '{DATA / "bridge.parquet"}' b ON b.st = p.st AND b.puma = p.puma
            WHERE CASE p.gq WHEN 0 THEN b.a_hh
                            WHEN 1 THEN b.a_gq_noninst
                            ELSE b.a_gq_inst END > 0
        """)
        n, states, metros = con.execute(
            "SELECT count(*), count(DISTINCT st), count(DISTINCT cbsa) FROM contrib"
        ).fetchone()
        print(f"contrib built: {n:,} person-metro contributions, "
              f"{states} states, {metros} metros")
        orphans = con.execute(f"""
            SELECT count(*) FROM (
                SELECT DISTINCT st, puma FROM read_parquet('{DATA / "pums"}/*.parquet')
                EXCEPT SELECT DISTINCT st, puma FROM '{DATA / "bridge.parquet"}'
            )""").fetchone()[0]
        assert orphans == 0, f"{orphans} extracted PUMAs missing from bridge"
    if (rebuild or "hcontrib" not in have) and (DATA / "pums_h").exists():
        n_h = len(list((DATA / "pums_h").glob("*.parquet")))
        assert n_h == 51, f"housing extract incomplete: {n_h}/51 states"
        con.execute(f"""
            CREATE OR REPLACE TABLE hcontrib AS
            SELECT h.*, b.cbsa, b.a_hh
            FROM read_parquet('{DATA / "pums_h"}/*.parquet') h
            JOIN '{DATA / "bridge.parquet"}' b ON b.st = h.st AND b.puma = h.puma
            WHERE b.a_hh > 0 AND h.typehugq = 1 AND h.np > 0
        """)
        n = con.execute("SELECT count(*) FROM hcontrib").fetchone()[0]
        print(f"hcontrib built: {n:,} household-metro contributions")
    return con


def _finish(row: tuple) -> dict:
    n_raw, n_alloc, sw2, est, *reps = row
    est = float(est or 0.0)
    n_alloc = float(n_alloc or 0.0)
    sw2 = float(sw2 or 0.0)
    var = 0.05 * sum((float(e or 0.0) - est) ** 2 for e in reps)
    moe = 1.645 * math.sqrt(var)
    cv = (moe / 1.645) / est * 100 if est > 0 else None
    n_kish = est * est / sw2 if sw2 > 0 else 0.0
    return {"n_raw": int(n_raw), "n_alloc": n_alloc, "n_kish": n_kish,
            "n_gate": min(n_alloc, n_kish), "est": est, "moe": moe, "cv_pct": cv}


_CORE = ("count(*), sum(a_eff), sum(pwgtp * pwgtp * a_eff * a_eff), "
         "sum(pwgtp * a_eff)")


def pool(con, cbsa: str, where: str = "TRUE", include_inst: bool = False,
         log: bool = True) -> dict:
    gq = "" if include_inst else " AND gq <> 2"
    row = con.execute(
        f"SELECT {_CORE}, {REP_SUMS} FROM contrib "
        f"WHERE cbsa = ? AND ({where}){gq}", [cbsa]).fetchone()
    out = _finish(row)
    if log:
        QUERY_LOG.append({"cbsa": cbsa, "where": where, **out})
    return out


def pool_by(con, cbsa: str, group_expr: str, where: str = "TRUE",
            include_inst: bool = False) -> pd.DataFrame:
    gq = "" if include_inst else " AND gq <> 2"
    rows = con.execute(
        f"SELECT {group_expr} AS grp, {_CORE}, {REP_SUMS} FROM contrib "
        f"WHERE cbsa = ? AND ({where}){gq} GROUP BY 1", [cbsa]).fetchall()
    return pd.DataFrame([{"grp": r[0], **_finish(r[1:])} for r in rows])


def pool_all_metros(con, where: str = "TRUE", include_inst: bool = False) -> pd.DataFrame:
    """One scan, every metro: the workhorse for the variance battery and
    scale calibration. Returns a frame indexed by cbsa."""
    gq = "" if include_inst else " AND gq <> 2"
    rows = con.execute(
        f"SELECT cbsa, {_CORE}, {REP_SUMS} FROM contrib "
        f"WHERE ({where}){gq} GROUP BY 1").fetchall()
    df = pd.DataFrame([{"cbsa": r[0], **_finish(r[1:])} for r in rows])
    return df.set_index("cbsa")


def pool_grouped(con, dims: str, where: str = "TRUE",
                 include_inst: bool = False) -> pd.DataFrame:
    """Grouped pool estimates in one scan; `dims` is a comma-separated list of
    SQL expressions (e.g. "cbsa, sex"). Returns one row per group."""
    gq = "" if include_inst else " AND gq <> 2"
    ndims = len([d for d in dims.split(",") if d.strip()])
    rows = con.execute(
        f"SELECT {dims}, {_CORE}, {REP_SUMS} FROM contrib "
        f"WHERE ({where}){gq} GROUP BY {', '.join(str(i + 1) for i in range(ndims))}"
    ).fetchall()
    dim_names = [f"d{i}" for i in range(ndims)]
    return pd.DataFrame([dict(zip(dim_names, r[:ndims]), **_finish(r[ndims:]))
                         for r in rows])


def ratio_grouped(con, dims: str, num_expr: str, den_expr: str,
                  where: str = "TRUE", include_inst: bool = True) -> pd.DataFrame:
    """Replicate-consistent ratio of two weighted value sums per group —
    covers shares (0/1 numerators) and means (value numerators)."""
    gq = "" if include_inst else " AND gq <> 2"
    ndims = len([d for d in dims.split(",") if d.strip()])
    parts = [f"sum(pwgtp * a_eff * ({num_expr}))",
             f"sum(pwgtp * a_eff * ({den_expr}))",
             f"sum(a_eff * (CASE WHEN ({num_expr}) <> 0 THEN 1 ELSE 0 END))"]
    for i in range(1, 81):
        parts.append(f"sum(pwgtp{i} * a_eff * ({num_expr}))")
        parts.append(f"sum(pwgtp{i} * a_eff * ({den_expr}))")
    rows = con.execute(
        f"SELECT {dims}, {', '.join(parts)} FROM contrib "
        f"WHERE ({where}){gq} GROUP BY {', '.join(str(i + 1) for i in range(ndims))}"
    ).fetchall()
    out = []
    for r in rows:
        vals = r[ndims:]
        n_top, d_top, n_alloc = (float(vals[0] or 0), float(vals[1] or 0),
                                 float(vals[2] or 0))
        rec = dict(zip([f"d{i}" for i in range(ndims)], r[:ndims]))
        if d_top <= 0:
            out.append({**rec, "n_alloc": n_alloc, "ratio": None,
                        "moe": None, "cv_pct": None})
            continue
        s = n_top / d_top
        reps = []
        for i in range(80):
            nr, dr = float(vals[3 + 2 * i] or 0), float(vals[4 + 2 * i] or 0)
            reps.append(nr / dr if dr > 0 else s)
        var = 0.05 * sum((x - s) ** 2 for x in reps)
        moe = 1.645 * math.sqrt(var)
        out.append({**rec, "n_alloc": n_alloc, "ratio": s, "moe": moe,
                    "cv_pct": (moe / 1.645) / abs(s) * 100 if s != 0 else None})
    return pd.DataFrame(out)


def weighted_median_by(con, dims: str, value: str, where: str = "TRUE",
                       include_inst: bool = True) -> pd.DataFrame:
    """Point-estimate weighted median of `value` per group (no replicate MOE —
    used for the B20002 sanity read where the published MOE is the envelope)."""
    gq = "" if include_inst else " AND gq <> 2"
    ndims = len([d for d in dims.split(",") if d.strip()])
    dim_cols = ", ".join(f"g{i}" for i in range(ndims))
    dim_sel = ", ".join(f"{d.strip()} AS g{i}"
                        for i, d in enumerate(dims.split(",")))
    rows = con.execute(f"""
        WITH base AS (
            SELECT {dim_sel}, {value} AS v, pwgtp * a_eff AS w
            FROM contrib WHERE ({where}){gq}
        ), ordered AS (
            SELECT *, sum(w) OVER (PARTITION BY {dim_cols} ORDER BY v
                                   ROWS UNBOUNDED PRECEDING) AS cw,
                      sum(w) OVER (PARTITION BY {dim_cols}) AS tw
            FROM base
        )
        SELECT {dim_cols}, min(v) FROM ordered WHERE cw >= tw / 2
        GROUP BY {', '.join(str(i + 1) for i in range(ndims))}
    """).fetchall()
    return pd.DataFrame([dict(zip([f"d{i}" for i in range(ndims)], r[:ndims]),
                              median=float(r[ndims])) for r in rows])


def share(con, cbsa: str, num_where: str, den_where: str,
          include_inst: bool = True) -> dict:
    """Replicate-consistent ratio num/den (e.g. never-married share)."""
    gq = "" if include_inst else " AND gq <> 2"
    num = f"CASE WHEN ({num_where}) THEN 1 ELSE 0 END"
    den = f"CASE WHEN ({den_where}) THEN 1 ELSE 0 END"
    parts = [f"sum(pwgtp * a_eff * {num})", f"sum(pwgtp * a_eff * {den})",
             f"sum(a_eff) FILTER (WHERE {num_where})"]
    for i in range(1, 81):
        parts.append(f"sum(pwgtp{i} * a_eff * {num})")
        parts.append(f"sum(pwgtp{i} * a_eff * {den})")
    row = con.execute(
        f"SELECT {', '.join(parts)} FROM contrib "
        f"WHERE cbsa = ? AND (({num_where}) OR ({den_where})){gq}", [cbsa]).fetchone()
    n_top, d_top, n_alloc = float(row[0] or 0), float(row[1] or 0), float(row[2] or 0)
    if d_top <= 0:
        return {"n_alloc": n_alloc, "share": None, "moe": None, "cv_pct": None}
    s = n_top / d_top
    reps = []
    for i in range(80):
        nr, dr = float(row[3 + 2 * i] or 0), float(row[4 + 2 * i] or 0)
        reps.append(nr / dr if dr > 0 else s)
    var = 0.05 * sum((r - s) ** 2 for r in reps)
    moe = 1.645 * math.sqrt(var)
    return {"n_alloc": n_alloc, "share": s, "moe": moe,
            "cv_pct": (moe / 1.645) / s * 100 if s > 0 else None}


def household_income_bands(con, edges: list[float]) -> pd.DataFrame:
    """Household income banded at `edges` (2024 dollars), every metro at once,
    with replicate MOEs — the B19001 calibration query (household universe)."""
    labels = []
    conds = []
    lo = None
    for i, e in enumerate(edges + [None]):
        if lo is None and e is not None:
            conds.append(f"hincp_adj < {e}"); labels.append(f"<{int(e/1000)}k")
        elif e is not None:
            conds.append(f"hincp_adj >= {lo} AND hincp_adj < {e}")
            labels.append(f"{int(lo/1000)}-{int(e/1000)}k")
        else:
            conds.append(f"hincp_adj >= {lo}"); labels.append(f">={int(lo/1000)}k")
        lo = e
    case = "CASE " + " ".join(
        f"WHEN {c} THEN '{i:02d}_{lab}'" for i, (c, lab) in enumerate(zip(conds, labels))
    ) + " END"
    rows = con.execute(f"""
        SELECT cbsa, {case} AS band, count(*), sum(a_hh),
               sum(wgtp * wgtp * a_hh * a_hh), sum(wgtp * a_hh), {H_REP_SUMS}
        FROM hcontrib WHERE hincp_adj IS NOT NULL GROUP BY 1, 2
    """).fetchall()
    return pd.DataFrame([{"cbsa": r[0], "band": r[1], **_finish(r[2:])} for r in rows])


def tier(n_gate: float, cv_pct: float | None) -> str:
    """Display policy: gate on the conservative respondent count (correction 2)."""
    if n_gate < 100 or cv_pct is None or cv_pct > 30:
        return "suppressed"
    if cv_pct > 20:
        return "shown_not_ranked"
    return "ranked"
