"""Phase 4 Stage 3 (ADR 0012, Nathan's decisions): each source's verdict is
typed in the licence registry -- shippable, the exact citation strings,
the notice its terms require, the conditions -- and the build refuses a
served feature that traces to a source that is unshippable or uncited."""
import re

import pytest

from atlas.pipeline.adapters.base import CENSUS_API_NOTICE, GEOGRAPHY_SOURCES, LICENSES
from atlas.pipeline.build.cube import SERVED_STATUSES
from atlas.pipeline.contracts.provenance import (LicenseTerms, Provenance,
                                                 assert_all_shippable,
                                                 assert_credited_shippable)
from atlas.pipeline.registry.loader import load_registry

CENSUS = ("census_acs", "census_dhc", "census_geo", "census_cbp")


def _prov(source: str) -> Provenance:
    return Provenance(source, "d", "t", ("v",), "cbsa", "2024", "x", "measured")


def test_every_shippable_source_carries_a_citation():
    for sid, lic in LICENSES.items():
        if lic.shippable:
            assert lic.citations, sid
            assert all(c.strip() == c and c.endswith(".") for c in lic.citations), sid


def test_census_citations_are_the_decided_form_with_the_api_notice():
    form = re.compile(r"^Source: U\.S\. Census Bureau, [^;]+; estimates by Dating Stats Atlas\.$")
    assert CENSUS_API_NOTICE == ("This product uses the Census Bureau Data API but is not "
                                 "endorsed or certified by the Census Bureau.")
    for sid in CENSUS:
        lic = LICENSES[sid]
        assert all(form.match(c) for c in lic.citations), lic.citations
        assert lic.notice == CENSUS_API_NOTICE


def test_only_census_sources_carry_the_census_notice():
    for sid, lic in LICENSES.items():
        if sid not in CENSUS:
            assert lic.notice is None, sid


def test_hud_is_cited_alone_from_its_bulk_files():
    lic = LICENSES["hud_fmr50"]
    assert lic.citations == ("Source: U.S. Department of Housing and Urban Development, "
                             "FY2027 50th Percentile Rent Estimates.",)
    assert any("bulk files" in c for c in lic.conditions)


@pytest.mark.parametrize("sid,needle", [
    ("ghcn_daily", "NOAA National Centers for Environmental Information"),
    ("epa_sld", "U.S. Environmental Protection Agency"),
    ("bea_rpp", "U.S. Bureau of Economic Analysis"),
    ("ipeds", "Integrated Postsecondary Education Data System (IPEDS)"),
    ("omb_delineation", "Office of Management and Budget Bulletin No. 23-01"),
    ("fbi_cde", "Federal Bureau of Investigation"),
])
def test_each_federal_source_is_cited_by_name(sid, needle):
    assert any(needle in c for c in LICENSES[sid].citations)


def test_pew_is_never_cited_and_never_shippable():
    lic = LICENSES["pew_intermarriage"]
    assert lic.shippable is False and lic.citations == ()
    assert {"build-time only", "never published", "never compared in public"} <= set(lic.conditions)


def test_every_served_feature_traces_to_a_shippable_cited_source():
    reg = load_registry()
    served = {f.id: _prov(f.provenance["source"]) for f in reg.features.values()
              if f.status in SERVED_STATUSES}
    assert served
    assert_all_shippable(served, LICENSES)
    assert_credited_shippable(list(GEOGRAPHY_SOURCES), LICENSES)


def test_a_served_feature_on_an_unshippable_source_fails_the_build():
    with pytest.raises(AssertionError, match="non-shippable"):
        assert_all_shippable({"violent_crime_rate": _prov("pew_intermarriage")}, LICENSES)


def test_a_served_feature_on_an_uncited_source_fails_the_build():
    uncited = LicenseTerms(name="n", url="u", shippable=True)
    with pytest.raises(AssertionError, match="no citation"):
        assert_all_shippable({"x": _prov("new_source")}, LICENSES | {"new_source": uncited})


def test_an_uncited_geography_source_fails_the_build():
    uncited = LicenseTerms(name="n", url="u", shippable=True)
    with pytest.raises(AssertionError, match="not shippable or not cited"):
        assert_credited_shippable(["census_geo"], LICENSES | {"census_geo": uncited})
