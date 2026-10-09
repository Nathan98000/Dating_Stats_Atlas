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
    # after the Phase 5 report a restored photograph can give way to the
    # city's card photograph from outside Commons (checked below)
    outside = {(r["page"], r["key"]) for r in state["rev"].get("external_files", [])}
    for r in state["rev"]["restored"]:
        if (r["page"], r["key"]) in outside:
            continue
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


def test_phase4e_stat_photos_are_the_reviewed_picks(state):
    """Phase 4e items 3-4: who lives here takes the first of its subjects
    whose lead image passes; political lean, none of whose subjects passes,
    takes the file the review names — and the refused candidate stays
    refused on any re-run."""
    p4e = state["rev"]["phase4e_stat_pages"]
    from atlas.pipeline.build.city_images import STAT_SUBJECTS
    assert STAT_SUBJECTS["who_lives_here"] == p4e["subjects"]["who_lives_here"]
    assert STAT_SUBJECTS["political_lean"] == p4e["subjects"]["political_lean"]
    assert "Crowd" not in STAT_SUBJECTS["who_lives_here"]
    refused = PR.refused_files()
    for r in p4e["refused"]:
        assert refused[r["file_title"]] == f"refused_review:{r['category']}"
    pinned = PR.pinned_files()
    alts = PR.pinned_alts()
    for r in p4e["pinned"]:
        assert pinned[(r["page"], r["key"])] == r["file_title"]
        assert state["stat"][r["key"]]["alt"] == alts[(r["page"], r["key"])] == r["alt"]
    shown = {k: _file_of(v["source_url"]).replace(" ", "_") for k, v in state["stat"].items()}
    assert shown["who_lives_here"] == p4e["checked"][0]["file_title"]
    assert shown["political_lean"] == p4e["pinned"][0]["file_title"].replace(" ", "_")
    for key in ("who_lives_here", "political_lean"):
        row = state["stat_csv"][state["stat_csv"]["stat"] == key].iloc[0]
        assert row["status"] == "ok" and row["file"] == state["stat"][key]["file"]
        assert state["stat"][key]["cropped"] is False
        assert re.match(r"^(public domain|cc0|cc by(-sa)? \d)", state["stat"][key]["license"], re.I)
        assert ("stat", key) in {(p["page"], p["key"]) for p in state["credits"]["photos"]}
    # no alternate ships: each page renders exactly its pick
    for key, alts_ in p4e["alternates"].items():
        assert not {a["file_title"].replace(" ", "_") for a in alts_} & {shown[key]}


def test_a_photograph_from_outside_commons_is_pinned_by_hash(state):
    """2026-10-07 (Nathan's pick): the everyday prices photograph comes from
    Pixabay by way of needpix, not Commons. The review records its credit,
    its alt text, its exact bytes and the evidence for its licence; the page
    renders exactly that record, and the licence is on the cleared list."""
    from atlas.pipeline.build import city_images as CI
    ext = PR.external_files()
    rec = ext[("stat", "everyday_prices")]
    assert CI.REVIEW_EXTERNAL[("stat", "everyday_prices")] == rec
    entry = state["stat"]["everyday_prices"]
    for k in ("author", "license", "license_url", "source_url", "title", "alt"):
        assert entry[k] == rec[k], k
    assert entry["cropped"] is False
    row = state["stat_csv"][state["stat_csv"]["stat"] == "everyday_prices"].iloc[0]
    assert row["status"] == "ok" and row["sha256"] == rec["sha256"] and row["file"] == entry["file"]
    # CC0 (Pixabay's licence for every upload before 9 January 2019), and
    # the record names the evidence: the upload date and the byte match
    assert re.match(r"^(public domain|cc0)", rec["license"], re.I)
    evidence = " ".join(rec["licence_evidence"])
    assert "March 6, 2017" in evidence and "9 January 2019" in evidence and "byte-identical" in evidence
    assert len(rec["sha256"]) == 64
    # the photograph it replaces renders nowhere, and no Commons pin competes
    assert rec["was"] not in {_file_of(v["source_url"]) for v in state["stat"].values()}
    assert ("stat", "everyday_prices") not in PR.pinned_files()


def test_the_pleasant_days_photograph_is_credited_to_its_photographer(state):
    """The credit audit after Phase 6 (Nathan, 2026-10-09: "Credit Billy
    Hathorn"): the file's metadata gave the 1846 painting's licence and its
    painter. The review pins the photograph's own credit, as its Commons
    page states it — CC BY 3.0, by Billy Hathorn — on the same bytes; the
    page renders exactly that record, and the licence is on the cleared
    list."""
    from atlas.pipeline.build import city_images as CI
    rec = PR.external_files()[("stat", "pleasant_days")]
    assert CI.REVIEW_EXTERNAL[("stat", "pleasant_days")] == rec
    entry = state["stat"]["pleasant_days"]
    for k in ("author", "license", "license_url", "source_url", "title", "alt"):
        assert entry[k] == rec[k], k
    assert (entry["author"], entry["license"]) == ("Billy Hathorn", "CC BY 3.0")
    assert rec["credit_was"] == {"author": "Thomas Cole", "license": "Public domain",
                                 "license_url": None}
    assert CI.ALLOW.match(rec["license"]) and not CI.REFUSE.search(rec["license"])
    evidence = " ".join(rec["licence_evidence"])
    assert "{{self|cc-by-3.0}}" in evidence and "Photo by Billy Hathorn" in evidence
    assert entry["cropped"] is False
    row = state["stat_csv"][state["stat_csv"]["stat"] == "pleasant_days"].iloc[0]
    assert row["status"] == "ok" and row["sha256"] == rec["sha256"] and row["file"] == entry["file"]
    assert ("stat", "pleasant_days", "CC BY 3.0") in {
        (p["page"], p["key"], p["license"]) for p in state["credits"]["photos"]}


def test_every_ranked_city_has_a_representative_photograph_recorded(state):
    """After the Phase 5 report (Nathan, 2026-10-08): every ranked city —
    any of them can be a home-page card — has a photograph, from any source
    (he arranges the permission), and every city photograph is credited
    "cropped" (the cards and the city page's band crop them). A photograph
    from outside Commons renders exactly its review record, pinned by its
    bytes; a kept photograph's rewritten alt text is the one rendered."""
    idx = json.loads((WEB / "search-index.json").read_text())
    ranked = [e["s"] for e in idx if e["r"]]
    assert all(s in state["city"] for s in ranked), [s for s in ranked if s not in state["city"]]
    assert all(v["cropped"] is True for v in state["city"].values())
    for r in state["rev"].get("external_files", []):
        if r["page"] != "city":
            continue
        entry = state["city"][r["key"]]
        for k in ("author", "license", "source_url", "title", "alt"):
            assert entry[k] == r[k], (r["key"], k)
        row = state["city_csv"][state["city_csv"]["slug"] == r["key"]].iloc[0]
        assert row["status"] == "ok" and row["sha256"] == r["sha256"] and row["file"] == entry["file"]
    for r in state["rev"].get("alt_overrides", []):
        assert state["city"][r["key"]]["alt"] == r["alt"], r["key"]
