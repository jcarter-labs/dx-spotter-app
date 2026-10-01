"""Worker thread: telnet-style login to the cluster, band filter, raw lines on the queue.

Never parses spots. Puts RawLine (spot lines only) and Status items on the queue.
Protocol (operator's live session): prompt "login: ", then "<call> de NC7J ... arc6>";
filter command "set dx filter Band=<n>" acked by "DX filter set to: Band = <n>".
Filters persist per callsign on the server but are re-sent on every login.
"""
import logging
import queue
import re
import socket
import threading
import time

from .models import RawLine, Status

log = logging.getLogger("cluster_client")

DEFAULT_BACKOFF = (5, 10, 30, 60)  # then 60 s forever
ACK = re.compile(r"DX filter set to:\s*Band\s*=\s*(\d+)", re.I)


class ClusterClient:
    def __init__(self, out: "queue.Queue", host="nc7j.com", port=7373, call="N6YU", band=20,
                 backoff=DEFAULT_BACKOFF, login_timeout=10.0, extra_commands=()):
        self.out, self.host, self.port, self.call = out, host, port, call
        self.backoff = tuple(backoff)
        self.login_timeout = login_timeout
        self.extra_commands = list(extra_commands)  # e.g. a skimmer-on command, once known
        self._band = band
        self._lock = threading.Lock()
        self._pending_band = None
        self._force = threading.Event()
        self._stop = threading.Event()
        self._sock = None
        self._thread = threading.Thread(target=self._run, name="cluster_client", daemon=True)
        self.retry = 0
        self.filter_acked_band = None

    # --- control (called from the GUI thread; the worker does the work)
    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._force.set()
        self._close()
        if self._thread.is_alive():
            self._thread.join(1.5)

    def set_band(self, band: int):
        with self._lock:
            self._pending_band = band

    def reconnect(self):
        """Clear: drop the link and log in again at once (amber, not counted as a retry)."""
        self._force.set()
        self._close()

    # --- internals
    def _status(self, state, detail=""):
        self.out.put(Status("cluster", state, self.retry, detail))

    def _close(self):
        s = self._sock
        if s:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                s.close()
            except OSError:
                pass

    def _run(self):
        self._status("connecting")
        while not self._stop.is_set():
            forced = False
            try:
                self._session()
            except Exception as e:  # lost link, refused, login timeout...
                if self._stop.is_set():
                    break
                forced = self._force.is_set()
                log.info("cluster session ended: %r", e)
                if not forced:
                    self._status("disconnected", str(e))
            if self._stop.is_set():
                break
            if forced:
                self._force.clear()
                self._status("connecting", "forced reconnect")
                continue
            delay = self.backoff[min(self.retry, len(self.backoff) - 1)]
            if self._force.wait(delay):
                self._force.clear()
            if self._stop.is_set():
                break
            self.retry += 1
            self._status("connecting")

    def _readline(self, buf: bytearray, s, deadline=None):
        """Next complete line from buf/socket; None on socket timeout."""
        while True:
            i = buf.find(b"\n")
            if i >= 0:
                line = bytes(buf[:i]).decode("latin-1").strip("\r")
                del buf[: i + 1]
                return line
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError("timed out")
            try:
                d = s.recv(4096)
            except socket.timeout:
                return None
            if not d:
                raise ConnectionError("connection closed by server")
            buf.extend(d)

    def _wait_for(self, s, buf, token: bytes, timeout):
        """Wait until token appears in the stream (prompts have no newline). Consumes through it."""
        end = time.monotonic() + timeout
        while True:
            i = buf.lower().find(token.lower())
            if i >= 0:
                del buf[: i + len(token)]
                return
            if time.monotonic() > end:
                raise TimeoutError(f"no {token!r} within {timeout}s")
            try:
                d = s.recv(4096)
            except socket.timeout:
                continue
            if not d:
                raise ConnectionError("connection closed by server")
            buf.extend(d)

    def _send_filter(self, s, band):
        s.sendall(f"set dx filter Band={band}\r\n".encode())

    def _session(self):
        s = socket.create_connection((self.host, self.port), timeout=self.login_timeout)
        self._sock = s
        s.settimeout(0.5)
        buf = bytearray()
        try:
            self._wait_for(s, buf, b"login:", self.login_timeout)
            s.sendall(f"{self.call}\r\n".encode())
            self._wait_for(s, buf, b"arc6>", self.login_timeout)
            with self._lock:
                self._pending_band = None
                band = self._band
            for c in self.extra_commands:
                s.sendall(c.encode() + b"\r\n")
            self._send_filter(s, band)
            self.filter_acked_band = None
            ack_deadline = time.monotonic() + self.login_timeout
            self.retry = 0  # login succeeded
            self._status("connected")
            warned = False
            while not self._stop.is_set():
                with self._lock:
                    nb, self._pending_band = self._pending_band, None
                if nb is not None:
                    self._band = band = nb
                    self.filter_acked_band = None
                    self._send_filter(s, band)
                    ack_deadline = time.monotonic() + self.login_timeout
                    warned = False
                line = self._readline(buf, s)
                if line is None:
                    if self.filter_acked_band != band and not warned and time.monotonic() > ack_deadline:
                        warned = True
                        log.warning("band filter %s not acknowledged", band)
                        self._status("connected", "filter unconfirmed")
                    continue
                m = ACK.search(line)
                if m:
                    self.filter_acked_band = int(m.group(1))
                    continue
                if line.startswith("DX de "):
                    self.out.put(RawLine(line))
        finally:
            self._close()
            if self._stop.is_set():
                return
        raise ConnectionError("stopped")
