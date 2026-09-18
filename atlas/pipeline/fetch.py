"""Downloads with a content-addressed cache under data/raw/, plus Census API GETs.

Every file fetched is recorded in results/fetch_manifest.json (URL, SHA-256,
bytes, timestamp) so each number downstream is traceable to an exact source
artifact. Large PUMS zips may be evicted from disk after use; the manifest
entry survives with evicted=true.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

import requests

ATLAS = Path(__file__).resolve().parents[1]
REPO = ATLAS.parent
DATA = ATLAS / "data"
RAW = DATA / "raw"
RESULTS = ATLAS / "results"
MANIFEST = RESULTS / "fetch_manifest.json"

UA = "DatingStatsAtlas-phase0/0.1 (python-requests; research pipeline)"
API_BASE = "https://api.census.gov/data"


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"files": {}, "api_datasets": {}}


def _save_manifest(m: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    adapter = requests.adapters.HTTPAdapter(
        max_retries=requests.adapters.Retry(
            total=5, backoff_factor=2.0, status_forcelist=[429, 500, 502, 503, 504]
        )
    )
    s.mount("https://", adapter)
    return s


SESSION = _session()


def census_api_key() -> str:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        key_file = REPO / "CENSUS_API_KEY.txt"
        if key_file.exists():
            key = key_file.read_text().strip()
    if not key:
        raise RuntimeError("No Census API key: set CENSUS_API_KEY or create CENSUS_API_KEY.txt")
    return key


def fetch(url: str, timeout: int = 300, headers: dict | None = None) -> Path:
    """Download url into the content-addressed cache; return local path.

    Cache key is the URL hash; integrity is the SHA-256 of the content,
    recorded in the manifest. A file already on disk with the manifest's
    byte size is reused without re-downloading. `headers` overrides for
    hosts that refuse the pipeline's plain UA (huduser.gov answers a
    non-browser agent with an empty 202 instead of the file).
    """
    m = _load_manifest()
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    name = url.rstrip("/").rsplit("/", 1)[-1]
    dest = RAW / key / name
    entry = m["files"].get(url)
    if dest.exists() and entry and dest.stat().st_size == entry["bytes"]:
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    sha = hashlib.sha256()
    n = 0
    with SESSION.get(url, stream=True, timeout=timeout, headers=headers) as r:
        r.raise_for_status()
        with open(part, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                sha.update(chunk)
                n += len(chunk)
    os.replace(part, dest)
    m = _load_manifest()
    m["files"][url] = {
        "path": str(dest.relative_to(ATLAS)),
        "sha256": sha.hexdigest(),
        "bytes": n,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "evicted": False,
    }
    _save_manifest(m)
    print(f"  fetched {name} ({n / 1e6:.1f} MB)")
    return dest


def evict(url: str) -> None:
    """Delete a cached file from disk (to bound disk usage) but keep its manifest entry."""
    m = _load_manifest()
    entry = m["files"].get(url)
    if not entry:
        return
    p = ATLAS / entry["path"]
    if p.exists():
        p.unlink()
        try:
            p.parent.rmdir()
        except OSError:
            pass
    entry["evicted"] = True
    _save_manifest(m)


def api_get(dataset: str, params: dict, timeout: int = 120) -> list[list]:
    """GET api.census.gov/data/<dataset> with the API key; return parsed JSON rows.

    dataset example: "2024/acs/acs5". The key is injected here and never logged.
    """
    url = f"{API_BASE}/{dataset}"
    q = dict(params)
    q["key"] = census_api_key()
    last_err = None
    for attempt in range(5):
        try:
            r = SESSION.get(url, params=q, timeout=timeout)
            if r.status_code == 200:
                m = _load_manifest()
                m["api_datasets"][dataset] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                _save_manifest(m)
                return r.json()
            last_err = f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code < 500 and r.status_code != 429:
                break
        except requests.RequestException as e:  # noqa: PERF203
            last_err = str(e)
        time.sleep(2 ** attempt)
    raise RuntimeError(f"Census API failed for {url} params={params}: {last_err}")


def disk_free_gb() -> float:
    return shutil.disk_usage(DATA).free / 1e9


if __name__ == "__main__":
    # Smoke test on the small reference files used by the bridge.
    for u in [
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx",
        "https://www2.census.gov/geo/docs/maps-data/data/rel2020/2020_Census_Tract_to_2020_PUMA.txt",
        "https://www2.census.gov/geo/docs/maps-data/data/rel/2010_Census_Tract_to_2010_PUMA.txt",
        "https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMS_Data_Dictionary_2020-2024.csv",
    ]:
        p = fetch(u)
        print(p)
    rows = api_get("2024/acs/acs5", {"get": "NAME,B01003_001E", "for": "state:11"})
    print("API ok:", rows[1])
    print(f"disk free: {disk_free_gb():.1f} GB")
