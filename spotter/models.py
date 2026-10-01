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


@dataclass(frozen=True)
class RawLine:
    """A raw cluster line, straight from the socket (never parsed by the client)."""
    text: str


@dataclass(frozen=True)
class RawRecords:
    """A raw POTA response list; ts is time.time() of the successful poll."""
    records: list
    ts: float


@dataclass(frozen=True)
class Status:
    """A status item. source: 'cluster' or 'pota'. state: connected, connecting, disconnected
    (cluster dot: green, amber, red) or ok, error (pota). retry: attempts since last success."""
    source: str
    state: str
    retry: int = 0
    detail: str = ""
