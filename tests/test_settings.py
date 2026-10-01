import pytest

from spotter.settings import Settings, band_of


def test_defaults_and_span():
    s = Settings()
    assert (s.frequency, s.bandwidth, s.fade, s.spotter, s.server) == (14.045, 50, 10, "Regional", "NC7J")
    lo, hi = s.span
    assert abs(lo - 14.020) < 1e-9 and abs(hi - 14.070) < 1e-9


@pytest.mark.parametrize("v", ["1.8", "30", "14.1", " 7.030 "])
def test_frequency_accepted(v):
    s = Settings(); assert s.set_frequency(v)[0] and s.frequency == float(v)


@pytest.mark.parametrize("v", ["1.79", "30.01", "abc", "", "nan", "inf", "14,045", "-5"])
def test_frequency_rejected_keeps_old(v):
    s = Settings(); ok, msg = s.set_frequency(v)
    assert not ok and msg and s.frequency == 14.045


def test_bandwidth_menu():
    s = Settings()
    for b in (10, 20, 40, 50, 80, 100):
        assert s.set_bandwidth(b)[0] and s.bandwidth == b
    for b in (30, "x", 0, 101):
        old = s.bandwidth; assert not s.set_bandwidth(b)[0] and s.bandwidth == old


def test_fade_menu_and_spotter():
    s = Settings()
    for f in (5, 10, 15): assert s.set_fade(f)[0] and s.fade == f
    for f in (0, 7, "x", 20): assert not s.set_fade(f)[0] and s.fade == 15
    assert s.set_spotter("Local")[0] and s.spotter == "Local"
    assert not s.set_spotter("Both")[0] and s.spotter == "Local"


def test_band_of_edges_and_gaps():
    assert band_of(14.045) == 20 and band_of(14.000) == 20 and band_of(14.350) == 20
    assert band_of(7.0) == 40 and band_of(7.3) == 40 and band_of(1.8) == 160 and band_of(29.7) == 10
    assert band_of(5.35) is None and band_of(14.351) is None and band_of(13.999) is None and band_of(3.0) is None


def test_band_table_matches_us_part_97_edges_confirmed_by_operator():
    from spotter.settings import HF_BANDS
    assert HF_BANDS == {160: (1.8, 2.0), 80: (3.5, 4.0), 40: (7.0, 7.3), 30: (10.1, 10.15), 20: (14.0, 14.35),
                        17: (18.068, 18.168), 15: (21.0, 21.45), 12: (24.89, 24.99), 10: (28.0, 29.7)}
