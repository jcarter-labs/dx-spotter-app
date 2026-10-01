"""One raw POTA.app record (dict) to a Spot or an explicit Reject."""
import math

from .models import Reject, Spot


def parse_record(rec) -> Spot | Reject:
    if not isinstance(rec, dict):
        return Reject("not an object", rec)
    call = rec.get("activator")
    if not isinstance(call, str) or not call.strip():
        return Reject("no call", rec)
    raw_freq = rec.get("frequency")
    if raw_freq is None or str(raw_freq).strip() == "":
        return Reject("no frequency", rec)
    try:
        khz = float(raw_freq)
    except (TypeError, ValueError):
        return Reject("bad frequency", rec)
    if not math.isfinite(khz) or khz <= 0:
        return Reject("bad frequency", rec)
    mode = rec.get("mode")
    mode = mode.strip().upper() if isinstance(mode, str) else ""
    return Spot(freq_mhz=khz / 1000.0, call=call.strip(), mode=mode)
