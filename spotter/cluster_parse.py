"""One raw cluster line to a Spot or an explicit Reject.

Format (operator's live session): ``DX de WA7LNW-#:  14020.0  XR4T  CW 13 dB 28 WPM CQ  0007Z``
Frequency is in kHz; the mode is the first word after the call.
"""
import math
import re

from .models import Reject, Spot

_LINE = re.compile(r"^DX de (\S+?):\s+(\S+)\s+(\S+)\s+(\S+)(?:\s.*)?$")


def parse_line(line: str) -> Spot | Reject:
    text = line.strip()
    if not text.startswith("DX de "):
        return Reject("not a spot line", line)
    m = _LINE.match(text)
    if not m:
        return Reject("malformed spot line", line)
    skimmer, raw_freq, call, mode = m.groups()
    try:
        khz = float(raw_freq)
    except ValueError:
        return Reject("bad frequency", line)
    if not math.isfinite(khz) or khz <= 0:
        return Reject("bad frequency", line)
    return Spot(freq_mhz=khz / 1000.0, call=call, mode=mode.upper(), skimmer=skimmer)
