"""Phase 4 Stage 1: scan every blob reachable from every ref (and, with
``--all-objects``, every blob in the object store) for Pew's metro table.

A blob fails if it carries any of:

  * the table's column-header line (``pew_guard.has_pew_header``);
  * a Pew column: a CSV/TSV/parquet header field naming Pew, or a numeric
    JSON leaf keyed ``pew`` / ``pew_total`` (``pew_guard``);
  * ten or more of Pew's (metro, value) pairs: a metro together with Pew's
    published value for it (the total or any of the four group rates, as a
    percent or as a share), counted three ways --
      - structured (CSV, TSV, parquet): per column, the metros whose row
        carries that metro's Pew value in that column;
      - JSON (and npz): per key path inside a record that names one metro
        (or per array beside an array of metro codes);
      - prose (every other text, and .docx/.pdf text): a metro's name or
        code followed within 60 characters by that metro's Pew value.
    The largest count any one column, key path or text reaches is the
    blob's count. A count of ten or more fails only if it also beats
    chance: Pew's values are shuffled across its metros PERMUTATIONS times
    (seeded) and the same largest count is taken each time; the blob fails
    if its count exceeds every shuffled count. Columns of small counts
    (PUMAs per metro, fit iterations, income buckets) reach ten by
    coincidence with Pew's 1-50 percent range -- files written before the
    table was ever downloaded do -- and the shuffle is what tells a copy of
    Pew's values from that coincidence.

The values are read from the private copy (``pew_guard.PEW_TABLE``) and
never written out: the record names blobs, paths, rules and counts only.

    python -m atlas.pipeline.build.pew_history_scan \
        --out results/phase4/pew_history_scan.json [--all-objects]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
import time
import zipfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from atlas.pipeline.build import pew_guard as G
from atlas.pipeline.fetch import REPO

PAIR_LIMIT = 10          # "ten or more" fails (when above chance)
PERMUTATIONS = 200
SEED = 2026
PROSE_WINDOW = 60        # characters after a metro's name or code
IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "ico", "webp", "woff", "woff2"}
STRUCTURED_EXT = {"csv", "tsv"}
NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)%?(?![\d])")


TARGET = {"repo": REPO}


def git(*args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(TARGET["repo"]), *args], input=data,
                          check=True, capture_output=True).stdout


# ---- Pew's rows (values stay in memory) -------------------------------------

def load_rows(table: Path) -> list[dict]:
    lines = [l for l in table.read_text().splitlines() if not l.startswith("#")]
    rows = []
    for r in csv.DictReader(io.StringIO("\n".join(lines))):
        if r["msa_code"] == "1":
            continue                      # the national row is not a metro
        vals = set()
        for col in ("total", "whites", "blacks", "hisps", "asians"):
            v = (r.get(col) or "").strip()
            if v and v != "-":
                vals.add(Decimal(v))
        name = r["metro_name"]
        head = name.rsplit(",", 1)[0]
        variants = {name}
        for part in re.split(r"[-–/]", head):
            part = part.strip()
            if part.startswith("Urban "):
                part = part[len("Urban "):]
            if len(part) >= 4:
                variants.add(part)
        rows.append({"code": r["msa_code"], "name": name,
                     "variants": variants, "values": frozenset(vals)})
    return rows


def number(token) -> Decimal | None:
    try:
        return Decimal(str(token).strip().rstrip("%"))
    except (InvalidOperation, ValueError):
        return None


def hit(d: Decimal | None, values: frozenset) -> bool:
    """``d`` is one of ``values`` as a percent or as a share."""
    return d is not None and (d in values or (d * 100) in values)


class Detector:
    """Each reader turns a blob into observations -- (location, metro code,
    the numbers found there for that metro) -- once; ``count`` then reads
    them under Pew's true values and under shuffled ones."""

    def __init__(self, rows: list[dict]):
        import random
        self.rows = rows
        self.by_code = {r["code"]: r for r in rows}
        self.by_name = {r["name"]: r for r in rows}
        self.values = {r["code"]: r["values"] for r in rows}
        rng = random.Random(SEED)
        codes = [r["code"] for r in rows]
        self.shuffles = []
        for _ in range(PERMUTATIONS):
            perm = codes[:]
            rng.shuffle(perm)
            self.shuffles.append({c: self.values[p] for c, p in zip(codes, perm)})
        ident: dict[str, list[str]] = defaultdict(list)
        for r in rows:
            ident[r["code"]].append(r["code"])
            for v in r["variants"]:
                ident[v].append(r["code"])
        self.ident = ident
        alts = sorted(ident, key=len, reverse=True)
        pat = "|".join(re.escape(a).replace(r"\ ", r"\s+") for a in alts)
        self.ident_re = re.compile(rf"(?<![\w])({pat})(?![\w])")

    @staticmethod
    def _largest(obs, values) -> tuple[int, str | None]:
        found: dict[str, set[str]] = defaultdict(set)
        for loc, code, nums in obs:
            vals = values[code]
            if any(hit(d, vals) for d in nums):
                found[loc].add(code)
        if not found:
            return 0, None
        loc = max(found, key=lambda k: (len(found[k]), k))
        return len(found[loc]), loc

    def count(self, obs: list) -> dict:
        n, loc = self._largest(obs, self.values)
        rec = {"pairs": n, "where": loc}
        if n >= PAIR_LIMIT:
            chance = sorted(self._largest(obs, sh)[0] for sh in self.shuffles)
            rec["chance"] = {"permutations": PERMUTATIONS,
                             "median": chance[len(chance) // 2],
                             "max": chance[-1]}
            rec["above_chance"] = n > chance[-1]
        return rec

    # -- structured: CSV / TSV / parquet rows (strings)
    def table_obs(self, header: list[str], rows: list[list[str]]) -> list:
        obs = []
        for row in rows:
            code = None
            for cell in row:
                c = cell.strip()
                if c in self.by_code:
                    code = c
                    break
                if c in self.by_name:
                    code = self.by_name[c]["code"]
                    break
            if code is None:
                continue
            for j, cell in enumerate(row):
                c = cell.strip()
                if not c or c == code:
                    continue
                d = number(c)
                if d is not None:
                    col = header[j] if j < len(header) else f"#{j}"
                    obs.append((f"column {col!r}", code, (d,)))
        return obs

    # -- JSON
    def json_obs(self, doc) -> list:
        obs = []

        def metro_of(d: dict, parent_key) -> str | None:
            found = {str(v) for v in d.values()
                     if isinstance(v, (str, int)) and not isinstance(v, bool)
                     and str(v) in self.by_code}
            if parent_key is not None and str(parent_key) in self.by_code:
                found.add(str(parent_key))
            return found.pop() if len(found) == 1 else None

        def leaves(node, rel, code, anchor):
            if isinstance(node, dict):
                m = metro_of(node, None)
                if m is not None and m != code:
                    return          # a nested record for another metro
                for k, v in node.items():
                    leaves(v, f"{rel}/{k}", code, anchor)
            elif isinstance(node, list):
                for v in node:
                    leaves(v, f"{rel}[]", code, anchor)
            elif isinstance(node, (int, float)) and not isinstance(node, bool):
                obs.append((f"key path {anchor}{rel}", code, (number(repr(node)),)))

        def walk(node, path, parent_key):
            if isinstance(node, dict):
                m = metro_of(node, parent_key)
                if m is not None:
                    anchor = re.sub(r"/\d{5}(?=/|$)", "/<metro>", path)
                    for k, v in node.items():
                        leaves(v, f"/{k}", m, anchor)
                for k, v in node.items():          # {code: number} maps
                    if str(k) in self.by_code and isinstance(v, (int, float)) \
                            and not isinstance(v, bool):
                        obs.append((f"key path {path}/<metro>", str(k), (number(repr(v)),)))
                lists = {k: v for k, v in node.items() if isinstance(v, list)}
                for k, codes in lists.items():     # arrays beside an array of codes
                    cs = [str(c) for c in codes]
                    if sum(c in self.by_code for c in cs) < PAIR_LIMIT:
                        continue
                    for k2, vals in lists.items():
                        if k2 == k or len(vals) != len(cs):
                            continue
                        for c, v in zip(cs, vals):
                            if c in self.by_code and isinstance(v, (int, float, str)) \
                                    and not isinstance(v, bool):
                                obs.append((f"key path {path}/{k2}[aligned to {k}]", c,
                                            (number(v),)))
                for k, v in node.items():
                    walk(v, f"{path}/{k}", k)
            elif isinstance(node, list):
                for v in node:
                    walk(v, f"{path}[]", None)

        walk(doc, "", None)
        return obs

    # -- npz: arrays aligned with an array of metro codes
    def npz_obs(self, data: bytes) -> list:
        import numpy as np
        obs = []
        z = np.load(io.BytesIO(data), allow_pickle=False)
        arrays = {k: z[k] for k in z.files}
        for k, a in arrays.items():
            if a.dtype.kind not in "US" or a.ndim != 1:
                continue
            cs = [str(x) for x in a]
            if sum(c in self.by_code for c in cs) < PAIR_LIMIT:
                continue
            for k2, b in arrays.items():
                if k2 == k or b.ndim < 1 or b.shape[0] != len(cs) or b.dtype.kind not in "fiu":
                    continue
                flat = b.reshape(len(cs), -1)
                for i, c in enumerate(cs):
                    if c in self.by_code:
                        obs.append((f"array {k2}[aligned to {k}]", c,
                                    tuple(number(repr(float(x))) for x in flat[i])))
        return obs

    # -- prose: a metro's name or code, then the numbers in the next 60 chars
    def prose_obs(self, text: str) -> list:
        obs = []
        spans = list(self.ident_re.finditer(text))
        for i, m in enumerate(spans):
            end = m.end()
            stop = min(end + PROSE_WINDOW,
                       spans[i + 1].start() if i + 1 < len(spans) else len(text))
            nums = tuple(number(t.group(1)) for t in NUM.finditer(text[end:stop]))
            if not nums:
                continue
            key = re.sub(r"\s+", " ", m.group(1))
            for code in self.ident.get(key, []):
                obs.append(("prose", code, nums))
        return obs


# ---- reading a blob ----------------------------------------------------------

def ext_of(path: str) -> str:
    return path.rsplit(".", 1)[-1].lower() if "." in Path(path).name else ""


def text_of(ext: str, data: bytes) -> str:
    if ext == "docx":
        xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8", "replace")
        return re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", xml))
    if ext == "pdf":
        p = subprocess.run(["pdftotext", "-layout", "-", "-"], input=data, capture_output=True)
        return p.stdout.decode("utf-8", "replace")
    return data.decode("utf-8", "replace")


def inspect(det: Detector, path: str, data: bytes) -> dict:
    ext = ext_of(path)
    rec: dict = {}
    if ext in IMAGE_EXT:
        return rec
    if ext == "npz":
        rec["pairs"] = det.count(det.npz_obs(data))
        return rec
    if ext == "parquet":
        import pandas as pd
        df = pd.read_parquet(io.BytesIO(data))
        rec.update(G.tracked_file_findings(path, data))
        rows = df.astype(str).values.tolist()
        rec["pairs"] = det.count(det.table_obs([str(c) for c in df.columns], rows))
        return rec
    if ext in {"docx", "pdf"}:
        text = text_of(ext, data)
        if G.has_pew_header(text):
            rec["table_header"] = True
        rec["pairs"] = det.count(det.prose_obs(text))
        return rec
    if b"\0" in data[:8192]:
        return rec
    rec.update(G.tracked_file_findings(path, data))
    text = data.decode("utf-8", "replace")
    if ext in STRUCTURED_EXT:
        lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#")]
        if lines:
            delim = "\t" if ext == "tsv" else ","
            parsed = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delim))
            rec["pairs"] = det.count(det.table_obs(parsed[0], parsed[1:]))
        return rec
    if ext == "json":
        try:
            rec["pairs"] = det.count(det.json_obs(json.loads(text)))
            return rec
        except ValueError:
            pass
    rec["pairs"] = det.count(det.prose_obs(text))
    return rec


