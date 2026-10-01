from spotter.models import Spot
from spotter.spot_filter import (LOCAL, REGIONAL, in_span, is_cw, keep_pota, keep_rbn,
                                 skimmer_matches)


def sp(skimmer="WA7LNW-#", mode="CW", f=14.02):
    return Spot(f, "K1ABC", mode, skimmer)


def test_skimmer_match_rules():
    e = ("AK6RI-1",)
    assert skimmer_matches("AK6RI-1-#", e) and skimmer_matches("AK6RI-1-2", e) and skimmer_matches("AK6RI-1", e)
    assert not skimmer_matches("AK6RI-10", e) and not skimmer_matches("AK6RI", e)
    assert not skimmer_matches("AK6RI-1-x", e)
    w = ("W6YX",)
    assert all(skimmer_matches(s, w) for s in ("W6YX", "W6YX-#", "W6YX-2", "W6YX-2-#"))
    assert not skimmer_matches("W6YXX-#", w) and not skimmer_matches("XW6YX", w) and not skimmer_matches(None, w)
    assert skimmer_matches("KW7MM-2-#", REGIONAL) and skimmer_matches("KW7MM-#", REGIONAL)


def test_lists_match_masterplan():
    assert LOCAL == ("W6YX", "AK6RI-1", "N6TV")
    assert len(REGIONAL) == 10 and "KW7MM-2" in REGIONAL


def test_rbn_keep_cases():
    assert keep_rbn(sp(), REGIONAL)                      # matching suffix, CW
    assert not keep_rbn(sp("AK6RI-10-#"), LOCAL)         # non-matching suffix
    assert not keep_rbn(sp("WA7LNW-#"), LOCAL)           # skimmer not in the selected list
    assert not keep_rbn(sp(mode="RTTY"), REGIONAL)       # non-CW
    assert not keep_rbn(sp("KF6IWW", mode=""), REGIONAL) # human spot, no mode


def test_pota_keep():
    assert keep_pota(Spot(14.03, "K1ABC", "CW"))
    assert not keep_pota(Spot(14.03, "K1ABC", "SSB"))
    assert not keep_pota(Spot(0.0, "K1ABC", "CW"))


def test_span():
    assert in_span(14.020, 14.045, 50) and in_span(14.070, 14.045, 50) and in_span(14.045, 14.045, 50)
    assert not in_span(14.0199, 14.045, 50) and not in_span(14.0701, 14.045, 50)
    assert in_span(14.025, 14.045, 10) is False and in_span(14.040, 14.045, 10)


def test_regional_is_superset_of_local():
    from spotter.spot_filter import SKIMMER_LISTS
    assert set(LOCAL) < set(SKIMMER_LISTS["Regional"]) and set(REGIONAL) < set(SKIMMER_LISTS["Regional"])
    assert SKIMMER_LISTS["Local"] == LOCAL
