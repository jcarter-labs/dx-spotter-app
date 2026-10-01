"""Step 2.6 live checks for cluster_client against the real NC7J. Not part of the app."""
import queue, time
from spotter.cluster_client import ClusterClient
from spotter.cluster_parse import parse_line
from spotter.models import RawLine, Spot, Status

res = []
def check(name, ok, info=""):
    res.append(ok); print(("PASS " if ok else "FAIL ") + name, info, flush=True)

def wait(pred, t):
    end = time.time() + t
    while time.time() < end:
        if pred(): return True
        time.sleep(0.05)
    return False

def pull(q):
    out = []
    while not q.empty(): out.append(q.get_nowait())
    return out

q = queue.Queue()
c = ClusterClient(q, band=20)
t0 = time.time()
c.start()
ok = wait(lambda: c.filter_acked_band == 20, 12)
items = pull(q)
check("connect: login + filter ack within 10 s, green", ok and Status("cluster", "connected", 0) in items, f"({time.time()-t0:.1f}s)")
wait(lambda: any(isinstance(i, RawLine) for i in list(q.queue)), 60)
sp = [parse_line(i.text) for i in pull(q) if isinstance(i, RawLine)]
sp = [s for s in sp if isinstance(s, Spot)]
check("20 m spots arrive", sp and all(14.0 <= s.freq_mhz <= 14.35 for s in sp), f"({len(sp)} spots)")

# band change 20 -> 40
c.set_band(40)
check("band change: ack for 40", wait(lambda: c.filter_acked_band == 40, 10))
time.sleep(1); pull(q)  # anything queued before the filter took effect
wait(lambda: any(isinstance(i, RawLine) for i in list(q.queue)), 120)
sp = [parse_line(i.text) for i in pull(q) if isinstance(i, RawLine)]
sp = [s for s in sp if isinstance(s, Spot)]
check("band change: only 40 m spots after ack", len(sp) > 0 and all(7.0 <= s.freq_mhz <= 7.3 for s in sp), f"({len(sp)} spots)")

# forced reconnect (Clear): amber, not a retry, filter re-sent and acked (still band 40)
pull(q); c.filter_acked_band = None
c.reconnect()
ok = wait(lambda: c.filter_acked_band == 40, 15)
st = [i for i in pull(q) if isinstance(i, Status)]
check("Clear/reconnect: amber, no retry counted, filter re-acked",
      ok and any(s.state == "connecting" for s in st) and not any(s.state == "disconnected" for s in st) and all(s.retry == 0 for s in st))

# kill the socket: red, then amber with retry, then green, retry reset
pull(q); c.filter_acked_band = None
c._sock.shutdown(2)
ok = wait(lambda: c.filter_acked_band == 40, 30)
st = [(s.state, s.retry) for s in pull(q) if isinstance(s, Status)]
check("killed socket: red -> amber(retry 1) -> green(retry 0), filter re-sent", ok and st[0][0] == "disconnected" and ("connecting", 1) in st and st[-1] == ("connected", 0), str(st))
c.stop()

# blocked network: nothing reachable; backoff 5,10,30 observed
q2 = queue.Queue()
c2 = ClusterClient(q2, host="127.0.0.1", port=1, band=20)
t=time.time(); c2.start()
wait(lambda: c2.retry >= 3, 60)
times = []
c2.stop()
st = [s for s in pull(q2) if isinstance(s, Status)]
check("blocked: red/amber with retry counts 1,2,3", [s.retry for s in st if s.state == "connecting"][:4] == [0, 1, 2, 3] and any(s.state == "disconnected" for s in st), f"({time.time()-t:.0f}s)")
print("ALL PASS" if all(res) else "SOME FAILED")
