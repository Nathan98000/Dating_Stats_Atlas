"""Phase 4 Stage 1: the one-time history rewrite that took Pew's metro
table out of the repository (Nathan's decision; ADR 0012).

Three transforms, applied by ``git filter-repo`` to every version of every
file in every commit (a ``--file-info-callback``, so each is path-aware):

  1. ``results/reference/pew_intermarriage_2015.csv`` is removed from
     every commit;
  2. every ``pew_lomo_*.csv`` loses its Pew columns (``pew_total``); our
     own columns -- the held-out predictions and their corrected forms --
     stay, byte for byte;
  3. the per-metro Pew figures quoted in reports are redacted:
     - JSON: the ``pew`` value inside ``composition_check.jackson_ms``;
     - Markdown: each quoted figure becomes ``[redacted]`` (PHASE3.md,
       PHASE3B.md and ADR 0009; the patterns below name the metros and
       the sentence around each figure, never a value).

Pew's national figure and the summary comparisons (medians, paired
counts, correlations) are not per-metro values and stay on the record.

Run with a Python that has ``git_filter_repo`` (it is not a project
dependency; Phase 4 used a throwaway virtualenv):

    python atlas/pipeline/build/pew_history_rewrite.py run --log <json>
    python atlas/pipeline/build/pew_history_rewrite.py verify \
        --backup <mirror.git> --log <json> --out results/phase4/pew_history_rewrite.json

``verify`` proves the rewrite did these transforms and nothing else: every
old commit maps to a new one with the same author, dates and message (up to
the rewritten hashes), the same paths (less the table) and the same blobs,
except that each transformed file's new content equals the transform of its
old content, re-applied here from the backup.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TABLE = "atlas/results/reference/pew_intermarriage_2015.csv"
LOMO = re.compile(r"(?:^|/)pew_lomo_[^/]*\.csv$")
JACKSON = re.compile(rb'("jackson_ms": \{\n)[ \t]*"pew": -?[0-9][0-9.eE+-]*,\n')

# per-metro Pew figures quoted in reports: (label, pattern, replacement)
S = r"\s+"
REDACT = [
    ("Santa Maria-Santa Barbara, PHASE3.md",
     rf"(\(Pew{S})\d+%(?=,{S}predicted)", r"\1[redacted]"),
    ("Palm Bay, El Paso, Ogden, Fayetteville NC, Miami, PHASE3.md",
     rf"((?:Palm{S}Bay|El{S}Paso|Ogden|Fayetteville{S}NC|Miami){S}\()\d+({S}→)",
     r"\1[redacted]\2"),
    ("Honolulu, PHASE3.md", rf"(Honolulu{S}\(Pew{S})\d+%", r"\1[redacted]"),
    ("Jackson MS, PHASE3.md", rf"(Jackson,{S}Mississippi:{S}Pew{S})\d+%", r"\1[redacted]"),
    ("Jackson MS restated, PHASE3.md and ADR 0009",
     rf"(so{S}no{S}model{S}built{S}on{S}(?:them|2020–24{S}data){S}reaches{S})\d+%",
     r"\1[redacted]"),
    ("Jackson MS, PHASE3B.md", rf"(Mississippi{S}reads{S}Pew{S})\d+%", r"\1[redacted]"),
    ("Jackson MS, ADR 0009", rf"(predicted{S}against{S}Pew's{S})\d+%", r"\1[redacted]"),
]
REDACT_RE = [(label, re.compile(p), r) for label, p, r in REDACT]


# ---- the transforms (pure; verify re-applies them) ---------------------------

def _serialise(fields: list[str]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow(fields)
    return buf.getvalue()


def strip_pew_columns(data: bytes) -> tuple[bytes, dict]:
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    if not lines:
        return data, {}
    header = next(csv.reader([lines[0].rstrip("\r\n")]))
    drop = {i for i, f in enumerate(header) if "pew" in f.lower()}
    if not drop:
        return data, {}
    out = []
    for line in lines:
        body = line.rstrip("\r\n")
        end = line[len(body):]
        if not body:
            out.append(line)
            continue
        fields = next(csv.reader([body]))
        if _serialise(fields) != body:
            raise ValueError(f"CSV line does not round-trip: {body[:80]!r}")
        out.append(_serialise([f for i, f in enumerate(fields) if i not in drop]) + end)
    return "".join(out).encode("utf-8"), {"dropped": sorted(header[i] for i in drop),
                                          "rows": len(lines) - 1}


def _strip_jackson(node):
    if isinstance(node, dict):
        return {k: _strip_jackson(v) for k, v in node.items()
                if not (k == "pew" and isinstance(v, (int, float)))}
    if isinstance(node, list):
        return [_strip_jackson(v) for v in node]
    return node


def strip_jackson_pew(data: bytes) -> tuple[bytes, dict]:
    if b'"jackson_ms"' not in data:
        return data, {}
    new, n = JACKSON.subn(rb"\1", data)
    if not n:
        return data, {}
    old_doc, new_doc = json.loads(data), json.loads(new)

    def only_jackson(node, path=""):
        # the stripped keys are exactly composition_check/jackson_ms/pew
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "pew" and isinstance(v, (int, float)) and not path.endswith("/jackson_ms"):
                    raise ValueError(f"unexpected numeric pew key at {path}")
                only_jackson(v, f"{path}/{k}")
        elif isinstance(node, list):
            for v in node:
                only_jackson(v, path)

    only_jackson(old_doc)
    if new_doc != _strip_jackson(old_doc):
        raise ValueError("JSON strip changed more than the jackson_ms pew values")
    return new, {"removed": n}


def redact_report(data: bytes) -> tuple[bytes, dict]:
    if b"Pew" not in data and b"Mississippi" not in data:
        return data, {}
    text = data.decode("utf-8")
    counts = {}
    for label, rx, rep in REDACT_RE:
        text, n = rx.subn(rep, text)
        if n:
            counts[label] = n
    return (text.encode("utf-8"), counts) if counts else (data, {})


def transform(path: str, data: bytes) -> tuple[bytes | None, str | None, dict]:
    """(new content or None to remove, the transform's name, its record)."""
    if path == TABLE:
        return None, "table removed", {}
    if LOMO.search(path):
        new, rec = strip_pew_columns(data)
        return new, "Pew columns stripped" if rec else None, rec
    if path.endswith(".json"):
        new, rec = strip_jackson_pew(data)
        return new, "jackson_ms pew value removed" if rec else None, rec
    if path.endswith(".md"):
        new, rec = redact_report(data)
        return new, "per-metro figures redacted" if rec else None, rec
    return data, None, {}


# ---- run -----------------------------------------------------------------------

def run(log_path: Path) -> None:
    import git_filter_repo as fr

    log: dict = {"transformed": {}}

    def file_info_callback(filename, mode, blob_id, value):
        path = filename.decode("utf-8")
        if path == TABLE:
            log["transformed"].setdefault(f"{path}@{blob_id.decode()}", "table removed")
            return (None, mode, blob_id)
        if not (LOMO.search(path) or path.endswith((".json", ".md"))):
            return (filename, mode, blob_id)
        cache = value.data.setdefault("cache", {})
        key = (path.rsplit(".", 1)[-1], blob_id)
        if key not in cache:
            data = value.get_contents_by_identifier(blob_id)
            new, name, rec = transform(path, data)
            if name is None or new == data:
                cache[key] = blob_id
            else:
                cache[key] = value.insert_file_with_contents(new)
                log["transformed"][f"{path}@{blob_id.decode()}"] = {"what": name, **rec}
        return (filename, mode, cache[key])

    args = fr.FilteringOptions.parse_args(["--force"])
    fr.RepoFilter(args, file_info_callback=file_info_callback).run()
    log_path.write_text(json.dumps(log, indent=1) + "\n")
    print(f"transformed {len(log['transformed'])} file versions; log: {log_path}")


# ---- verify --------------------------------------------------------------------

def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True).stdout


