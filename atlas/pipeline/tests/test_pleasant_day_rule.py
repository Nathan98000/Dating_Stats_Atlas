"""Phase 4e: Nathan's nice-day rule (m4.2.0), criterion by criterion.

A day counts when it meets all six: an average temperature, (TMAX + TMIN) / 2,
between 55 and 75°F inclusive; a high below 85°F; a low above 45°F; at most
0.1 in of rain; no measurable snowfall; snow on the ground under 1 in. A day
with no SNOW or SNWD reading is snow-free. Every threshold is the
registry's (pleasant_day), read through the loader."""
import numpy as np
import pandas as pd
import pytest

from atlas.pipeline.adapters.ghcn_daily import GhcnDailyAdapter, nice_day_parts
from atlas.pipeline.registry.loader import PLEASANT_DAY_KEYS, _pleasant_day_block, load_registry

RULE = load_registry().pleasant_day
NAN = np.nan


def nice(tmax, tmin, prcp=0.0, snow=0.0, snwd=0.0, rule=RULE) -> bool:
    s = lambda v: pd.Series([v], dtype=float)  # noqa: E731
    return bool(nice_day_parts(s(tmax), s(tmin), s(prcp), s(snow), s(snwd), rule)["nice"].iloc[0])


def test_the_registry_holds_nathans_six_thresholds():
    assert RULE == {"tavg_f": [55.0, 75.0], "tmax_below_f": 85.0, "tmin_above_f": 45.0,
                    "prcp_max_in": 0.1, "snow_max_in": 0.0, "snwd_max_in": 1.0}
    adapter = GhcnDailyAdapter()
    assert adapter.rule == RULE
    assert {"SNOW", "SNWD"} <= set(adapter.requested_variables)


def test_a_mild_dry_day_counts():
    assert nice(72, 52)


@pytest.mark.parametrize("tmax,tmin,ok", [
    (64, 46, True),     # average 55.0: the lower bound is inclusive
    (63, 46, False),    # average 54.5
    (84, 66, True),     # average 75.0: the upper bound is inclusive
    (84, 67, False),    # average 75.5
])
def test_the_average_bounds_are_inclusive(tmax, tmin, ok):
    assert nice(tmax, tmin) is ok


def test_the_average_is_the_mean_of_the_high_and_the_low():
    s = lambda v: pd.Series(v, dtype=float)  # noqa: E731
    # the same high, three lows: the mean of the two decides the band
    # (80+46)/2 = 63.0 in; (80+70)/2 = 75.0 in; (80+71)/2 = 75.5 out
    parts = nice_day_parts(s([80, 80, 80]), s([46, 70, 71]), s([0, 0, 0]),
                           s([0, 0, 0]), s([0, 0, 0]), RULE)
    assert parts["tavg"].tolist() == [True, True, False]
    # a cool high with a warm-enough low still averages below 55
    assert not nice(60, 46)             # 53.0
    # the rule reads TMAX and TMIN, never a TAVG column
    assert nice_day_parts.__code__.co_varnames[:6] == ("tmax", "tmin", "prcp", "snow", "snwd", "rule")


@pytest.mark.parametrize("tmax,ok", [(84, True), (84.9, True), (85, False), (86, False)])
def test_the_high_must_be_below_85(tmax, ok):
    # a low of 50 keeps the average inside 55-75 for every high here
    # (84 -> 67, 86 -> 68), so only the high decides
    assert nice(tmax, 50) is ok


@pytest.mark.parametrize("tmin,ok", [(46, True), (45.1, True), (45, False), (44, False)])
def test_the_low_must_be_above_45(tmin, ok):
    # a high of 70 keeps the average inside the band for every low here
    assert nice(70, tmin) is ok


@pytest.mark.parametrize("prcp,ok", [(0.0, True), (0.1, True), (0.11, False), (0.5, False)])
def test_rain_of_at_most_a_light_shower(prcp, ok):
    assert nice(72, 52, prcp=prcp) is ok


