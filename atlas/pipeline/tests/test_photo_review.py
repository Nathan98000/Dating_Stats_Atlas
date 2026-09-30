"""The photo review's decisions are what the site renders (Phase 4 Stage 3,
ADR 0012; Nathan's calls after Phase 4c, 2026-09-29: keep every removed
photograph except Waco's, and replace Waco's and Savannah's). Read from the
committed records only — the review, the manifests, the render data and the
credits list — since the image files themselves are gitignored."""
import json
import re
import urllib.parse

import pandas as pd
import pytest

from atlas.pipeline.build import photo_review as PR
from atlas.pipeline.fetch import RESULTS

WEB = RESULTS.parents[0] / "web" / "src" / "data"


@pytest.fixture(scope="module")
def state():
    return {"rev": json.loads(PR.REVIEW.read_text()),
            "city": json.loads((WEB / "city-images.json").read_text()),
            "stat": json.loads((WEB / "stat-images.json").read_text()),
            "city_csv": pd.read_csv(RESULTS / "phase2e" / "city_images.csv", dtype={"cbsa": str}),
            "stat_csv": pd.read_csv(RESULTS / "phase2e" / "stat_images.csv"),
            "credits": json.loads(PR.CREDITS.read_text())}


def _page(state, r):
    if r["page"] == "city":
        return state["city"], state["city_csv"][state["city_csv"]["slug"] == r["key"]].iloc[0]
    return state["stat"], state["stat_csv"][state["stat_csv"]["stat"] == r["key"]].iloc[0]


def _file_of(url: str) -> str:
    """The Commons file title a source link points at (links are
    percent-encoded: "façade" travels as "fa%C3%A7ade")."""
    return "File:" + urllib.parse.unquote(url.rsplit("File:", 1)[-1])


def test_nathans_calls_are_recorded(state):
    rev = state["rev"]
    assert [r["key"] for r in rev["removed"]] == ["waco-texas"]
    assert len(rev["restored"]) == 15
    assert {r["key"] for r in rev["replaced"]} == {"waco-texas", "savannah-georgia"}
    assert not any(f["key"] == "savannah-georgia" for f in rev["findings_not_acted_on"])


def test_every_restored_photograph_renders_as_recorded(state):
    for r in state["rev"]["restored"]:
        render, row = _page(state, r)
        assert r["key"] in render, r["key"]
        assert row["status"] == "ok", r["key"]
        assert row["file_title"] == r["file_title"]
        assert _file_of(render[r["key"]]["source_url"]) == r["file_title"]


def test_each_replaced_page_takes_the_named_file_and_refuses_the_old(state):
    refused = PR.refused_files()
    pinned = PR.pinned_files()
    for r in state["rev"]["replaced"]:
        render, row = _page(state, r)
        assert pinned[(r["page"], r["key"])] == r["file_title"]
        assert row["status"] == "ok" and row["file_title"] == r["file_title"]
        assert _file_of(render[r["key"]]["source_url"]) == r["file_title"]
        assert r["was"] in refused and r["was"] != r["file_title"]
        # the licence rule holds for a named file as for any other
        assert re.match(r"^(public domain|cc0|cc by(-sa)? \d)", render[r["key"]]["license"], re.I)
        assert render[r["key"]]["author"]


def test_the_removed_collage_renders_nowhere(state):
    gone = {r["file_title"] for r in state["rev"]["removed"]}
    shown = {_file_of(v["source_url"]) for d in (state["city"], state["stat"]) for v in d.values()}
    assert not gone & shown


def test_a_review_alt_text_replaces_an_unusable_description(state):
    for r in state["rev"]["replaced"]:
        if r.get("alt"):
            render, _ = _page(state, r)
            assert render[r["key"]]["alt"] == r["alt"]
    assert state["city"]["savannah-georgia"]["alt"].startswith("The Forsyth Park fountain")


def test_the_credits_list_covers_every_photograph_shown(state):
    cr = state["credits"]
    shown = len(state["city"]) + len(state["stat"]) + 1          # and the hero
    assert cr["photos_in_use"] == shown == len(cr["photos"])
    listed = {(p["page"], p["key"]) for p in cr["photos"]}
    assert {("city", k) for k in state["city"]} <= listed
    assert {("stat", k) for k in state["stat"]} <= listed
