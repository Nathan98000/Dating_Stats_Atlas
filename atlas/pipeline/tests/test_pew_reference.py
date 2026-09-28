"""Phase 3c (A3): the Pew intermarriage table is a build-time reference and
nothing derived from it may reach the artifact. The typed licence registry
carries it as non-shippable, and build.validate's hard check inspects the
shipped files directly because the table is read outside any adapter.

Phase 4 (ADR 0012): the table is build-time only, never published and never
compared in public. It lives only in the gitignored private folder on the
build machine, so every test here that needs it skips where it is absent,
and no tracked file may carry its header line or a Pew column."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from atlas.pipeline.adapters.base import LICENSES
from atlas.pipeline.build import pew_guard as G
from atlas.pipeline.build.validate import check_pew_never_shipped

FIXTURE = Path(__file__).resolve().parents[1].parent / "model" / "tests" / "golden" / "fixture_build"
REPO = Path(__file__).resolve().parents[3]


def test_pew_licence_is_registered_and_non_shippable():
    lic = LICENSES["pew_intermarriage"]
    assert lic.shippable is False
    assert "pew_intermarriage_2015.csv" in (lic.notes or "")
    assert "data/private/pew" in (lic.notes or "")


def test_fixture_build_carries_nothing_from_pew():
    out = check_pew_never_shipped(FIXTURE)
    assert out["pass"], out


@pytest.mark.parametrize("leak", [
    lambda m, k: m.__setitem__("pew_level_offset", 1.38),
    lambda m, k: k.setdefault("fitting_sample_spec", {}).__setitem__("note", "calibrated to Pew"),
    lambda m, k: m["features_block"].__setitem__(
        "x", {"provenance": {"source": "pew_intermarriage"}}),
])
def test_a_leak_fails_the_check(tmp_path, leak):
    m = json.loads((FIXTURE / "manifest.json").read_text())
    k = json.loads((FIXTURE / "kernel.json").read_text())
    leak(m, k)
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    (tmp_path / "kernel.json").write_text(json.dumps(k))
    assert not check_pew_never_shipped(tmp_path)["pass"]


def _tracked_files() -> list[str]:
    try:
        out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z"],
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [f for f in out.decode().split("\0") if f]


def test_no_tracked_file_carries_a_pew_column_or_the_table_header():
    offenders = {}
    for f in _tracked_files():
        p = REPO / f
        if not p.is_file():
            continue
        found = G.tracked_file_findings(f, p.read_bytes())
        if found:
            offenders[f] = found
    assert not offenders, offenders


@pytest.mark.parametrize("path,text", [
    ("x.csv", "msa_code,metro_name,pew_total,shrunk_dial\n10420,\"Akron, OH\",0.5,0.4\n"),
    ("x.tsv", "msa_code\tPew_rate\n10420\t0.5\n"),
    ("x.json", json.dumps({"composition_check": {"jackson_ms": {"pew": 0.5}}})),
    ("x.json", json.dumps({"rows": [{"msa_code": "10420", "pew_total": 0.5}]})),
])
def test_the_tracked_file_check_sees_a_pew_column(path, text):
    assert G.tracked_file_findings(path, text.encode())


def test_the_tracked_file_check_passes_our_own_names():
    # our predictions, and aggregates named after the comparison, are not Pew's values
    text = json.dumps({"pew_pred": {"shrunk_dial": 0.2}, "pew_national": 0.16,
                       "level_offset_ratio_ours_over_pew": 1.4,
                       "pew_corrected_median_abs_pts": 2.5})
    assert G.tracked_file_findings("x.json", text.encode()) == {}
    assert G.tracked_file_findings(
        "x.csv", b"msa_code,national_only,shrunk_dial\n10420,0.2,0.3\n") == {}


@pytest.mark.skipif(not G.PEW_TABLE.exists(),
                    reason="Pew's table is private: only the build machine has it")
def test_the_private_table_is_ignored_and_its_header_is_the_one_guarded():
    rel = G.PEW_TABLE.relative_to(REPO)
    ignored = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", str(rel)])
    assert ignored.returncode == 0, f"{rel} is not gitignored"
    assert G.has_pew_header(G.PEW_TABLE.read_text())


def test_pew_comparison_writes_no_pew_values(tmp_path):
    """The comparison reads Pew's values in memory; what it writes to the
    per-metro table and the record carries our predictions only. Synthetic
    inputs: none of these numbers is Pew's."""
    from atlas.pipeline.build import kernel as K
    codes = [f"{10000 + i}" for i in range(12)] + ["27140"]
    rng = np.random.default_rng(0)
    pew = pd.DataFrame({"msa_code": codes, "metro_name": [f"M{c}" for c in codes],
                        "pew_total": rng.uniform(0.05, 0.4, len(codes))})
    lomo = [{"cbsa": c, "pew_pred": {k: float(rng.uniform(0.05, 0.4)) for k in (
        "national_only", "raw_dial", "shrunk_dial", "random_pairing",
        "observed_fitting_sample")}} for c in codes]
    full = {c: SimpleNamespace(W=float(rng.uniform(1, 5))) for c in codes}
    out_csv = tmp_path / "pew_lomo_test.csv"
    rec, comp = K.pew_comparison(lomo, pew, 0.16, 0.24, codes, full, out_csv)
    assert G.tracked_file_findings("pew_lomo_test.csv", out_csv.read_bytes()) == {}
    assert "pew_total" not in pd.read_csv(out_csv).columns
    assert "pew" not in comp["jackson_ms"]
    assert G.json_pew_value_paths({"rec": rec, "comp": comp}) == []
