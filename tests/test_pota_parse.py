import json
from pathlib import Path

from spotter.models import Reject, Spot
from spotter.pota_parse import parse_record

RAW = json.loads((Path(__file__).resolve().parent.parent / "captures" / "pota_spots_raw.json").read_text())


def test_accepted_plus_rejected_equals_read():
    res = [parse_record(r) for r in RAW]
    acc = [r for r in res if isinstance(r, Spot)]
    rej = [r for r in res if isinstance(r, Reject)]
    assert len(acc) + len(rej) == len(RAW) == 59
    assert len(acc) == 59  # live capture has no bad records
    assert sum(1 for s in acc if s.mode == "CW") == 10


def test_first_record_fields():
    s = parse_record(RAW[0])
    assert (s.call, s.mode) == ("W4LAW", "FT8")
    assert abs(s.freq_mhz - 14.07563) < 1e-9


def test_rejects():
    for bad, why in [(None, "not an object"), ({}, "no call"), ({"activator": "K1ABC"}, "no frequency"),
                     ({"activator": "K1ABC", "frequency": ""}, "no frequency"),
                     ({"activator": "K1ABC", "frequency": "abc"}, "bad frequency"),
                     ({"activator": "K1ABC", "frequency": "nan"}, "bad frequency"),
                     ({"activator": "K1ABC", "frequency": "-5"}, "bad frequency")]:
        r = parse_record(bad)
        assert isinstance(r, Reject) and r.reason == why


def test_missing_mode_accepted_as_blank_and_suffix_kept():
    s = parse_record({"activator": "K1ABC/P", "frequency": 7030, "mode": None})
    assert s.call == "K1ABC/P" and s.mode == "" and s.freq_mhz == 7.03
