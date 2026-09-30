"""Phase 4d (ADR 0019, Nathan's decision): political lean is context — never
scored, never a filter, never a weight, never feeding the compatibility
figure, never asked. The engine composes it from the build's summed votes,
always in the same order, and nothing a ranking reads can see it."""
import copy
import json
import re
from pathlib import Path

import numpy as np
import pytest

from atlas import model as engine
from atlas.model.context import SEGMENTS, political_lean_all, political_lean_block
from atlas.model.scoring import scored_features

FIXTURE_DIR = Path(__file__).resolve().parent / "golden" / "fixture_build"
GOLDENS = Path(__file__).resolve().parent / "golden" / "goldens.json"


@pytest.fixture(scope="module")
def build():
    return engine.load_build(FIXTURE_DIR)


def _without_votes(build, which=None):
    """A copy of the build whose political votes are blank — every metro's,
    or metro `which`'s alone — with a fresh memo."""
    b = copy.copy(build)
    b.memo = {}
    b.political = {k: v.copy() for k, v in build.political.items()}
    for v in b.political.values():
        if which is None:
            v[:] = np.nan
        else:
            v[which] = np.nan
    return b


def test_every_fixture_metro_shows_its_shares_in_the_fixed_order(build):
    s = build.manifest["strings"]
    for i, cbsa in enumerate(build.metro_levels):
        b = political_lean_block(build, i)
        assert b["available"], cbsa
        assert [x["key"] for x in b["segments"]] == list(SEGMENTS) == ["dem", "other", "rep"]
        assert [x["label"] for x in b["segments"]] == [
            s["political_lean_dem"], s["political_lean_other"], s["political_lean_rep"]]
        assert abs(sum(x["width"] for x in b["segments"]) - 100) < 0.02
        # the shares divide the metro's summed votes once
        dem, rep, votes = (build.political[k][i] for k in ("dem", "rep", "votes"))
        assert b["share"] == {"dem": round(dem / votes, 6), "rep": round(rep / votes, 6)}
        d, o, r = (x["display"] for x in b["segments"])
        assert re.fullmatch(r"\d{1,3}%", d) and re.fullmatch(r"\d{1,3}%", r)
        assert b["text"] == f"{d} Democratic\u00a0· {r} Republican"
        assert b["bar_label"] == f"Democratic {d}, Everyone else {o}, Republican {r}"
        assert b["text"].index("Democratic") < b["text"].index("Republican")


def test_a_metro_without_figures_is_not_available(build):
    b = _without_votes(build, which=0)
    blk = political_lean_block(b, 0)
    assert blk == {"available": False, "note": "Not available"}
    assert blk["note"] == build.manifest["strings"]["political_lean_missing"]
    assert political_lean_block(b, 1)["available"]


def test_political_lean_is_never_scored(build):
    fb = build.legend["political_lean"]
    assert fb["status"] == "context_only" and fb["weight_in_pillar"] == 0
    assert fb["pillar"] == "context" and not fb.get("band_labels")
    assert "political_lean" not in [f["id"] for f in scored_features(build)]
    assert "political_lean" not in build.manifest["city_cards"]


def test_no_ranking_can_see_political_lean(build):
    """Blanking every metro's votes changes nothing any golden search is
    served: the rankings do not read it."""
    blank = _without_votes(build)
    for v in json.loads(GOLDENS.read_text())["vectors"]:
        req = engine.parse_request(v["request"])
        a, b = engine.rank(build, req), engine.rank(blank, req)
        assert json.dumps(a) == json.dumps(b), v["name"]
        assert "politic" not in json.dumps(a).lower()


def test_every_metro_is_keyed_by_its_code(build):
    all_ = political_lean_all(build)
    assert list(all_) == build.metro_levels
