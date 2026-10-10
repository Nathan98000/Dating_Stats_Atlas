"""After the credit audit (Nathan, 2026-10-10): clear_licence reads the
file's own Commons page, and a photograph of an old artwork is cleared and
credited under the photograph's licence and photographer, never the
artwork's. Every other page keeps the metadata's answer. No network: the
pages are the files' wikitext as read on 9 October 2026 (abridged), the
metadata what imageinfo answered for them."""
from __future__ import annotations

from atlas.pipeline.build import city_images as CI
from atlas.pipeline.build import commons_page as CP


def ii(licence: str, artist: str, url: str = "", mime: str = "image/jpeg") -> dict:
    return {"mime": mime, "extmetadata": {
        "LicenseShortName": {"value": licence}, "Artist": {"value": artist},
        "LicenseUrl": {"value": url}, "ImageDescription": {"value": "a description"}}}


JACKSON_SQUARE = """== {{int:filedesc}} ==
{{artwork
|artist = {{Creator:Clark Mills (sculptor)}}
|Description={{de|Jackson Square in New Orleans}} {{en|Jackson Square in New Orleans}}
|Source={{own}}
|Date=2009-06-12
|Author=[[User:Dschwen|Daniel Schwen]]
|Permission=
|other_versions=
}}
{{Location|29|57|26.834|N|90|3|45.986|W|heading:W}}

== {{int:license-header}} ==
{{PD-old}}
{{self|cc-by-sa-4.0}}
{{QualityImage}}
[[Category:Jackson Square, New Orleans]]
"""

THE_PICNIC = """== {{int:filedesc}} ==
{{Artwork
|Description    ={{en|"The Picnic"}}
|Source         = Photo by Billy Hathorn, 7-23-2011
|artist         ={{creator:Thomas Cole}}
|Date           =1846
|institution={{institution:Brooklyn Museum}}
}}
== {{int:license-header}} ==
{{PD-old-100-1923}}
{{self|cc-by-3.0}}
"""


def page(licence_section: str, description: str = "{{Information|author=[[User:Snap|Snap Shot]]|source={{own}}}}") -> str:
    return f"== {{{{int:filedesc}}}} ==\n{description}\n== {{{{int:license-header}}}} ==\n{licence_section}\n"


def test_jackson_square_is_the_photographers_cc_by_sa_4_not_the_statues_public_domain():
    cleared, reason = CI.clear_licence(ii("Public domain", "Clark Mills"), page=JACKSON_SQUARE)
    assert reason == ""
    assert (cleared["license"], cleared["author"]) == ("CC BY-SA 4.0", "Daniel Schwen")
    assert cleared["license_url"] == "https://creativecommons.org/licenses/by-sa/4.0"


def test_the_picnic_is_billy_hathorns_cc_by_3_not_thomas_coles_public_domain():
    cleared, _ = CI.clear_licence(ii("Public domain", "<bdi>Thomas Cole</bdi>"), page=THE_PICNIC)
    assert (cleared["license"], cleared["author"]) == ("CC BY 3.0", "Billy Hathorn")
    assert cleared["license_url"] == "https://creativecommons.org/licenses/by/3.0"


def test_the_hero_gate_no_longer_reads_such_a_photograph_as_public_domain():
    from atlas.pipeline.build.hero_image import STRICT_PD
    cleared, _ = CI.clear_licence(ii("Public domain", "Clark Mills"), page=JACKSON_SQUARE)
    assert not STRICT_PD.match(cleared["license"])


def test_without_a_page_the_metadata_answer_is_unchanged():
    for args in (("CC BY-SA 4.0", "Ann Lee", "https://creativecommons.org/licenses/by-sa/4.0"),
                 ("Public domain", "Clark Mills", "")):
        cleared, reason = CI.clear_licence(ii(*args))
        assert reason == "" and (cleared["license"], cleared["author"]) == args[:2]
    assert CI.clear_licence(ii("CC BY-NC-SA 2.0", "x"))[1] == "refused_terms:CC BY-NC-SA 2.0"
    assert CI.clear_licence(ii("CC BY 2.0", ""))[1] == "attribution_unreadable:CC BY 2.0"


def test_every_other_page_keeps_the_metadata_answer():
    """A dual licence by one holder, the 2009 migration, a faithful copy of
    a painting ({{PD-Art}}), an old photograph, a government work, a single
    licence, a user's own template: no change."""
    cases = [
        page("{{self|cc-by-sa-3.0|GFDL}}"),
        page("{{Self|GFDL|Cc-by-sa-2.5,2.0,1.0|migration=relicense|author=Billy Hathorn}}"),
        page("{{self|GFDL|cc-by-sa-all|migration=redundant}}"),
        page("{{PD-Art|PD-old-100}}", "{{Artwork|artist={{Creator:Old Painter}}|source=Museum}}"),
        page("{{PD-old-70}}\n{{PD-US-expired}}", "{{Photograph|photographer=Unknown}}"),
        page("{{PD-USGov-Interior-NPS}}"),
        page("{{cc-by-2.0}}\n{{Flickrreview|Bob|2020-01-01}}"),
        page("{{User:Michael Barera/license}}"),
    ]
    for p in cases:
        assert CP.photograph_credit(p) is None, p
        meta = ii("CC BY-SA 3.0", "Someone")
        assert CI.clear_licence(meta, page=p) == CI.clear_licence(meta), p


