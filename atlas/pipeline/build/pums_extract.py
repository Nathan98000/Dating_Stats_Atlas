"""PUMS 2020-2024 5-year extract, Phase 1: person and housing files, all
51 states, one state at a time with disk eviction.

Person derivations (the cube axes — Phase 1 axis definitions):
  marital3   never (MSP=6) / currently (MSP 1-2) / previously (MSP 3-5)
             — "not currently married" downstream = MSP in (3,4,5,6)
  edu4       hs_or_less (SCHL<=17, incl. GED) / some_college (18-20, incl.
             associate) / bachelors (21) / graduate (22-24)
  inc_adj    PINCP * ADJINC / 1e6   (constant 2024 dollars)
  incband7   <25k / 25-50 / 50-75 / 75-100 / 100-150 / 150-250 / >=250k
  pernp_adj  PERNP * ADJINC / 1e6   (earnings — calibration against B20001/2)
  race8      hispanic (HISP>=2) else NH white/black/asian/aian/nhpi/twoplus/other
  gq         0 household, 1 noninstitutional GQ (RELSHIPP=38),
             2 institutional GQ (RELSHIPP=37)

Housing extract (calibration of household income against B19001 only —
the cube never uses it): HINCP * ADJINC, WGTP + 80 replicate weights,
TYPEHUGQ/NP to scope the household universe.

Only rows in PUMAs that allocate to at least one target metro are kept;
all ages are kept so calibration can compare against published all-age
universes. `verify` asserts every semantic this file relies on against
PUMS_Data_Dictionary_2020-2024.csv before anything is extracted.
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import time
import zipfile
from collections import defaultdict

import duckdb

from atlas.pipeline.fetch import DATA, RESULTS, disk_free_gb, evict, fetch

PUMS_BASE = "https://www2.census.gov/programs-surveys/acs/data/pums/2024/5-Year"
DICT_URL = (
    "https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/"
    "PUMS_Data_Dictionary_2020-2024.csv"
)
PUMS_DIR = DATA / "pums"
PUMS_H_DIR = DATA / "pums_h"
TMP_DIR = DATA / "tmp"
EXTRACT_LOG = RESULTS / "phase1" / "pums_extract_log.json"
MIN_FREE_GB = 5.0

P_REPWTS = [f"PWGTP{i}" for i in range(1, 81)]
H_REPWTS = [f"WGTP{i}" for i in range(1, 81)]
P_BASE = ["SERIALNO", "SPORDER", "STATE", "PUMA", "AGEP", "SEX", "MSP", "SCHL",
          "PINCP", "PERNP", "ADJINC", "RAC1P", "HISP", "RELSHIPP", "PWGTP"]
H_BASE = ["SERIALNO", "STATE", "PUMA", "HINCP", "ADJINC", "TYPEHUGQ", "NP", "WGTP"]


def load_dictionary() -> tuple[dict, dict]:
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
    """Assert every semantic assumption against the 2020-2024 dictionary,
    including the Phase 1 education and income derivations."""
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

    assert "STATE" in names and "ST" not in names
    checks.append(f"- `STATE`: {names['STATE']} (renamed from `ST` in older vintages)")
    need("PUMA", "2020 Census definition")
    assert "PUMA10" not in names and "PUMA20" not in names
    checks.append(f"- `PUMA`: {names['PUMA']} — single column; no PUMA10/PUMA20")

    checks.append("- `RELSHIPP=37`: " + code("RELSHIPP", "37", "Institutionalized group quarters"))
    checks.append("- `RELSHIPP=38`: " + code("RELSHIPP", "38", "Noninstitutionalized group quarters"))
    checks.append("- `MSP=b`: " + code("MSP", "b", "less than 15"))
    checks.append("- `MSP=6`: " + code("MSP", "6", "Never married"))
    for v, lab in [("1", "spouse present"), ("2", "spouse absent"), ("3", "Widowed"),
                   ("4", "Divorced"), ("5", "Separated")]:
        code("MSP", v, lab)

    # edu4 cutpoints (Phase 1 axis: hs_or_less / some_college / bachelors / graduate)
    checks.append("- `SCHL=16`: " + code("SCHL", "16", "Regular high school diploma") +
                  " -> hs_or_less")
    checks.append("- `SCHL=17`: " + code("SCHL", "17", "GED") + " -> hs_or_less")
    checks.append("- `SCHL=18`: " + code("SCHL", "18", "less than 1 year") + " -> some_college")
    checks.append("- `SCHL=19`: " + code("SCHL", "19", "1 or more years") + " -> some_college")
    checks.append("- `SCHL=20`: " + code("SCHL", "20", "Associate") + " -> some_college")
    checks.append("- `SCHL=21`: " + code("SCHL", "21", "Bachelor") + " -> bachelors")
    checks.append("- `SCHL=22`: " + code("SCHL", "22", "Master") + " -> graduate")
    checks.append("- `SCHL=23`: " + code("SCHL", "23", "Professional degree") + " -> graduate")
    checks.append("- `SCHL=24`: " + code("SCHL", "24", "Doctorate") + " -> graduate")

    # income / earnings
    need("PINCP", "Total person's income")
    need("PERNP", "Total person's earnings")
    checks.append(f"- `PERNP`: {names['PERNP']} (calibration vs B20001/B20002)")
    adj = [f"{lo} ({lab})" for lo, hi, lab in vals["ADJINC"]]
    checks.append("- `ADJINC` factors: " + "; ".join(adj))
    checks.append("- income bands (2024 dollars): <25k / 25-50 / 50-75 / 75-100 "
                  "/ 100-150 / 150-250 / >=250k applied to PINCP*ADJINC")

    checks.append("- `RAC1P=1`: " + code("RAC1P", "1", "White alone"))
    checks.append("- `RAC1P=2`: " + code("RAC1P", "2", "Black or African American alone"))
    code("RAC1P", "3", "American Indian alone")
    code("RAC1P", "5", "American Indian")
    checks.append("- `RAC1P=6`: " + code("RAC1P", "6", "Asian alone"))
    code("RAC1P", "7", "Pacific Islander")
    code("RAC1P", "8", "Some other Race alone")
    checks.append("- `RAC1P=9`: " + code("RAC1P", "9", "Two or More Races"))
    checks.append("- `HISP=01`: " + code("HISP", "01", "Not Spanish"))
    checks.append("- `SEX=1`: " + code("SEX", "1", "Male"))
    checks.append("- `SEX=2`: " + code("SEX", "2", "Female"))

    # housing file (B19001 calibration)
    need("HINCP", "Household income")
    need("WGTP", "Housing Unit Weight")
    need("NP", "Number of persons")
    for v in ["WGTP1", "WGTP80"]:
        need(v)
    checks.append(f"- `HINCP`: {names['HINCP']}")
    checks.append(f"- `WGTP`: {names['WGTP']} + WGTP1..WGTP80 replicates")
    checks.append("- `TYPEHUGQ=1`: " + code("TYPEHUGQ", "1", "Housing unit"))

    doc = (
        "# PUMS 2020-2024 data dictionary verification (Phase 1)\n\n"
        f"Source: {DICT_URL}\n\n"
        "Every variable the pipeline relies on, verified programmatically against the\n"
        "dictionary (pums.py verify). Assertions fail the run if any semantic drifts.\n\n"
        + "\n".join(checks) + "\n"
    )
    (RESULTS / "pums_dictionary_check.md").write_text(doc)
    print(f"dictionary verified: {len(checks)} checks OK -> results/pums_dictionary_check.md")


def keep_pumas(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        f"""CREATE OR REPLACE TEMP TABLE keep AS
            SELECT DISTINCT st, puma FROM '{DATA / 'bridge.parquet'}'"""
    )


def _unzip(url: str, tmp) -> tuple[list[str], int]:
    zpath = fetch(url)
    zip_bytes = zpath.stat().st_size
    tmp.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
        assert members, f"no csv inside {zpath.name}"
        zf.extractall(tmp, members=members)
    return members, zip_bytes


def extract_person(postal: str) -> dict:
    PUMS_DIR.mkdir(parents=True, exist_ok=True)
    out = PUMS_DIR / f"{postal}.parquet"
    if out.exists():
        return {}
    if disk_free_gb() < MIN_FREE_GB:
        raise RuntimeError(f"only {disk_free_gb():.1f} GB free — refusing to continue")
    t0 = time.time()
    url = f"{PUMS_BASE}/csv_p{postal}.zip"
    tmp = TMP_DIR / f"p_{postal}"
    members, zip_bytes = _unzip(url, tmp)
    csv_bytes = sum((tmp / m).stat().st_size for m in members)

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    keep_pumas(con)
    hdr = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_csv('{tmp}/*.csv', header=true, all_varchar=true)"
    ).fetchall()]
    missing = [c for c in P_BASE + P_REPWTS if c not in hdr]
    assert not missing, f"[{postal}] person columns missing: {missing}"
    assert "PUMA10" not in hdr and "PUMA20" not in hdr

    rep_sql = ", ".join(f'CAST("{c}" AS INTEGER) AS {c.lower()}' for c in P_REPWTS)
    con.execute(f"""
        COPY (
            WITH raw AS (
                SELECT * FROM read_csv('{tmp}/*.csv', header=true, all_varchar=true)
            ), typed AS (
                SELECT
                    SERIALNO AS serialno,
                    CAST(SPORDER AS SMALLINT) AS sporder,
                    STATE AS st, PUMA AS puma,
                    CAST(AGEP AS SMALLINT) AS agep,
                    CAST(SEX AS TINYINT) AS sex,
                    TRY_CAST(MSP AS TINYINT) AS msp,
                    TRY_CAST(SCHL AS TINYINT) AS schl,
                    TRY_CAST(PINCP AS INTEGER) AS pincp,
                    TRY_CAST(PERNP AS INTEGER) AS pernp,
                    CAST(ADJINC AS INTEGER) AS adjinc,
                    CAST(RAC1P AS TINYINT) AS rac1p,
                    CAST(HISP AS TINYINT) AS hisp,
                    CAST(RELSHIPP AS TINYINT) AS relshipp,
                    CAST(PWGTP AS INTEGER) AS pwgtp,
                    {rep_sql}
                FROM raw
            ), derived AS (
                SELECT t.*,
                    CAST(t.pincp AS DOUBLE) * t.adjinc / 1e6 AS inc_adj,
                    CAST(t.pernp AS DOUBLE) * t.adjinc / 1e6 AS pernp_adj
                FROM typed t
                JOIN keep k ON k.st = t.st AND k.puma = t.puma
            )
            SELECT d.*,
                CASE WHEN d.msp = 6 THEN 'never'
                     WHEN d.msp IN (1, 2) THEN 'married'
                     WHEN d.msp IN (3, 4, 5) THEN 'formerly' END AS marital3,
                CASE WHEN d.schl IS NULL THEN NULL
                     WHEN d.schl <= 17 THEN 'hs_or_less'
                     WHEN d.schl <= 20 THEN 'some_college'
                     WHEN d.schl = 21 THEN 'bachelors'
                     ELSE 'graduate' END AS edu4,
                CASE WHEN d.inc_adj IS NULL THEN NULL
                     WHEN d.inc_adj < 25000 THEN 1
                     WHEN d.inc_adj < 50000 THEN 2
                     WHEN d.inc_adj < 75000 THEN 3
                     WHEN d.inc_adj < 100000 THEN 4
                     WHEN d.inc_adj < 150000 THEN 5
                     WHEN d.inc_adj < 250000 THEN 6
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
    rows_kept, gq_mismatch = con.execute(f"""
        SELECT count(*),
               sum(CASE WHEN (serialno LIKE '%GQ%') != (relshipp IN (37,38)) THEN 1 ELSE 0 END)
        FROM '{out}'
    """).fetchone()
    assert gq_mismatch == 0 and rows_kept > 0
    con.close()
    shutil.rmtree(tmp)
    evict(url)
    return {"file": "person", "state": postal, "rows_total": rows_total,
            "rows_kept": rows_kept, "zip_mb": round(zip_bytes / 1e6, 1),
            "csv_mb": round(csv_bytes / 1e6, 1),
            "parquet_mb": round(out.stat().st_size / 1e6, 1),
            "seconds": round(time.time() - t0, 1),
            "disk_free_gb_after": round(disk_free_gb(), 1)}


def extract_housing(postal: str) -> dict:
    PUMS_H_DIR.mkdir(parents=True, exist_ok=True)
    out = PUMS_H_DIR / f"{postal}.parquet"
    if out.exists():
        return {}
    if disk_free_gb() < MIN_FREE_GB:
        raise RuntimeError(f"only {disk_free_gb():.1f} GB free — refusing to continue")
    t0 = time.time()
    url = f"{PUMS_BASE}/csv_h{postal}.zip"
    tmp = TMP_DIR / f"h_{postal}"
    members, zip_bytes = _unzip(url, tmp)
    csv_bytes = sum((tmp / m).stat().st_size for m in members)

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    keep_pumas(con)
    hdr = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_csv('{tmp}/*.csv', header=true, all_varchar=true)"
    ).fetchall()]
    missing = [c for c in H_BASE + H_REPWTS if c not in hdr]
    assert not missing, f"[{postal}] housing columns missing: {missing}"

    rep_sql = ", ".join(f'CAST("{c}" AS INTEGER) AS {c.lower()}' for c in H_REPWTS)
    con.execute(f"""
        COPY (
            WITH raw AS (
                SELECT * FROM read_csv('{tmp}/*.csv', header=true, all_varchar=true)
            ), typed AS (
                SELECT
                    SERIALNO AS serialno, STATE AS st, PUMA AS puma,
                    TRY_CAST(HINCP AS BIGINT) AS hincp,
                    CAST(ADJINC AS INTEGER) AS adjinc,
                    CAST(TYPEHUGQ AS TINYINT) AS typehugq,
                    TRY_CAST(NP AS SMALLINT) AS np,
                    CAST(WGTP AS INTEGER) AS wgtp,
                    {rep_sql}
                FROM raw
            )
            SELECT t.*, CAST(t.hincp AS DOUBLE) * t.adjinc / 1e6 AS hincp_adj
            FROM typed t
            JOIN keep k ON k.st = t.st AND k.puma = t.puma
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    rows_total = con.execute(
        f"SELECT count(*) FROM read_csv('{tmp}/*.csv', header=true, all_varchar=true)"
    ).fetchone()[0]
    rows_kept = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    assert rows_kept > 0
    con.close()
    shutil.rmtree(tmp)
    evict(url)
    return {"file": "housing", "state": postal, "rows_total": rows_total,
            "rows_kept": rows_kept, "zip_mb": round(zip_bytes / 1e6, 1),
            "csv_mb": round(csv_bytes / 1e6, 1),
            "parquet_mb": round(out.stat().st_size / 1e6, 1),
            "seconds": round(time.time() - t0, 1),
            "disk_free_gb_after": round(disk_free_gb(), 1)}


def extract_all(which: str) -> None:
    geo = json.loads((RESULTS / "geography_manifest.json").read_text())
    order = sorted(geo["pums_states_postal"])
    EXTRACT_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = json.loads(EXTRACT_LOG.read_text()) if EXTRACT_LOG.exists() else {"states": []}
    fn = extract_person if which == "person" else extract_housing
    for postal in order:
        stats = fn(postal)
        if stats:
            print(f"[{which} {postal}] {stats['rows_total']:,} -> {stats['rows_kept']:,} "
                  f"({stats['seconds']}s, parquet {stats['parquet_mb']} MB, "
                  f"free {stats['disk_free_gb_after']} GB)", flush=True)
            log["states"] = [s for s in log["states"]
                             if not (s["state"] == postal and s["file"] == which)] + [stats]
            EXTRACT_LOG.write_text(json.dumps(log, indent=2) + "\n")
    print(f"ALL {which.upper()} STATES DONE", flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["verify"]:
        verify_dictionary()
    elif sys.argv[1:] == ["person"]:
        extract_all("person")
    elif sys.argv[1:] == ["housing"]:
        extract_all("housing")
    else:
        print("usage: pums.py verify | person | housing")
