"""PUMS 2020-2024 5-year person extract: one state at a time, slimmed to Parquet.

Two jobs:
  1. verify: parse PUMS_Data_Dictionary_2020-2024.csv and assert the exact
     semantics of every variable this pipeline relies on (the GQ variable and
     the PUMA vintage in particular). Writes results/pums_dictionary_check.md.
  2. extract: download csv_p{st}.zip, unzip, select + derive columns into
     data/pums/{st}.parquet with DuckDB, then delete the CSV and evict the zip
     (disk on this machine is tight). Only rows in PUMAs that allocate to one
     of the ten target CBSAs are kept; all ages are kept so calibration can
     compare against published all-age tables.

Derived fields:
  marital3   never / married (MSP 1-2, incl. separated=no) / formerly (MSP 3-5)
             — "not currently married" downstream = MSP in (3,4,5,6)
  edu4       lt_hs (SCHL<=15) / hs (16-17) / some_college (18-20) / ba_plus (21-24)
  inc_adj    PINCP * ADJINC / 1e6  (constant 2024 dollars)
  incband7   <25k / 25-50 / 50-75 / 75-100 / 100-150 / 150-200 / >=200k
  race8      hispanic (HISP>=2) else NH white/black/asian/aian/nhpi/twoplus/other
  gq         0 household, 1 noninstitutional GQ (RELSHIPP=38),
             2 institutional GQ (RELSHIPP=37)
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import duckdb

from fetch import DATA, RESULTS, disk_free_gb, evict, fetch

PUMS_BASE = "https://www2.census.gov/programs-surveys/acs/data/pums/2024/5-Year"
DICT_URL = (
    "https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/"
    "PUMS_Data_Dictionary_2020-2024.csv"
)
PUMS_DIR = DATA / "pums"
TMP_DIR = DATA / "tmp"
EXTRACT_LOG = RESULTS / "pums_extract_log.json"
MIN_FREE_GB = 5.0

REPWTS = [f"PWGTP{i}" for i in range(1, 81)]
BASE_COLS = ["SERIALNO", "SPORDER", "STATE", "PUMA", "AGEP", "SEX", "MSP", "SCHL",
             "PINCP", "ADJINC", "RAC1P", "HISP", "RELSHIPP", "PWGTP"]


def load_dictionary() -> tuple[dict, dict]:
    """Parse the CSV data dictionary into {var: label} and {var: [(min,max,label)]}."""
    path = fetch(DICT_URL)
    names: dict[str, str] = {}
    vals: dict[str, list] = defaultdict(list)
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if not row:
                continue
            if row[0] == "NAME" and len(row) >= 5:
                names.setdefault(row[1], row[4])
            elif row[0] == "VAL" and len(row) >= 7:
                vals[row[1]].append((row[4], row[5], row[6]))
    return names, vals


def verify_dictionary() -> None:
    """Assert every semantic assumption against the 2020-2024 dictionary."""
    names, vals = load_dictionary()

    def need(var: str, label_contains: str = "") -> None:
        assert var in names, f"{var} missing from dictionary"
        if label_contains:
            assert label_contains.lower() in names[var].lower(), (
                f"{var} label unexpected: {names[var]!r}")

    def code(var: str, value: str, label_contains: str) -> str:
        matches = [lab for lo, hi, lab in vals[var] if lo == value]
        assert matches, f"{var}={value} not in dictionary"
        assert any(label_contains.lower() in m.lower() for m in matches), (
            f"{var}={value} label unexpected: {matches!r}")
        return matches[0]

    checks: list[str] = []

    for v in ["SERIALNO", "SPORDER", "AGEP", "SEX", "MSP", "SCHL", "PINCP",
              "ADJINC", "RAC1P", "HISP", "RELSHIPP", "PWGTP", "PWGTP1", "PWGTP80"]:
        need(v)
        checks.append(f"- `{v}`: {names[v]}")

    # State variable: this vintage uses STATE (the brief said ST — renamed).
    assert "STATE" in names and "ST" not in names, (
        f"state var: STATE in dict={'STATE' in names}, ST in dict={'ST' in names}")
    checks.append(f"- `STATE`: {names['STATE']} (NOTE: renamed from `ST` in older vintages)")

    # PUMA: single column, 2020 Census definition; no PUMA10/PUMA20 pair.
    need("PUMA", "2020 Census definition")
    assert "PUMA10" not in names and "PUMA20" not in names, (
        "dictionary has PUMA10/PUMA20 — dual-vintage handling would be required")
    checks.append(f"- `PUMA`: {names['PUMA']} — single column; no PUMA10/PUMA20 in this file")

    # Group quarters: identified on the person file by RELSHIPP 37/38.
    checks.append("- `RELSHIPP=37`: " + code("RELSHIPP", "37", "Institutionalized group quarters"))
    checks.append("- `RELSHIPP=38`: " + code("RELSHIPP", "38", "Noninstitutionalized group quarters"))

    # MSP semantics (the MAR trap does not apply: MSP has b for under-15).
    checks.append("- `MSP=b`: " + code("MSP", "b", "less than 15"))
    checks.append("- `MSP=6`: " + code("MSP", "6", "Never married"))
    for v, lab in [("1", "spouse present"), ("2", "spouse absent"), ("3", "Widowed"),
                   ("4", "Divorced"), ("5", "Separated")]:
        code("MSP", v, lab)

    # SCHL cutpoints for edu4.
    checks.append("- `SCHL=15`: " + code("SCHL", "15", "12th grade - no diploma"))
    checks.append("- `SCHL=16`: " + code("SCHL", "16", "Regular high school diploma"))
    checks.append("- `SCHL=18`: " + code("SCHL", "18", "less than 1 year"))
    checks.append("- `SCHL=20`: " + code("SCHL", "20", "Associate"))
    checks.append("- `SCHL=21`: " + code("SCHL", "21", "Bachelor"))
    checks.append("- `SCHL=22`: " + code("SCHL", "22", "Master"))
    checks.append("- `SCHL=24`: " + code("SCHL", "24", "Doctorate"))

    # RAC1P / HISP for race8.
    checks.append("- `RAC1P=1`: " + code("RAC1P", "1", "White alone"))
    checks.append("- `RAC1P=2`: " + code("RAC1P", "2", "Black or African American alone"))
    code("RAC1P", "3", "American Indian alone")
    code("RAC1P", "5", "American Indian")  # AIAN tribes specified/not specified
    checks.append("- `RAC1P=6`: " + code("RAC1P", "6", "Asian alone"))
    code("RAC1P", "7", "Pacific Islander")
    code("RAC1P", "8", "Some other Race alone")
    checks.append("- `RAC1P=9`: " + code("RAC1P", "9", "Two or More Races"))
    checks.append("- `HISP=01`: " + code("HISP", "01", "Not Spanish"))

    # SEX codes.
    checks.append("- `SEX=1`: " + code("SEX", "1", "Male"))
    checks.append("- `SEX=2`: " + code("SEX", "2", "Female"))

    # ADJINC per-year factors, recorded for traceability.
    adj = [f"{lo} ({lab})" for lo, hi, lab in vals["ADJINC"]]
    checks.append("- `ADJINC` factors: " + "; ".join(adj))

    doc = (
        "# PUMS 2020-2024 data dictionary verification\n\n"
        f"Source: {DICT_URL}\n\n"
        "Every variable the pipeline relies on, verified programmatically against the\n"
        "dictionary (pums.py verify). Assertions fail the run if any semantic drifts.\n\n"
        + "\n".join(checks) + "\n"
    )
    (RESULTS / "pums_dictionary_check.md").write_text(doc)
    print(f"dictionary verified: {len(checks)} checks OK -> results/pums_dictionary_check.md")


def keep_pumas(con: duckdb.DuckDBPyConnection) -> None:
    """Temp table of (st, puma) that allocate to any of the ten target CBSAs."""
    metros = (RESULTS / "metros.csv").read_text().splitlines()[1:]
    cbsas = [line.split(",")[1] for line in metros]
    con.execute(
        f"""CREATE OR REPLACE TEMP TABLE keep AS
            SELECT DISTINCT st, puma FROM '{DATA / 'bridge.parquet'}'
            WHERE cbsa IN ({','.join(repr(c) for c in cbsas)}) AND a > 0"""
    )


def extract_state(postal: str, fips: str) -> dict:
    PUMS_DIR.mkdir(parents=True, exist_ok=True)
    out = PUMS_DIR / f"{postal}.parquet"
    if out.exists():
        print(f"[{postal}] parquet exists, skipping")
        return {}
    if disk_free_gb() < MIN_FREE_GB:
        raise RuntimeError(f"only {disk_free_gb():.1f} GB free — refusing to continue")

    t0 = time.time()
    url = f"{PUMS_BASE}/csv_p{postal}.zip"
    zpath = fetch(url)
    zip_bytes = zpath.stat().st_size

    tmp = TMP_DIR / postal
    tmp.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
        assert members, f"no csv inside {zpath.name}"
        zf.extractall(tmp, members=members)
    csv_bytes = sum((tmp / m).stat().st_size for m in members)

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    keep_pumas(con)

    # Header check: all needed columns present, and no PUMA10/PUMA20 sneaking in.
    hdr = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_csv('{tmp}/*.csv', header=true, all_varchar=true)"
    ).fetchall()]
    missing = [c for c in BASE_COLS + REPWTS if c not in hdr]
    assert not missing, f"[{postal}] columns missing from CSV: {missing}"
    assert "PUMA10" not in hdr and "PUMA20" not in hdr, f"[{postal}] dual PUMA columns present"

    rep_sql = ", ".join(f'CAST("{c}" AS INTEGER) AS {c.lower()}' for c in REPWTS)
    con.execute(f"""
        COPY (
            WITH raw AS (
                SELECT * FROM read_csv('{tmp}/*.csv', header=true, all_varchar=true)
            ), typed AS (
                SELECT
                    SERIALNO AS serialno,
                    CAST(SPORDER AS SMALLINT) AS sporder,
                    STATE AS st,
                    PUMA AS puma,
                    CAST(AGEP AS SMALLINT) AS agep,
                    CAST(SEX AS TINYINT) AS sex,
                    TRY_CAST(MSP AS TINYINT) AS msp,
                    TRY_CAST(SCHL AS TINYINT) AS schl,
                    TRY_CAST(PINCP AS INTEGER) AS pincp,
                    CAST(ADJINC AS INTEGER) AS adjinc,
                    CAST(RAC1P AS TINYINT) AS rac1p,
                    CAST(HISP AS TINYINT) AS hisp,
                    CAST(RELSHIPP AS TINYINT) AS relshipp,
                    CAST(PWGTP AS INTEGER) AS pwgtp,
                    {rep_sql}
                FROM raw
            )
            , derived AS (
                SELECT t.*,
                    CAST(t.pincp AS DOUBLE) * t.adjinc / 1e6 AS inc_adj
                FROM typed t
                JOIN keep k ON k.st = t.st AND k.puma = t.puma
            )
            SELECT d.*,
                CASE WHEN d.msp = 6 THEN 'never'
                     WHEN d.msp IN (1, 2) THEN 'married'
                     WHEN d.msp IN (3, 4, 5) THEN 'formerly' END AS marital3,
                CASE WHEN d.schl IS NULL THEN NULL
                     WHEN d.schl <= 15 THEN 'lt_hs'
                     WHEN d.schl <= 17 THEN 'hs'
                     WHEN d.schl <= 20 THEN 'some_college'
                     ELSE 'ba_plus' END AS edu4,
                CASE WHEN d.inc_adj IS NULL THEN NULL
                     WHEN d.inc_adj < 25000 THEN 1
                     WHEN d.inc_adj < 50000 THEN 2
                     WHEN d.inc_adj < 75000 THEN 3
                     WHEN d.inc_adj < 100000 THEN 4
                     WHEN d.inc_adj < 150000 THEN 5
                     WHEN d.inc_adj < 200000 THEN 6
                     ELSE 7 END AS incband7,
                CASE WHEN d.hisp >= 2 THEN 'hispanic'
                     WHEN d.rac1p = 1 THEN 'nh_white'
                     WHEN d.rac1p = 2 THEN 'nh_black'
                     WHEN d.rac1p IN (3, 4, 5) THEN 'nh_aian'
                     WHEN d.rac1p = 6 THEN 'nh_asian'
                     WHEN d.rac1p = 7 THEN 'nh_nhpi'
                     WHEN d.rac1p = 8 THEN 'nh_other'
                     ELSE 'nh_twoplus' END AS race8,
                CASE d.relshipp WHEN 37 THEN 2 WHEN 38 THEN 1 ELSE 0 END AS gq
            FROM derived d
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    rows_total = con.execute(
        f"SELECT count(*) FROM read_csv('{tmp}/*.csv', header=true, all_varchar=true)"
    ).fetchone()[0]
    rows_kept, wt_kept, gq_mismatch = con.execute(f"""
        SELECT count(*), sum(pwgtp),
               sum(CASE WHEN (serialno LIKE '%GQ%') != (relshipp IN (37,38)) THEN 1 ELSE 0 END)
        FROM '{out}'
    """).fetchone()
    assert gq_mismatch == 0, f"[{postal}] SERIALNO GQ prefix disagrees with RELSHIPP for {gq_mismatch} rows"
    assert rows_kept > 0, f"[{postal}] extract kept zero rows"
    con.close()

    shutil.rmtree(tmp)
    evict(url)

    stats = {
        "state": postal, "fips": fips, "rows_total": rows_total, "rows_kept": rows_kept,
        "weighted_kept": int(wt_kept), "zip_mb": round(zip_bytes / 1e6, 1),
        "csv_mb": round(csv_bytes / 1e6, 1),
        "parquet_mb": round(out.stat().st_size / 1e6, 1),
        "seconds": round(time.time() - t0, 1),
        "disk_free_gb_after": round(disk_free_gb(), 1),
    }
    print(f"[{postal}] {rows_total:,} rows -> kept {rows_kept:,} "
          f"(zip {stats['zip_mb']} MB, csv {stats['csv_mb']} MB, "
          f"parquet {stats['parquet_mb']} MB, {stats['seconds']}s, "
          f"free {stats['disk_free_gb_after']} GB)")
    return stats


def extract_all() -> None:
    geo = json.loads((RESULTS / "geography_manifest.json").read_text())
    fips_by_postal = {}
    from bridge import STATE_FIPS_TO_POSTAL
    for f in geo["involved_state_fips"]:
        fips_by_postal[STATE_FIPS_TO_POSTAL[f]] = f
    # Small state first as a smoke test, then the rest largest-first.
    order = ["dc", "ca", "tx", "ny", "pa", "ga", "mi", "nj", "va", "wi", "mn", "md", "ut", "wv"]
    assert set(order) == set(fips_by_postal), (set(order) ^ set(fips_by_postal))
    PUMS_DIR.mkdir(parents=True, exist_ok=True)
    log = json.loads(EXTRACT_LOG.read_text()) if EXTRACT_LOG.exists() else {"states": []}
    for postal in order:
        stats = extract_state(postal, fips_by_postal[postal])
        if stats:
            log["states"] = [s for s in log["states"] if s["state"] != postal] + [stats]
            EXTRACT_LOG.write_text(json.dumps(log, indent=2) + "\n")
    print("ALL STATES DONE")


if __name__ == "__main__":
    if sys.argv[1:] == ["verify"]:
        verify_dictionary()
    elif sys.argv[1:] == ["all"]:
        extract_all()
    elif len(sys.argv) == 3:
        extract_state(sys.argv[1], sys.argv[2])
    else:
        print("usage: pums.py verify | all | <postal> <fips>")
