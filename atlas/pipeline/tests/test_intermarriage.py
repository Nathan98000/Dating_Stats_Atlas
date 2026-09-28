"""Phase 4 Stage 4 (ADR 0016): the intermarriage check from Census PUMS,
which replaced Pew's table in every check and report."""
import json

import pandas as pd
import pytest

from atlas.pipeline.build import intermarriage_pums as I
from atlas.pipeline.build.validate import check_intermarriage


def test_pews_scheme_is_race8_with_asian_and_pacific_islander_merged():
    assert set(I.PEW7) == {"hispanic", "nh_white", "nh_black", "nh_asian", "nh_nhpi",
                           "nh_aian", "nh_twoplus", "nh_other"}
    assert I.PEW7["nh_asian"] == I.PEW7["nh_nhpi"] == "asian"
    assert len(set(I.PEW7.values())) == 7


@pytest.mark.skipif(not I.RATES_CSV.exists(), reason="the rates are computed on the build machine")
def test_the_committed_rates_are_whole_and_carry_their_margins():
    df = pd.read_csv(I.RATES_CSV, dtype={"cbsa": str})
    rec = json.loads(I.RATES_JSON.read_text())
    assert rec["join"]["field_mismatch"] == 0
    assert df["rate"].between(0, 1).all() and (df["moe90"] >= 0).all()
    assert (df["meets_floor"] == (df["n_alloc"] >= I.FLOOR)).all()
    assert int(df["meets_floor"].sum()) == rec["metros_meeting_floor"]
    ref = I.reference(sorted(df["cbsa"]))
    assert len(ref) == rec["metros_meeting_floor"]
    assert list(ref.columns) == ["msa_code", "metro_name", "ref_rate"]
    assert 0 < I.reference_national() < 1


@pytest.mark.skipif(not I.CHECK_JSON.exists(), reason="the check runs on the build machine")
def test_validate_reads_the_pums_check_as_its_soft_intermarriage_reading():
    out = check_intermarriage()
    assert out["metros"] == json.loads(I.CHECK_JSON.read_text())["comparison"]["metros_matched"]
    assert set(out["median_abs_pts"]) == {"national_only", "raw_dial", "shrunk_dial"}


@pytest.mark.skipif(not I.AGREEMENT_JSON.exists(), reason="the one Pew reading is on record")
def test_the_one_pew_reading_holds_aggregates_only():
    rec = json.loads(I.AGREEMENT_JSON.read_text())
    for block in ("all_matched_metros", "matched_and_meeting_floor"):
        assert set(rec[block]) == {"metros", "pearson_r", "median_abs_difference_pts"}
