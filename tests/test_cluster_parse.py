from pathlib import Path

from spotter.cluster_parse import parse_line
from spotter.models import Reject, Spot

CAPTURE = Path(__file__).resolve().parent / "captures" / "cluster_session.txt"

# From the operator's live session (one real line).
REAL = "DX de WA7LNW-#:  14020.0  XR4T  CW 13 dB 28 WPM CQ  0007Z"
# HAND-MADE lines (marked as such), standing in until the raw capture is saved.
HAND = [
    "DX de AK6RI-1-#:  14033.2  K1ABC/P  CW 22 dB 25 WPM CQ  0010Z",
    "DX de W6YX-2:  14074.0  JA1XYZ  FT8 -5 dB  0011Z",
    "DX de KW7MM-2-#:  14045.5  W1AW  RTTY 18 dB 45 BPS CQ  0012Z",
]
HUMAN = "DX de KF6IWW:    14253.0  N7MES                                       0015Z"  # from the live capture
BAD = ["", "garbage", "DX de :", "DX de W6YX-#:  abc  K1ABC  CW", "DX de W6YX-#:  14020.0", "DX de W6YX-#:  -3  K1ABC  CW"]


def test_real_line():
    s = parse_line(REAL)
    assert isinstance(s, Spot)
    assert (s.call, s.mode, s.skimmer) == ("XR4T", "CW", "WA7LNW-#")
    assert abs(s.freq_mhz - 14.020) < 1e-9


def test_hand_made_lines():
    a, b, c = (parse_line(l) for l in HAND)
    assert (a.call, a.mode, a.skimmer) == ("K1ABC/P", "CW", "AK6RI-1-#")
    assert (b.mode, b.skimmer) == ("FT8", "W6YX-2")
    assert c.mode == "RTTY"


def test_human_spot_has_blank_mode():
    s = parse_line(HUMAN)
    assert (s.call, s.mode, s.skimmer) == ("N7MES", "", "KF6IWW")


def test_rejects():
    for l in BAD:
        assert isinstance(parse_line(l), Reject), l


def test_trailing_newline_ok():
    assert isinstance(parse_line(REAL + "\r\n"), Spot)


def test_saved_capture_accepted_plus_rejected_equals_lines():
    if not CAPTURE.exists():
        import pytest
        pytest.skip("no saved cluster capture yet (step 2.1)")
    lines = [l for l in CAPTURE.read_text(errors="replace").splitlines() if l.startswith("DX de ")]
    res = [parse_line(l) for l in lines]
    assert len(lines) >= 1
    assert sum(isinstance(r, Spot) for r in res) + sum(isinstance(r, Reject) for r in res) == len(lines)
    assert not any(isinstance(r, Reject) for r in res)
    assert len(lines) >= 50
    assert sum(s.mode == "CW" for s in res) == 49 and sum(s.mode == "" for s in res) == 2