def tree(repo: Path, commit: str) -> dict[str, tuple[str, str]]:
    out = {}
    for line in git(repo, "ls-tree", "-r", "--full-tree", commit).decode().splitlines():
        meta, path = line.split("\t", 1)
        mode, _, sha = meta.split()
        out[path] = (mode, sha)
    return out


def verify(backup: Path, log_path: Path, out: Path, repo: Path = REPO) -> None:
    REPO = repo  # noqa: N806 (the repository that was rewritten)
    cmap = {}
    for line in (REPO / ".git" / "filter-repo" / "commit-map").read_text().splitlines()[1:]:
        old, new = line.split()
        cmap[old] = new
    rec: dict = {"commits_old": len(git(backup, "rev-list", "--all").split()),
                 "commits_new": len(git(REPO, "rev-list", "--all").split()),
                 "commits_mapped": len(cmap), "unchanged_commits": 0,
                 "problems": [], "transformed_paths": {}, "blobs_checked": 0}
    old_blob_new = {}
    for old, new in cmap.items():
        if new == "0" * 40:
            rec["problems"].append(f"{old}: pruned")
            continue
        if old == new:
            rec["unchanged_commits"] += 1
        fmt = "%an%x00%ae%x00%ad%x00%cn%x00%ce%x00%cd"
        if git(backup, "show", "-s", f"--format={fmt}", "--date=raw", old) != \
                git(REPO, "show", "-s", f"--format={fmt}", "--date=raw", new):
            rec["problems"].append(f"{old}: author/committer or dates differ")
        msg_old = git(backup, "show", "-s", "--format=%B", old).decode()
        msg_new = git(REPO, "show", "-s", "--format=%B", new).decode()
        for o, n in cmap.items():
            for k in (7, 8, 9, 10, 12, 40):
                msg_old = re.sub(rf"(?<![0-9a-f]){o[:k]}(?![0-9a-f])", n[:k], msg_old)
        if msg_old != msg_new:
            rec["problems"].append(f"{old}: message differs beyond rewritten hashes")
        t_old, t_new = tree(backup, old), tree(REPO, new)
        if set(t_old) - {TABLE} != set(t_new):
            rec["problems"].append(f"{old}: paths differ beyond the table")
        for path, (mode, sha) in t_old.items():
            if path == TABLE:
                continue
            nmode, nsha = t_new.get(path, (None, None))
            if nmode != mode:
                rec["problems"].append(f"{old}:{path}: mode differs")
            key = (path, sha)
            if key not in old_blob_new:
                data = git(backup, "cat-file", "blob", sha)
                new_data, name, _ = transform(path, data)
                expect = subprocess.run(["git", "hash-object", "--stdin"], input=new_data,
                                        capture_output=True, check=True).stdout.decode().strip()
                old_blob_new[key] = (expect, name)
                rec["blobs_checked"] += 1
            expect, name = old_blob_new[key]
            if nsha != expect:
                rec["problems"].append(f"{old}:{path}: blob is not the transform of the old one")
            if name and expect != sha:
                rec["transformed_paths"].setdefault(path, {"what": name, "versions": set()})
                rec["transformed_paths"][path]["versions"].add(sha[:12])
    for v in rec["transformed_paths"].values():
        v["versions"] = len(v["versions"])
    log = json.loads(log_path.read_text())
    rec["table_versions_removed"] = sum(1 for v in log["transformed"].values() if v == "table removed")
    rec["redactions"] = {}
    for k, v in log["transformed"].items():
        if isinstance(v, dict) and v.get("what") == "per-metro figures redacted":
            for label, n in v.items():
                if label != "what":
                    rec["redactions"][label] = rec["redactions"].get(label, 0) + n
    rec["remote_origin"] = git(REPO, "remote").decode().split()
    rec["refs"] = git(REPO, "for-each-ref", "--format=%(refname)").decode().split()
    rec["pass"] = not rec["problems"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(f"verify: {'pass' if rec['pass'] else 'FAIL'}; {rec['commits_mapped']} commits, "
          f"{len(rec['transformed_paths'])} transformed paths, {len(rec['problems'])} problems")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--log", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--backup", type=Path, required=True)
    v.add_argument("--log", type=Path, required=True)
    v.add_argument("--out", type=Path, required=True)
    v.add_argument("--repo", type=Path, default=REPO)
    a = ap.parse_args()
    if a.cmd == "run":
        run(a.log)
    else:
        verify(a.backup, a.log, a.out, a.repo)


if __name__ == "__main__":
    sys.exit(main())
