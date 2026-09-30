"""MIT Election Data and Science Lab, County Presidential Election Returns
2000-2024 (Harvard Dataverse, doi:10.7910/DVN/VOQCHQ, V20, released 25
February 2026) — Phase 4d (ADR 0019): each metro's 2024 presidential vote,
shown as context, never scored or asked.

The pinned file is the original-format CSV, countypres_2000-2024.csv
(10,222,208 bytes; the file Dataverse ingested as countypres_2000-2024.tab,
94,151 rows, 12 columns). Its licence, read from the dataset page on 30
September 2026: CC0 1.0; the Terms tab adds the Dataverse community norm
"proper credit is given via citation. Please use the data citation shown
on the dataset page".

The dataset sits behind a guestbook — name, email, institution and
position, then "Accept" — which the pipeline never fills in. Nathan
downloaded the dataset by hand on 30 September 2026 ("Original Format ZIP");
`pin` moves the file into the content-addressed cache and writes its
fetch-manifest entry, after checking it against the SHA-256 pinned here and
against the MD5 Dataverse publishes for the file. `fetch` returns the
pinned file and refuses anything else.

What the file holds (checked by `validate`, handled in build.political_lean):

  * one row per county x candidate x `mode`. 2020 splits some counties'
    votes by method (ELECTION DAY, ABSENTEE, PROVISIONAL, ...) beside a
    TOTAL row, and so does 2024 in nine states; some counties have split
    modes only (South Dakota's nine VOTE CENTER counties), and eight states'
    2024 rows carry no mode at all (""). The rule: TOTAL where a unit has
    it, otherwise the sum of its modes — never both.
  * rows that are not votes for anyone: "TOTAL VOTES CAST" (party "", in
    South Carolina, Texas, Wisconsin and West Virginia), UNDERVOTES and
    OVERVOTES (party "" in Wyoming, "OTHER" in Arizona, Iowa and DC), SPOILED
    (Vermont). They are dropped by name, whatever their party.
  * `totalvotes` is the unit's total as the state reports it, which in
    Arizona, Iowa and Vermont includes ballots with no valid presidential
    vote; the site's denominator is the votes cast for a candidate.
  * Alaska reports by state house district, not borough: county_fips holds
    2000 + the district (the codebook says so), which collides with real
    borough codes — DISTRICT 20 reads as 02020, Anchorage Municipality's —
    so Alaska's rows are districts and never join as counties.
  * Connecticut reports by its eight former counties, which the 2023
    delineation's planning regions do not nest in.
  * Kansas City, Missouri reports its own returns, apart from the four
    counties it spans (county_fips 2938000 in 2020 and 36000 in 2024).
  * a few candidate-vote cells read "NA" (New Mexico's Libertarian rows).

The lab's state-level returns (U.S. President 1976-2024,
doi:10.7910/DVN/42MVDX, CC0 1.0, no guestbook) are read as a check only:
the county file carries no state rows, and the brief holds each state's
summed county totals to the lab's own state totals.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

import pandas as pd

from atlas.pipeline.adapters.base import LICENSES, RawBundle
from atlas.pipeline.contracts.provenance import Provenance, Report
from atlas.pipeline.fetch import ATLAS, RAW, _load_manifest, _save_manifest, fetch

DATASET_DOI = "doi:10.7910/DVN/VOQCHQ"
DATASET_VERSION = "V20"
FILE_NAME = "countypres_2000-2024.csv"
# the Dataverse access URL of the original-format file; the manifest keys
# the pinned copy by it, as fetch() keys every download by its URL
URL = "https://dataverse.harvard.edu/api/access/datafile/13573089?format=original"
PINNED_SHA256 = "9299583148f5f8264baf50b5d929c260699c46d915909b13ea3c3850918946f8"
DATAVERSE_MD5 = "bd6661282936006b4ef4f5ee71418f3e"
PINNED_BYTES = 10_222_208
# the dataset's codebook, pinned beside the data as the record of what the
# columns mean (its md5 is Dataverse's too)
CODEBOOK_NAME = "County Presidential Returns 2000-2024.md"
CODEBOOK_URL = "https://dataverse.harvard.edu/api/access/datafile/11723285"
CODEBOOK_SHA256 = "12447fa5e7a7a823bc4416f34a6c624313cc703b745fcbfb2fe64902d2b37c70"
CODEBOOK_MD5 = "bb49e28faf9b18266665ab01dccf295f"

STATE_DOI = "doi:10.7910/DVN/42MVDX"
STATE_URL = "https://dataverse.harvard.edu/api/access/datafile/13887042"
STATE_SHA256 = "9936410a6dd4ecc8be7fe202c6dff5b5f8fee59d88f35ab542ed12879941dcb7"
STATE_MD5 = "405af83db7625cb35d8c19a5ebe029ff"

YEARS = ("2020", "2024")
COLUMNS = ["state", "county_name", "year", "state_po", "county_fips", "office",
           "candidate", "party", "candidatevotes", "totalvotes", "version", "mode"]
# rows that count no vote for anyone, named by the file itself
NOT_VOTES = ("TOTAL VOTES CAST", "UNDERVOTES", "OVERVOTES", "SPOILED")
# the state file's own names for the same
STATE_NOT_VOTES = ("OVERVOTES", "UNDERVOTES", "SPOILED", "VOID", "BLANK VOTES")


def _digest(path: Path) -> tuple[str, str]:
    b = path.read_bytes()
    return hashlib.sha256(b).hexdigest(), hashlib.md5(b).hexdigest()


def _cache_path(url: str, name: str) -> Path:
    """Where fetch() would keep url: the same content-addressed scheme."""
    return RAW / hashlib.sha256(url.encode()).hexdigest()[:16] / name


def _pin_one(src: Path, url: str, name: str, sha256: str, md5: str) -> Path:
    got_sha, got_md5 = _digest(src)
    assert got_sha == sha256, f"{src}: sha256 {got_sha} is not the pinned {sha256}"
    assert got_md5 == md5, f"{src}: md5 {got_md5} is not Dataverse's {md5}"
    dest = _cache_path(url, name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or _digest(dest)[0] != sha256:
        shutil.copyfile(src, dest)
    m = _load_manifest()
    m["files"][url] = {
        "path": str(dest.relative_to(ATLAS)),
        "sha256": sha256,
        "bytes": dest.stat().st_size,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "evicted": False,
        # the one entry not downloaded by fetch(): the dataset's guestbook
        "obtained": "downloaded by hand through the dataset's guestbook "
                    "(Nathan, 2026-09-30), checked against the pinned sha256 "
                    "and Dataverse's md5",
    }
    _save_manifest(m)
    return dest


def pin(download_dir: str | Path) -> list[Path]:
    """Pin Nathan's download (the folder unzipped from Dataverse's "Original
    Format ZIP"): the data file and its codebook, each refused unless it is
    byte for byte the file pinned here."""
    d = Path(download_dir)
    return [_pin_one(d / FILE_NAME, URL, FILE_NAME, PINNED_SHA256, DATAVERSE_MD5),
            _pin_one(d / CODEBOOK_NAME, CODEBOOK_URL, CODEBOOK_NAME, CODEBOOK_SHA256,
                     CODEBOOK_MD5)]


def _pinned(url: str, name: str, sha256: str) -> Path:
    entry = _load_manifest()["files"].get(url)
    path = _cache_path(url, name)
    assert entry and path.exists(), (
        f"{name} is not pinned: download the dataset by hand from "
        f"https://doi.org/10.7910/DVN/VOQCHQ (its guestbook asks for a name, an "
        f"email, an institution and a position) and run "
        f"`python -m atlas.pipeline.adapters.medsl_president pin <unzipped folder>`")
    got = _digest(path)[0]
    assert got == sha256 == entry["sha256"], (
        f"{path}: sha256 {got} is not the pinned {sha256}")
    return path


class MedslCountyPresidentAdapter:
    source_id = "medsl_president"
    vintage = f"County Presidential Election Returns 2000-2024 ({DATASET_VERSION}, 2026-02-25)"
    license = LICENSES["medsl_president"]

    def fetch(self) -> RawBundle:
        return RawBundle(self.source_id, [_pinned(URL, FILE_NAME, PINNED_SHA256)],
                         {"doi": DATASET_DOI, "version": DATASET_VERSION})

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        """The 2020 and 2024 rows, every column as published (strings), plus
        `votes` (candidatevotes as a number; "NA" reads as missing)."""
        df = pd.read_csv(raw.paths[0], dtype=str, keep_default_na=False)
        assert list(df.columns) == COLUMNS, df.columns.tolist()
        df = df[df["year"].isin(YEARS)].copy()
        df["votes"] = pd.to_numeric(df["candidatevotes"].replace("NA", None))
        df["totalvotes"] = pd.to_numeric(df["totalvotes"])
        return df.reset_index(drop=True)

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        checks, fails = [], []
        for y in YEARS:
            d = df[df["year"] == y]
            states = d["state_po"].nunique()
            checks.append(f"{y}: {len(d):,} rows, {states} states and DC")
            if states != 51:
                fails.append(f"{y}: {states} states and DC, not 51")
        if (df["office"] != "US PRESIDENT").any():
            fails.append("rows for an office other than US PRESIDENT")
        blank_party = set(df.loc[df["party"] == "", "candidate"])
        if not blank_party <= set(NOT_VOTES):
            fails.append(f"party-less rows that are not a known non-vote: "
                         f"{sorted(blank_party - set(NOT_VOTES))}")
        checks.append(f"party-less rows are non-votes only: {sorted(blank_party)}")
        na = df["votes"].isna()
        checks.append(f"{int(na.sum())} candidate-vote cells read NA "
                      f"({sorted(set(df.loc[na, 'state_po']))})")
        if (df["votes"].dropna() < 0).any() or (df["totalvotes"] < 0).any():
            fails.append("negative vote counts")
        per_unit = df.groupby(["year", "state_po", "county_fips"])["totalvotes"].nunique()
        if (per_unit > 1).any():
            fails.append(f"{int((per_unit > 1).sum())} units with more than one totalvotes")
        return Report(self.source_id, not fails, checks, fails)

    def provenance(self) -> Provenance:
        return Provenance("medsl_president",
                          "County Presidential Election Returns 2000-2024",
                          FILE_NAME, ("candidatevotes", "party", "mode"),
                          "county (Alaska: house district) -> cbsa",
                          "2024", "political_lean_v1", "measured")


class MedslStatePresidentAdapter:
    """The lab's state-level returns, 2024 and 2020 — a check only (the
    county sums against the lab's own state totals); no served figure
    traces to it."""
    source_id = "medsl_president_state"
    vintage = "U.S. President 1976-2024 (V10, 2026-09-04)"
    license = LICENSES["medsl_president_state"]

    def fetch(self) -> RawBundle:
        path = fetch(STATE_URL)
        got_sha, got_md5 = _digest(path)
        assert got_sha == STATE_SHA256, f"{path}: sha256 {got_sha} is not the pinned {STATE_SHA256}"
        assert got_md5 == STATE_MD5, f"{path}: md5 {got_md5} is not Dataverse's {STATE_MD5}"
        return RawBundle(self.source_id, [path], {"doi": STATE_DOI})

    def normalize(self, raw: RawBundle) -> pd.DataFrame:
        df = pd.read_csv(raw.paths[0], dtype=str, keep_default_na=False)
        df = df[df["year"].isin(YEARS)].copy()
        df["votes"] = pd.to_numeric(df["candidatevotes"])
        df["totalvotes"] = pd.to_numeric(df["totalvotes"])
        return df.reset_index(drop=True)

    def validate(self, raw: RawBundle) -> Report:
        df = self.normalize(raw)
        fails = [f"{y}: {df[df['year'] == y]['state_po'].nunique()} states and DC"
                 for y in YEARS if df[df["year"] == y]["state_po"].nunique() != 51]
        return Report(self.source_id, not fails, ["51 states and DC in 2020 and 2024"], fails)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "pin":
        for p in pin(sys.argv[2]):
            print(f"pinned {p.relative_to(ATLAS)}")
        print(json.dumps({u: _load_manifest()["files"][u]["sha256"] for u in (URL, CODEBOOK_URL)},
                         indent=1))
    else:
        raise SystemExit(__doc__)