def failing(rec: dict) -> list[str]:
    why = []
    if rec.get("table_header"):
        why.append("table header")
    if rec.get("pew_columns") or rec.get("pew_value_keys"):
        why.append("Pew column")
    pairs = rec.get("pairs") or {}
    if pairs.get("pairs", 0) >= PAIR_LIMIT and pairs.get("above_chance"):
        why.append(f">= {PAIR_LIMIT} (metro, value) pairs, above chance")
    return why


def reachable_blobs() -> dict[str, set[str]]:
    """blob -> every path it appears under, over every commit of every ref."""
    paths: dict[str, set[str]] = defaultdict(set)
    for c in git("rev-list", "--all").decode().split():
        for line in git("ls-tree", "-r", "--full-tree", c).decode().splitlines():
            meta, path = line.split("\t", 1)
            _, typ, sha = meta.split()
            if typ == "blob":
                paths[sha].add(path)
    # blobs a ref points at directly (none expected) or tag trees
    for line in git("rev-list", "--objects", "--all").decode().splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[0] not in paths:
            kind = git("cat-file", "-t", parts[0]).decode().strip()
            if kind == "blob":
                paths[parts[0]].add(parts[1])
    return paths


def store_blobs() -> list[str]:
    out = git("cat-file", "--batch-all-objects", "--batch-check").decode().splitlines()
    return [l.split()[0] for l in out if l.split()[1] == "blob"]


