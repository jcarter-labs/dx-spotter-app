"""Decides whether a spot is kept and drawn. Pure functions, no Tk."""
import re

from .models import Spot

LOCAL = ("W6YX", "AK6RI-1", "N6TV")
REGIONAL = ("K6FOD", "WA7LNW", "ND7K", "K7CO", "NG7M", "N7VVX", "N7TUG", "KD7EFG", "KW7MM", "KW7MM-2")
SKIMMER_LISTS = {"Local": LOCAL, "Regional": REGIONAL}
ALL_SKIMMERS = LOCAL + REGIONAL  # the store keeps spots from both lists; the choice applies at draw time


def skimmer_matches(skimmer: str | None, entries) -> bool:
    """The skimmer equals an entry, optionally followed by a trailing ``-<digits>`` and/or ``-#``.

    AK6RI-1 matches AK6RI-1-# and AK6RI-1-2, not AK6RI-10 or AK6RI. W6YX matches W6YX,
    W6YX-#, W6YX-2 and the live form W6YX-2-#.
    """
    if not skimmer:
        return False
    return any(re.fullmatch(re.escape(e) + r"(?:-\d+)?(?:-#)?", skimmer) for e in entries)


def is_cw(spot: Spot) -> bool:
    return spot.mode == "CW"  # client-side check is authoritative


def keep_rbn(spot: Spot, entries) -> bool:
    return is_cw(spot) and skimmer_matches(spot.skimmer, entries)


def keep_pota(spot: Spot) -> bool:
    return is_cw(spot) and spot.freq_mhz > 0


def in_span(freq_mhz: float, centre_mhz: float, bandwidth_khz: float) -> bool:
    half = bandwidth_khz / 2000.0
    eps = 1e-9
    return centre_mhz - half - eps <= freq_mhz <= centre_mhz + half + eps
