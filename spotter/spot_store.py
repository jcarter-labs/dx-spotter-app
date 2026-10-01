"""Spots with age (from receipt), opacity, one spot per call per scale, counts, Clear."""
import time

from .models import Spot

MIN_OPACITY = 0.15


def opacity(age_s: float, fade_s: float) -> float:
    """1.0 when new, linear to 0.15 at the fade time; never below 0.15."""
    if age_s <= 0:
        return 1.0
    return max(MIN_OPACITY, 1.0 - (1.0 - MIN_OPACITY) * min(age_s / fade_s, 1.0))


class SpotStore:
    def __init__(self, clock=time.time):
        self._clock = clock
        self._spots = {"rbn": {}, "pota": {}}  # scale -> call key -> (received_at, Spot)

    def add(self, scale: str, spot: Spot) -> None:
        key = spot.call.upper()
        old = self._spots[scale].get(key)
        if old and spot.spot_id is not None and old[1].spot_id == spot.spot_id:
            return  # the same POTA report seen again on a later poll: keep its age
        self._spots[scale][key] = (self._clock(), spot)

    def purge(self, fade_min: float) -> None:
        now, fade_s = self._clock(), fade_min * 60.0
        for d in self._spots.values():
            for k in [k for k, (t, _) in d.items() if now - t >= fade_s]:
                del d[k]

    def items(self, scale: str, fade_min: float) -> list[tuple[Spot, float]]:
        """Current spots as (spot, opacity); drops those at age >= fade time first."""
        self.purge(fade_min)
        now, fade_s = self._clock(), fade_min * 60.0
        return [(s, opacity(now - t, fade_s)) for t, s in self._spots[scale].values()]

    def count(self, scale: str) -> int:
        return len(self._spots[scale])

    def clear(self, scale: str | None = None) -> None:
        for k in ([scale] if scale else list(self._spots)):
            self._spots[k].clear()
