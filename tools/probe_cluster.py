"""Step 2.1: live NC7J session. Not part of the app.

    python tools/probe_cluster.py "set dx filter Band=20" [more commands...]

Logs in as N6YU, waits for the post-login prompt, sends each command (one second apart),
then records raw lines until 50 spot lines or 5 minutes. Everything received is saved
unmodified (before any filtering) to tests/captures/cluster_session.txt.
"""
import socket, sys, time
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tests" / "captures" / "cluster_session.txt"
cmds = sys.argv[1:]
s = socket.create_connection(("nc7j.com", 7373), timeout=10)
s.settimeout(1)
raw = bytearray()
t0 = time.time()


def pump(secs, until=None):
    end = time.time() + secs
    while time.time() < end:
        try:
            d = s.recv(4096)
        except socket.timeout:
            d = b""
        else:
            if not d:
                return False
        raw.extend(d)
        if until and until in raw[-200:].lower():
            return True
    return until is None


assert pump(10, b"login:"), "no login prompt"
s.sendall(b"N6YU\r\n")
ok = pump(10, b"arc6>")
print("post-login prompt seen:", ok)
for c in cmds:
    mark = f"\n<<SENT {c!r}>>\n".encode()
    raw.extend(mark)
    s.sendall(c.encode() + b"\r\n")
    pump(1.5)
spot_lines = lambda: sum(1 for l in bytes(raw).split(b"\n") if l.startswith(b"DX de "))
while time.time() - t0 < 300 and spot_lines() < 50:
    pump(1)
s.close()
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(bytes(raw))
print(f"saved {len(raw)} bytes, {spot_lines()} spot lines in {time.time()-t0:.0f}s -> {OUT}")
