"""Phase 4 Stage 1: Pew's metro table is private.

Pew Research Center's newlywed intermarriage table (2011-2015, by metro)
was a build-time validation reference from Phase 2 to Phase 3d. Nathan's
decision (ADR 0012): it is used at build time only, never published and
never compared in public. Phase 4 took it, and every per-metro value
copied from it, out of the repository and its history; the only copy
lives in a gitignored private folder on the build machine.

This module is the one place that names that folder, and it holds the
checks that keep Pew's values out of tracked files:

  * the table's column-header line is recognised by its SHA-256, so the
    line itself is never written into a tracked file (a tracked file
    carrying it would fail the very check that looks for it);
  * a "Pew column" is a CSV/TSV/parquet header field, or a numeric JSON
    leaf keyed ``pew`` / ``pew_total``, i.e. the two names Pew's
    per-metro value was stored under before Phase 4.

The per-metro (metro, value) pair detection needs the values themselves,
so it lives in ``pew_history_scan`` and reads the private copy.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

from atlas.pipeline.fetch import DATA

PEW_PRIVATE_DIR = DATA / "private" / "pew"
PEW_TABLE = PEW_PRIVATE_DIR / "pew_intermarriage_2015.csv"

# SHA-256 of the table's column-header line (msa code, metro name, the
# total and four group columns), stripped of its line ending
PEW_HEADER_SHA256 = "f8832fe106f4f3095058666a2bb7330a4a9647b669927297d70e1b8b705742b2"

# the keys Pew's per-metro value was stored under in tracked results
PEW_VALUE_KEYS = frozenset({"pew", "pew_total"})


def require_pew_table() -> Path:
    """The private table's path, or a clear error where it is absent (a
    fresh clone has no copy; only the build machine does)."""
    if not PEW_TABLE.exists():
        raise FileNotFoundError(
            f"{PEW_TABLE} is absent. Pew's table is private (ADR 0012): it lives "
            "only in the gitignored atlas/data/private/pew/ on the build machine.")
    return PEW_TABLE


def has_pew_header(text: str) -> bool:
    """True if any line of ``text`` is the table's column-header line."""
    for line in text.splitlines():
        s = line.strip().encode("utf-8", "replace")
        if len(s) < 200 and hashlib.sha256(s).hexdigest() == PEW_HEADER_SHA256:
            return True
    return False


def csv_pew_columns(text: str) -> list[str]:
    """Header fields naming Pew in a CSV/TSV (the first line that is not a
    ``#`` comment is the header)."""
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        delim = "\t" if line.count("\t") > line.count(",") else ","
        fields = next(csv.reader(io.StringIO(line), delimiter=delim))
        return [f for f in fields if "pew" in f.lower()]
    return []


def json_pew_value_paths(node, path: str = "") -> list[str]:
    """Paths of numeric JSON leaves keyed ``pew`` or ``pew_total``."""
    out: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}/{k}"
            if (str(k).lower() in PEW_VALUE_KEYS and isinstance(v, (int, float))
                    and not isinstance(v, bool)):
                out.append(p)
            out.extend(json_pew_value_paths(v, p))
    elif isinstance(node, list):
        for v in node:
            out.extend(json_pew_value_paths(v, f"{path}[]"))
    return sorted(set(out))


def tracked_file_findings(path: str, data: bytes) -> dict:
    """What a tracked file carries of Pew's table: its header line, a Pew
    column, or a numeric value keyed as Pew's. Binary files other than
    parquet are not read."""
    out: dict = {}
    low = path.lower()
    if low.endswith(".parquet"):
        import pyarrow.parquet as pq
        cols = pq.read_schema(io.BytesIO(data)).names
        pew_cols = [c for c in cols if "pew" in c.lower()]
        if pew_cols:
            out["pew_columns"] = pew_cols
        return out
    if b"\0" in data[:8192]:
        return out
    text = data.decode("utf-8", "replace")
    if has_pew_header(text):
        out["table_header"] = True
    if low.endswith((".csv", ".tsv")):
        cols = csv_pew_columns(text)
        if cols:
            out["pew_columns"] = cols
    if low.endswith(".json"):
        try:
            paths = json_pew_value_paths(json.loads(text))
        except ValueError:
            paths = []
        if paths:
            out["pew_value_keys"] = paths
    return out