def test_the_photographs_licence_must_itself_be_on_the_list():
    for section, want in (("{{PD-old}}\n{{self|GFDL}}", "GFDL"),
                          ("{{PD-old}}\n{{cc-by-nc-sa-2.0}}", "cc-by-nc-sa-2.0")):
        cleared, reason = CI.clear_licence(ii("Public domain", "A Sculptor"), page=page(section))
        assert cleared is None and reason == f"photo_licence_not_cleared:{want}"
    # a GFDL photograph under the 2009 migration also grants CC BY-SA 3.0
    cleared, _ = CI.clear_licence(ii("Public domain", "A Sculptor"),
                                  page=page("{{PD-old}}\n{{self|GFDL|migration=relicense}}"))
    assert (cleared["license"], cleared["author"]) == ("CC BY-SA 3.0", "Snap Shot")


def test_the_other_ways_a_page_names_the_photographs_licence():
    art_photo = ("{{Art Photo|artist={{Creator:X}}|photographer=[[User:Yy|Yolanda Zed]]"
                 "|artwork license={{PD-old-100}}|photo license={{self|cc-by-sa-4.0}}}}")
    cleared, _ = CI.clear_licence(ii("Public domain", "X"), page=page("", art_photo))
    assert (cleared["license"], cleared["author"]) == ("CC BY-SA 4.0", "Yolanda Zed")
    licensed = page("{{Licensed-PD-Art|PD-old-auto|cc-by-sa-4.0|deathyear=1900}}",
                    "{{Artwork|artist={{Creator:Old Painter}}|author=[[User:Snap|Snap Shot]]}}")
    cleared, _ = CI.clear_licence(ii("Public domain", "Old Painter"), page=licensed)
    assert (cleared["license"], cleared["author"]) == ("CC BY-SA 4.0", "Snap Shot")
    # an artwork page whose photograph carries its own licence alone: the
    # licence stands, the author is the photographer, not the architect
    building = page("{{self|cc-by-sa-4.0}}", "{{Artwork|artist={{Creator:An Architect}}"
                                            "|author=[[User:Snap|Snap Shot]]}}")
    cleared, _ = CI.clear_licence(ii("CC BY-SA 4.0", "An Architect"), page=building)
    assert (cleared["license"], cleared["author"]) == ("CC BY-SA 4.0", "Snap Shot")


def test_with_no_photographer_named_the_uploader_is_the_holder():
    p = page("{{PD-old}}\n{{self|cc-by-sa-4.0}}", "{{Artwork|artist={{Creator:X}}|source={{own}}}}")
    cleared, _ = CI.clear_licence(ii("Public domain", "X"), page=p, uploader=lambda: "Upl Oader")
    assert (cleared["license"], cleared["author"]) == ("CC BY-SA 4.0", "Upl Oader")
    cleared, reason = CI.clear_licence(ii("Public domain", "X"), page=p, uploader=lambda: None)
    assert cleared is None and reason == "attribution_unreadable:CC BY-SA 4.0"


def test_an_old_works_tag_beside_a_users_own_template_refuses():
    cleared, reason = CI.clear_licence(ii("Public domain", "A Sculptor"),
                                       page=page("{{PD-old}}\n{{User:Someone/License}}"))
    assert cleared is None and reason.startswith("photo_licence_unreadable:")


def test_clear_file_reads_the_page_and_refuses_one_it_cannot_read(monkeypatch):
    monkeypatch.setattr(CI, "file_page", lambda name: JACKSON_SQUARE if name == "Jackson_Square.jpg" else None)
    monkeypatch.setattr(CI, "uploader_of", lambda name: "never asked")
    cleared, _ = CI.clear_file("Jackson_Square.jpg", ii("Public domain", "Clark Mills"))
    assert (cleared["license"], cleared["author"]) == ("CC BY-SA 4.0", "Daniel Schwen")
    assert CI.clear_file("Other.jpg", ii("CC BY 4.0", "A")) == (None, "no_readable_page")


def test_licence_names_read_as_commons_writes_them():
    assert CP.norm_licence("cc-by-sa-all") == [f"cc-by-sa-{v}" for v in ("4.0", "3.0", "2.5", "2.0", "1.0")]
    assert CP.norm_licence("Cc-by-sa-3.0-migrated") == ["cc-by-sa-3.0"]
    assert CP.norm_licence("CC BY 3.0 us") == ["cc-by-3.0-us"]
    assert CP.display_licence("cc-by-3.0-us") == "CC BY 3.0 us"
    assert CP.strip_markup("{{user at project|Justin65656|wikipedia|en}}") == "Justin65656"
