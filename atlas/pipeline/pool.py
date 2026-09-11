"""The pool query: weighted estimate, unweighted count, MOE and CV for any
filter over the derived fields, in any of the ten metros.

Each person record in PUMA p contributes PWGTP * a(p, c) to metro c, and each
of the 80 replicate estimates uses PWGTPr * a(p, c) the same way (successive
difference replication):

    V(est) = (4/80) * sum_r (est_r - est)^2
    MOE    = 1.645 * sqrt(V)          # ACS margins are 90% confidence
    CV     = (MOE / 1.645) / est

Institutional group quarters (gq=2) are excluded from pool queries by default
but includable for calibration against published tables, whose universe
contains them.
"""
from __future__ import annotations

import math
from pathlib import Path

import duckdb
import pandas as pd

from fetch import DATA, RESULTS

POOL_DB = DATA / "pool.duckdb"
REP_SUMS = ", ".join(f"sum(pwgtp{i} * a)" for i in range(1, 81))

# Every scalar pool() result lands here so checks.py can test MOE ~ 1/sqrt(n).
QUERY_LOG: list[dict] = []


def open_pool(rebuild: bool = False) -> duckdb.DuckDBPyConnection:
    """Connection to the joined person x metro contribution table (built once)."""
    con = duckdb.connect(str(POOL_DB))
    con.execute("SET preserve_insertion_order=false")
    have = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    if rebuild or "contrib" not in have:
        con.execute(f"""
            CREATE OR REPLACE TABLE bridge AS
            SELECT b.st, b.puma, b.cbsa, b.a
            FROM '{DATA / "bridge.parquet"}' b
            JOIN read_csv('{RESULTS / "metros.csv"}', header=true) m
              ON b.cbsa = CAST(m.cbsa AS VARCHAR)
            WHERE b.a > 0
        """)
        con.execute(f"""
            CREATE OR REPLACE TABLE contrib AS
            SELECT p.*, b.cbsa, b.a
            FROM read_parquet('{DATA / "pums"}/*.parquet') p
            JOIN bridge b ON b.st = p.st AND b.puma = p.puma
        """)
        n, states = con.execute(
            "SELECT count(*), count(DISTINCT st) FROM contrib").fetchone()
        print(f"pool table built: {n:,} person-metro contributions from {states} states")
        # Every (st, puma) present in the PUMS extract must be in the bridge;
        # the extract already inner-joined on the keep list, so assert parity.
        orphans = con.execute(f"""
            SELECT count(*) FROM (
                SELECT DISTINCT st, puma FROM read_parquet('{DATA / "pums"}/*.parquet')
                EXCEPT SELECT DISTINCT st, puma FROM bridge
            )
        """).fetchone()[0]
        assert orphans == 0, f"{orphans} extracted PUMAs missing from bridge"
    return con


def _finish(n: int, est: float | None, reps: list[float]) -> dict:
    est = float(est or 0.0)
    var = 0.05 * sum((float(e or 0.0) - est) ** 2 for e in reps)
    moe = 1.645 * math.sqrt(var)
    cv = (moe / 1.645) / est * 100 if est > 0 else None
    return {"n": int(n), "est": est, "moe": moe, "cv_pct": cv}


def pool(con: duckdb.DuckDBPyConnection, cbsa: str, where: str = "TRUE",
         include_inst: bool = False, log: bool = True) -> dict:
    gq = "" if include_inst else " AND gq <> 2"
    row = con.execute(
        f"SELECT count(*), sum(pwgtp * a), {REP_SUMS} "
        f"FROM contrib WHERE cbsa = ? AND ({where}){gq}", [cbsa]
    ).fetchone()
    out = _finish(row[0], row[1], list(row[2:]))
    if log:
        QUERY_LOG.append({"cbsa": cbsa, "where": where, **out})
    return out


def pool_by(con: duckdb.DuckDBPyConnection, cbsa: str, group_expr: str,
            where: str = "TRUE", include_inst: bool = False) -> pd.DataFrame:
    gq = "" if include_inst else " AND gq <> 2"
    rows = con.execute(
        f"SELECT {group_expr} AS grp, count(*), sum(pwgtp * a), {REP_SUMS} "
        f"FROM contrib WHERE cbsa = ? AND ({where}){gq} GROUP BY 1", [cbsa]
    ).fetchall()
    recs = []
    for r in rows:
        recs.append({"grp": r[0], **_finish(r[1], r[2], list(r[3:]))})
    return pd.DataFrame(recs)


def share(con: duckdb.DuckDBPyConnection, cbsa: str, num_where: str,
          den_where: str, include_inst: bool = True) -> dict:
    """Replicate-consistent ratio estimate num/den (e.g. never-married share).

    Each replicate share uses that replicate's numerator and denominator, so
    the covariance between the two is handled exactly rather than through the
    ACS approximation formula.
    """
    gq = "" if include_inst else " AND gq <> 2"
    num = f"CASE WHEN ({num_where}) THEN 1 ELSE 0 END"
    den = f"CASE WHEN ({den_where}) THEN 1 ELSE 0 END"
    parts = [f"sum(pwgtp * a * {num})", f"sum(pwgtp * a * {den})",
             f"count(*) FILTER (WHERE {num_where})"]
    for i in range(1, 81):
        parts.append(f"sum(pwgtp{i} * a * {num})")
        parts.append(f"sum(pwgtp{i} * a * {den})")
    row = con.execute(
        f"SELECT {', '.join(parts)} FROM contrib WHERE cbsa = ? AND (({num_where}) OR ({den_where})){gq}",
        [cbsa]).fetchone()
    n_top, d_top, n_unw = float(row[0] or 0), float(row[1] or 0), int(row[2])
    if d_top <= 0:
        return {"n": n_unw, "share": None, "moe": None, "cv_pct": None}
    s = n_top / d_top
    reps = []
    for i in range(80):
        nr, dr = float(row[3 + 2 * i] or 0), float(row[4 + 2 * i] or 0)
        reps.append(nr / dr if dr > 0 else s)
    var = 0.05 * sum((r - s) ** 2 for r in reps)
    moe = 1.645 * math.sqrt(var)
    return {"n": n_unw, "share": s, "moe": moe,
            "cv_pct": (moe / 1.645) / s * 100 if s > 0 else None}


def tier(n: int, cv_pct: float | None) -> str:
    """Display policy for a pool cell."""
    if n < 100 or cv_pct is None or cv_pct > 30:
        return "suppressed"
    if cv_pct > 20:
        return "shown_not_ranked"
    return "ranked"
