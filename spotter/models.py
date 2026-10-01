from dataclasses import dataclass


@dataclass(frozen=True)
class Spot:
    freq_mhz: float
    call: str
    mode: str
    skimmer: str | None = None


@dataclass(frozen=True)
class Reject:
    reason: str
    raw: object = None