@pytest.mark.parametrize("snow,ok", [(0.0, True), (0.1, False), (1.0, False)])
def test_any_measurable_snowfall_fails(snow, ok):
    assert nice(72, 52, snow=snow) is ok


@pytest.mark.parametrize("snwd,ok", [(0.0, True), (0.9, True), (1.0, False), (3.0, False)])
def test_snow_on_the_ground_must_be_under_one_inch(snwd, ok):
    assert nice(72, 52, snwd=snwd) is ok


@pytest.mark.parametrize("snow,snwd", [(NAN, NAN), (NAN, 0.0), (0.0, NAN)])
def test_a_missing_snow_reading_counts_as_snow_free(snow, snwd):
    assert nice(72, 52, snow=snow, snwd=snwd)


def test_a_missing_snow_reading_never_rescues_a_day_another_part_fails():
    assert not nice(72, 52, prcp=0.5, snow=NAN, snwd=NAN)
    assert not nice(72, 52, snow=NAN, snwd=2.0)          # depth reported, too deep
    assert not nice(72, 52, snow=0.5, snwd=NAN)          # snowfall reported


def test_the_rule_follows_the_registry_not_constants():
    looser = {**RULE, "tavg_f": [50.0, 80.0], "snwd_max_in": 5.0}
    assert not nice(62, 46, snwd=2.0)              # average 54: below 55
    assert nice(62, 46, snwd=2.0, rule=looser)     # inside the looser rule


def test_the_loader_refuses_a_partial_or_incoherent_rule():
    full = {"tavg_f": [55, 75], "tmax_below_f": 85, "tmin_above_f": 45,
            "prcp_max_in": 0.1, "snow_max_in": 0, "snwd_max_in": 1}
    assert set(full) == PLEASANT_DAY_KEYS
    _pleasant_day_block(full)
    with pytest.raises(AssertionError):
        _pleasant_day_block({k: v for k, v in full.items() if k != "snwd_max_in"})
    with pytest.raises(AssertionError):
        _pleasant_day_block({**full, "tmax_f": [55, 85]})           # the retired key
    with pytest.raises(AssertionError):
        _pleasant_day_block({**full, "tavg_f": [75, 55]})


def test_a_station_file_without_snow_columns_counts_its_days(tmp_path, monkeypatch):
    """The station path end to end: a file with no SNOW/SNWD columns at all
    (a station that never reports snow) counts its mild dry days, and the
    snow-data tallies read zero."""
    import atlas.pipeline.adapters.ghcn_daily as G
    days = pd.date_range("1991-01-01", "2020-12-31", freq="D")
    df = pd.DataFrame({"DATE": days.strftime("%Y-%m-%d"), "TMAX": 72, "TMIN": 52, "PRCP": 0.0})
    df.loc[days.month == 1, "TMAX"] = 40          # January fails on temperature
    p = tmp_path / "st.csv"
    df.to_csv(p, index=False)
    monkeypatch.setattr(G, "fetch", lambda url: p)
    r = GhcnDailyAdapter().station_pleasant("USW00000000")
    assert r is not None and r["years_used"] == 30
    jan = (days.month == 1).sum()
    assert r["days_counted"] == len(days) - jan
    assert r["days_counted_with_snow_data"] == 0 and r["days_excluded_by_snow"] == 0
    assert r["pleasant_days_no_snow_rule"] == pytest.approx(r["pleasant_days"])
    # with snow columns: a reported snowfall on five mild June days excludes
    # them, and every counted day now has snow data
    df["SNOW"] = 0.0
    df["SNWD"] = np.nan
    june = df.index[(days.month == 6) & (days.year == 2000)][:5]
    df.loc[june, "SNOW"] = 0.5
    df.to_csv(p, index=False)
    r2 = GhcnDailyAdapter().station_pleasant("USW00000000")
    assert r2["days_excluded_by_snow"] == 5
    assert r2["days_counted"] == r["days_counted"] - 5
    assert r2["days_counted_with_snow_data"] == r2["days_counted"]
