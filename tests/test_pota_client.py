import json
import queue
import time
from pathlib import Path

import requests

from spotter.models import RawRecords, Status
from spotter.pota_client import PotaClient

RAW = json.loads((Path(__file__).resolve().parent / "captures" / "pota_spots_raw.json").read_text())


class Resp:
    def __init__(self, data=None, status=200, bad_json=False):
        self.data, self.status, self.bad_json = data, status, bad_json

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")

    def json(self):
        if self.bad_json:
            raise ValueError("bad json")
        return self.data


def items(q):
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def test_success_puts_records_and_ok_status():
    q = queue.Queue()
    c = PotaClient(q, get=lambda url, timeout: Resp(RAW))
    assert c.poll_once() is True
    recs, st = items(q)
    assert isinstance(recs, RawRecords) and recs.records == RAW and len(recs.records) == 59
    assert st == Status("pota", "ok")


def test_failures_put_error_status_and_no_spots():
    def timeout(url, timeout): raise requests.Timeout("slow")
    for get in (timeout, lambda u, timeout: Resp(status=503), lambda u, timeout: Resp(bad_json=True),
                lambda u, timeout: Resp({"not": "a list"})):
        q = queue.Queue()
        assert PotaClient(q, get=get).poll_once() is False
        got = items(q)
        assert len(got) == 1 and isinstance(got[0], Status) and got[0].state == "error"


def test_polls_on_schedule_and_retries_after_failure():
    q = queue.Queue()
    calls = []

    def get(url, timeout):
        calls.append(time.monotonic())
        if len(calls) == 2:
            raise requests.ConnectionError("down")
        return Resp(RAW)

    c = PotaClient(q, interval=0.2, get=get)
    c.start()
    time.sleep(0.95)
    c.stop()
    assert len(calls) >= 4
    gaps = [b - a for a, b in zip(calls, calls[1:])]
    assert all(abs(g - 0.2) < 0.05 for g in gaps), gaps       # on schedule, no drift
    states = [i.state for i in items(q) if isinstance(i, Status)]
    assert states[:3] == ["ok", "error", "ok"]                 # failure, then the next poll retries


def test_default_interval_is_60s():
    assert PotaClient(queue.Queue()).interval == 60.0
