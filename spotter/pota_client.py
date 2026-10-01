"""Worker thread: poll the POTA.app spots API every 60 s; raw records on the queue.

On any failure (timeout, HTTP error, bad JSON) it puts a Status('pota','error') and no spots,
so the store keeps its old spots and the poll age keeps growing from the last success.
"""
import logging
import threading
import time

import requests

from .models import RawRecords, Status

log = logging.getLogger("pota_client")

URL = "https://api.pota.app/spot/activator"


class PotaClient:
    def __init__(self, out, url=URL, interval=60.0, timeout=10.0, get=requests.get, clock=time.monotonic):
        self.out, self.url, self.interval, self.timeout, self._get = out, url, interval, timeout, get
        self._clock = clock
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="pota_client", daemon=True)
        self.poll_times = []  # monotonic start of each request, for the timing check

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(self.timeout + 1)

    def poll_once(self):
        self.poll_times.append(self._clock())
        try:
            r = self._get(self.url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                raise ValueError("response is not a list")
        except Exception as e:
            log.warning("POTA poll failed: %r", e)
            self.out.put(Status("pota", "error", 0, repr(e)))
            return False
        self.out.put(RawRecords(data, time.time()))
        self.out.put(Status("pota", "ok"))
        return True

    def _run(self):
        # fixed schedule (start + k * interval) so request spacing does not drift with request time
        t = self._clock()
        while not self._stop.is_set():
            self.poll_once()
            t += self.interval
            if self._stop.wait(max(0.0, t - self._clock())):
                break
