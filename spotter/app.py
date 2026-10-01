"""Application logic, no Tk and no sockets.

`drain()` empties the queue, runs the parsers, filter and store, and applies status items.
`view()` says what `ui` should draw. Operator actions (frequency, bandwidth, fade, spotter,
clear) go through the methods here; the cluster client is reached only through two hooks.
"""
import logging
import queue
import time
from dataclasses import dataclass, field

from . import spot_filter
from .cluster_parse import parse_line
from .models import RawLine, RawRecords, Reject, Spot, Status
from .pota_parse import parse_record
from .settings import Settings, band_of
from .spot_store import SpotStore

log = logging.getLogger("app")

DOT = {"connected": "green", "connecting": "amber", "disconnected": "red"}


@dataclass
class DrawSpot:
    call: str
    freq_mhz: float
    opacity: float


@dataclass
class View:
    rbn: list = field(default_factory=list)
    pota: list = field(default_factory=list)
    lo: float = 0.0
    hi: float = 0.0
    dot: str = "amber"
    cluster_text: str = ""
    pota_text: str = ""
    shown_text: str = ""
    warning: str = ""


class App:
    def __init__(self, q: "queue.Queue", settings: Settings | None = None, clock=time.time,
                 send_band=lambda band: None, reconnect=lambda: None):
        self.q = q
        self.settings = settings or Settings()
        self.clock = clock
        self.store = SpotStore(clock)
        self._send_band, self._reconnect = send_band, reconnect
        self.filter_band = band_of(self.settings.frequency)  # band the server filter asks for
        self.cluster_state, self.retry = "connecting", 0
        self.pota_last = None
        self.rejected = 0
        self.warning = ""
        self.warning_prefix = "Frequency is outside"

    # --- queue
    def drain(self) -> None:
        while True:
            try:
                item = self.q.get_nowait()
            except queue.Empty:
                return
            if isinstance(item, RawLine):
                self._rbn_line(item.text)
            elif isinstance(item, RawRecords):
                self._pota_records(item)
            elif isinstance(item, Status):
                self._status(item)

    def _rbn_line(self, text):
        s = parse_line(text)
        if isinstance(s, Reject):
            self._reject(s)
            return
        if band_of(s.freq_mhz) != self.filter_band:
            return  # a spot from a band we no longer ask for (arrived around a band change)
        if spot_filter.keep_rbn(s, spot_filter.ALL_SKIMMERS):
            self.store.add("rbn", s)

    def _pota_records(self, item):
        self.pota_last = item.ts
        for rec in item.records:
            s = parse_record(rec)
            if isinstance(s, Reject):
                self._reject(s)
            elif spot_filter.keep_pota(s):
                self.store.add("pota", s)

    def _status(self, st: Status):
        if st.source == "cluster":
            self.cluster_state, self.retry = st.state, st.retry
        # a POTA failure changes nothing: old spots stay and the poll age keeps counting

    def _reject(self, r: Reject):
        self.rejected += 1
        log.warning("rejected (%s): %r", r.reason, r.raw)

    # --- operator actions
    def set_frequency(self, text) -> tuple[bool, str]:
        ok, msg = self.settings.set_frequency(text)
        self.warning = ""
        if not ok:
            return ok, msg
        band = band_of(self.settings.frequency)
        if band is None:
            self.warning = "Frequency is outside the HF amateur bands: keeping the last server filter"
        elif band != self.filter_band:
            self.filter_band = band
            self.store.clear("rbn")
            self._send_band(band)
        return True, ""

    def set_bandwidth(self, v):
        return self.settings.set_bandwidth(v)

    def set_fade(self, v):
        return self.settings.set_fade(v)  # applies to all existing spots at the next view

    def set_spotter(self, v) -> tuple[bool, str]:
        return self.settings.set_spotter(v)  # applies at draw time; the store is untouched

    def clear(self) -> None:
        self.store.clear()
        self.cluster_state = "connecting"  # forced reconnect: amber, not a retry
        self._reconnect()

    # --- what to draw
    def view(self) -> View:
        s = self.settings
        lo, hi = s.span
        v = View(lo=lo, hi=hi, warning=self.warning)
        for scale, out in (("rbn", v.rbn), ("pota", v.pota)):
            for sp, op in self.store.items(scale, s.fade):
                if scale == "rbn" and not spot_filter.skimmer_matches(sp.skimmer, spot_filter.SKIMMER_LISTS[s.spotter]):
                    continue
                if spot_filter.in_span(sp.freq_mhz, s.frequency, s.bandwidth):
                    out.append(DrawSpot(sp.call, sp.freq_mhz, op))
        v.dot = DOT.get(self.cluster_state, "amber")
        v.cluster_text = f"Cluster: {s.server}" + (f" (retry {self.retry})" if self.retry > 0 else "")
        v.pota_text = ("POTA: not polled yet" if self.pota_last is None
                       else f"POTA: last poll {max(0, int(self.clock() - self.pota_last))}s ago")
        v.shown_text = f"Shown: RBN {len(v.rbn)} · POTA {len(v.pota)}"
        return v
