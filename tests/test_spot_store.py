from spotter.models import Spot
from spotter.spot_store import SpotStore, opacity


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


def mk():
    c = Clock(); return c, SpotStore(c)


def test_opacity_curve():
    f = 600.0
    assert opacity(0, f) == 1.0
    assert opacity(f / 2, f) == pytest_approx(0.575)
    assert abs(opacity(f - 0.001, f) - 0.15) < 1e-4
    assert opacity(f * 2, f) == pytest_approx(0.15)
    assert opacity(100, f) < opacity(10, f)


def pytest_approx(x):
    import pytest; return pytest.approx(x)


def test_age_from_receipt_and_drop_at_fade_time():
    c, st = mk()
    st.add("rbn", Spot(14.03, "K1ABC", "CW", "W6YX"))
    assert st.items("rbn", 10)[0][1] == 1.0
    c.t += 599.9
    assert len(st.items("rbn", 10)) == 1 and abs(st.items("rbn", 10)[0][1] - 0.15) < 1e-3
    c.t += 0.1                                      # age == fade time: dropped
    assert st.items("rbn", 10) == [] and st.count("rbn") == 0


def test_fade_setting_applies_to_existing_spots():
    c, st = mk()
    st.add("rbn", Spot(14.03, "K1ABC", "CW"))
    c.t += 400
    assert len(st.items("rbn", 10)) == 1
    assert st.items("rbn", 5) == []                 # shortened to 5 min: gone at once


def test_one_label_per_call_per_scale_newer_wins():
    c, st = mk()
    st.add("rbn", Spot(14.030, "K1ABC", "CW"))
    c.t += 100
    st.add("rbn", Spot(14.040, "k1abc", "CW"))
    got = st.items("rbn", 10)
    assert len(got) == 1 and got[0][0].freq_mhz == 14.040 and got[0][1] == 1.0   # age reset
    st.add("pota", Spot(14.050, "K1ABC", "CW"))     # other scale keeps its own
    assert st.count("rbn") == 1 and st.count("pota") == 1


def test_same_pota_report_keeps_age_new_report_resets():
    c, st = mk()
    st.add("pota", Spot(14.05, "K1ABC", "CW", spot_id="1"))
    c.t += 300
    st.add("pota", Spot(14.05, "K1ABC", "CW", spot_id="1"))   # next poll, same report
    assert st.items("pota", 10)[0][1] < 1.0
    st.add("pota", Spot(14.05, "K1ABC", "CW", spot_id="2"))   # re-spotted
    assert st.items("pota", 10)[0][1] == 1.0


def test_clear():
    c, st = mk()
    st.add("rbn", Spot(14.03, "A1A", "CW")); st.add("pota", Spot(14.03, "B1B", "CW"))
    st.clear("rbn"); assert (st.count("rbn"), st.count("pota")) == (0, 1)
    st.add("rbn", Spot(14.03, "A1A", "CW")); st.clear(); assert (st.count("rbn"), st.count("pota")) == (0, 0)
    st.add("rbn", Spot(14.03, "C1C", "CW")); assert st.count("rbn") == 1   # new spots continue
