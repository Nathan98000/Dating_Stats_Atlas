"""Phase 3c (A3): the Pew intermarriage table is a build-time reference and
nothing derived from it may reach the artifact. The typed licence registry
carries it as non-shippable, and build.validate's hard check inspects the
shipped files directly because the table is read outside any adapter."""
import json
from pathlib import Path

import pytest

from atlas.pipeline.adapters.base import LICENSES
from atlas.pipeline.build.validate import check_pew_never_shipped

FIXTURE = Path(__file__).resolve().parents[1].parent / "model" / "tests" / "golden" / "fixture_build"


def test_pew_licence_is_registered_and_non_shippable():
    lic = LICENSES["pew_intermarriage"]
    assert lic.shippable is False
    assert "pew_intermarriage_2015.csv" in (lic.notes or "")


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
