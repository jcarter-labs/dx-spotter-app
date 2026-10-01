"""Operator settings with validation: a bad entry is rejected and the old value kept."""
import math

BANDWIDTHS = (10, 20, 40, 50, 80, 100)
FADE_TIMES = (5, 10, 15)
SPOTTERS = ("Local", "Regional")
FREQ_MIN, FREQ_MAX = 1.8, 30.0

# Standard US amateur HF bands, edges inclusive, MHz (masterplan Tech table).
HF_BANDS = {160: (1.800, 2.000), 80: (3.500, 4.000), 40: (7.000, 7.300), 30: (10.100, 10.150),
            20: (14.000, 14.350), 17: (18.068, 18.168), 15: (21.000, 21.450),
            12: (24.890, 24.990), 10: (28.000, 29.700)}


def band_of(freq_mhz: float):
    """Band in metres containing the frequency, or None (gaps and 60 m count as outside)."""
    for m, (lo, hi) in HF_BANDS.items():
        if lo - 1e-9 <= freq_mhz <= hi + 1e-9:
            return m
    return None


class Settings:
    def __init__(self):
        self.frequency = 14.045
        self.bandwidth = 50
        self.fade = 10
        self.spotter = "Regional"
        self.server = "NC7J"

    def set_frequency(self, text) -> tuple[bool, str]:
        try:
            f = float(str(text).strip())
        except ValueError:
            return False, "Frequency must be a number in MHz"
        if not math.isfinite(f) or not FREQ_MIN <= f <= FREQ_MAX:
            return False, f"Frequency must be {FREQ_MIN} to {FREQ_MAX:g} MHz"
        self.frequency = f
        return True, ""

    def set_bandwidth(self, value) -> tuple[bool, str]:
        try:
            v = int(str(value).strip())
        except ValueError:
            return False, "Bad bandwidth"
        if v not in BANDWIDTHS:
            return False, f"Bandwidth must be one of {BANDWIDTHS}"
        self.bandwidth = v
        return True, ""

    def set_fade(self, value) -> tuple[bool, str]:
        try:
            v = int(str(value).strip())
        except ValueError:
            return False, "Bad fade time"
        if v not in FADE_TIMES:
            return False, f"Fade time must be one of {FADE_TIMES}"
        self.fade = v
        return True, ""

    def set_spotter(self, value) -> tuple[bool, str]:
        if value not in SPOTTERS:
            return False, f"Spotter must be one of {SPOTTERS}"
        self.spotter = value
        return True, ""

    @property
    def span(self) -> tuple[float, float]:
        half = self.bandwidth / 2000.0
        return self.frequency - half, self.frequency + half
