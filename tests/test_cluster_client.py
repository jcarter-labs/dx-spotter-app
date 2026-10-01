import queue
import time

import pytest

from spotter.cluster_client import ClusterClient
from spotter.models import RawLine, Status
from tests.fake_cluster import FakeCluster, SPOT

FAST = (0.1, 0.2, 0.3, 0.4)


def wait(pred, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.02)
    return False


def drain(q):
    out = []
    while True:
        try:
            out.append(q.get_nowait())
        except queue.Empty:
            return out


@pytest.fixture
def fake():
    f = FakeCluster()
    yield f
    f.close()


def make(fake, **kw):
    q = queue.Queue()
    c = ClusterClient(q, host="127.0.0.1", port=fake.port, backoff=FAST, login_timeout=2.0, **kw)
    return c, q


def test_login_filter_ack_and_raw_lines(fake):
    c, q = make(fake, band=20)
    c.start()
    try:
        assert wait(lambda: c.filter_acked_band == 20)
        items = drain(q)
        assert Status("cluster", "connecting", 0) in items
        assert Status("cluster", "connected", 0) in items
        assert RawLine(SPOT.strip("\r\n")) in items
        assert fake.commands[0] == "set dx filter Band=20"
    finally:
        c.stop()


def test_band_change_sends_new_filter(fake):
    c, q = make(fake, band=20)
    c.start()
    try:
        assert wait(lambda: c.filter_acked_band == 20)
        c.set_band(40)
        assert wait(lambda: c.filter_acked_band == 40)
        assert "set dx filter Band=40" in fake.commands
    finally:
        c.stop()


def test_drop_goes_red_then_amber_then_green_and_resends_filter(fake):
    c, q = make(fake, band=20)
    c.start()
    try:
        assert wait(lambda: fake.logins == 1 and c.filter_acked_band == 20)
        drain(q)
        fake.drop_all()
        assert wait(lambda: fake.logins == 2 and c.filter_acked_band == 20)
        states = [(i.state, i.retry) for i in drain(q) if isinstance(i, Status)]
        assert states[0] == ("disconnected", 0)
        assert ("connecting", 1) in states
        assert states[-1] == ("connected", 0)           # retry reset on success
        assert fake.commands.count("set dx filter Band=20") == 2  # filter re-sent on reconnect
    finally:
        c.stop()


def test_backoff_and_retry_count_when_server_down():
    f = FakeCluster()
    port = f.port
    f.close()  # nothing listening
    q = queue.Queue()
    c = ClusterClient(q, host="127.0.0.1", port=port, backoff=(0.05, 0.1, 0.15, 0.2), login_timeout=1.0)
    c.start()
    try:
        assert wait(lambda: c.retry >= 5, 5)
        st = [i for i in drain(q) if isinstance(i, Status)]
        assert [s.retry for s in st if s.state == "connecting"][:6] == [0, 1, 2, 3, 4, 5]
        assert all(s.state in ("connecting", "disconnected") for s in st)
    finally:
        c.stop()


def test_backoff_schedule_defaults():
    from spotter.cluster_client import DEFAULT_BACKOFF
    assert DEFAULT_BACKOFF == (5, 10, 30, 60)


def test_forced_reconnect_is_amber_not_a_retry(fake):
    c, q = make(fake, band=20)
    c.start()
    try:
        assert wait(lambda: fake.logins == 1 and c.filter_acked_band == 20)
        drain(q)
        c.reconnect()
        assert wait(lambda: fake.logins == 2 and c.filter_acked_band == 20)
        st = [i for i in drain(q) if isinstance(i, Status)]
        assert Status("cluster", "connecting", 0, "forced reconnect") in st
        assert not any(s.state == "disconnected" for s in st)
        assert all(s.retry == 0 for s in st)
        assert fake.commands.count("set dx filter Band=20") == 2
    finally:
        c.stop()


def test_login_timeout_when_no_prompt():
    f = FakeCluster(accept_logins=False)
    q = queue.Queue()
    c = ClusterClient(q, host="127.0.0.1", port=f.port, backoff=FAST, login_timeout=0.4)
    c.start()
    try:
        assert wait(lambda: any(isinstance(i, Status) and i.state == "disconnected" for i in list(q.queue)), 3)
    finally:
        c.stop(); f.close()


def test_unacked_filter_reports_unconfirmed():
    f = FakeCluster(ack=False)
    q = queue.Queue()
    c = ClusterClient(q, host="127.0.0.1", port=f.port, backoff=FAST, login_timeout=0.5)
    c.start()
    try:
        assert wait(lambda: any(isinstance(i, Status) and i.detail == "filter unconfirmed" for i in list(q.queue)), 3)
    finally:
        c.stop(); f.close()


def test_non_spot_lines_are_not_queued():
    f = FakeCluster(spots=("Welcome to NC7J\r\n", "DX de W6YX-#:  14033.0  K1ABC  CW 20 dB 25 WPM CQ  0001Z\r\n"))
    q = queue.Queue()
    c = ClusterClient(q, host="127.0.0.1", port=f.port, backoff=FAST, login_timeout=1)
    c.start()
    try:
        assert wait(lambda: any(isinstance(i, RawLine) for i in list(q.queue)))
        time.sleep(0.2)
        assert [i.text.split()[2] for i in drain(q) if isinstance(i, RawLine)] == ["W6YX-#:"]
    finally:
        c.stop(); f.close()