def scan(table: Path, all_objects: bool) -> dict:
    t0 = time.time()
    det = Detector(load_rows(table))
    refs = git("for-each-ref", "--format=%(refname) %(objectname)").decode().split("\n")
    refs = [r for r in refs if r]
    blobs = reachable_blobs()
    results = {}
    for sha, paths in sorted(blobs.items()):
        data = git("cat-file", "blob", sha)
        # a blob seen under paths of different kinds is read as each kind
        per_kind = {}
        for p in sorted(paths):
            per_kind.setdefault(ext_of(p), p)
        recs = [inspect(det, p, data) for p in per_kind.values()]
        rec = max(recs, key=lambda r: (len(failing(r)), (r.get("pairs") or {}).get("pairs", 0)),
                  default={})
        results[sha] = {"paths": sorted(paths), **rec}
    extra = {}
    if all_objects:
        for sha in store_blobs():
            if sha in results:
                continue
            data = git("cat-file", "blob", sha)
            kind = "json" if data.lstrip()[:1] in (b"{", b"[") else "txt"
            if data[:4] == b"PK\x03\x04":
                kind = "zip"
            if kind == "zip":
                continue
            extra[sha] = {"paths": [], "read_as": kind, **inspect(det, f"x.{kind}", data)}
    viol = [{"blob": s, "paths": r["paths"], "why": failing(r),
             **{k: r[k] for k in ("table_header", "pew_columns", "pew_value_keys", "pairs") if k in r}}
            for s, r in {**results, **extra}.items() if failing(r)]
    below = [{"blob": s, "paths": r["paths"], **r["pairs"]}
             for s, r in {**results, **extra}.items()
             if not failing(r) and (r.get("pairs") or {}).get("pairs", 0) > 0]
    return {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "head": git("rev-parse", "HEAD").decode().strip(),
        "refs": refs,
        "criteria": {
            "table_header": "a line whose SHA-256 is the table's column-header line's",
            "pew_column": "a CSV/TSV/parquet header field naming Pew, or a numeric JSON leaf keyed pew / pew_total",
            "pairs": f">= {PAIR_LIMIT} metros carrying Pew's own value for that metro "
                     "(total or a group rate, as a percent or a share) in one column, one JSON "
                     f"key path, one array, or within {PROSE_WINDOW} characters after the metro's "
                     "name or code in text, AND more than the same count reaches in every one of "
                     f"{PERMUTATIONS} shuffles of Pew's values across its metros (seed {SEED})",
            "metros_in_table": len(det.rows),
        },
        "blobs_reachable_scanned": len(results),
        "store_blobs_unreachable_scanned": len(extra) if all_objects else None,
        "violations": viol,
        "below_limit": sorted(below, key=lambda b: -b["pairs"]),
        "verdict": "clean" if not viol else "FAIL",
        "seconds": round(time.time() - t0, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--table", type=Path, default=None,
                    help="the Pew table (default: the private copy)")
    ap.add_argument("--all-objects", action="store_true",
                    help="also scan unreachable blobs left in the object store")
    ap.add_argument("--repo", type=Path, default=REPO)
    a = ap.parse_args()
    TARGET["repo"] = a.repo
    rec = scan(a.table or G.require_pew_table(), a.all_objects)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{rec['verdict']}: {len(rec['violations'])} violations over "
          f"{rec['blobs_reachable_scanned']} reachable blobs; "
          f"{len(rec['below_limit'])} below the limit ({rec['seconds']} s)")


if __name__ == "__main__":
    main()
