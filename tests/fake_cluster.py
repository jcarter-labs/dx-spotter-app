"""Fake NC7J for tests: login prompt, filter ack, a few spot lines."""
import re
import socket
import threading

SPOT = "DX de WA7LNW-#:  14020.0  XR4T  CW 13 dB 28 WPM CQ  0007Z\r\n"


class FakeCluster:
    def __init__(self, ack=True, spots=(SPOT,), accept_logins=True):
        self.ack, self.spots, self.accept_logins = ack, spots, accept_logins
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(5)
        self.port = self.srv.getsockname()[1]
        self.commands = []   # every command received, across logins
        self.logins = 0
        self.conns = []
        self._stop = False
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while not self._stop:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            self.conns.append(c)
            threading.Thread(target=self._serve, args=(c,), daemon=True).start()

    def _serve(self, c):
        try:
            if not self.accept_logins:
                return  # hold the socket open, say nothing
            c.sendall(b"login: ")
            buf = b""
            while b"\n" not in buf:
                buf += c.recv(1024)
            self.logins += 1
            c.sendall(b"\r\nN6YU de NC7J 30-Sep 0007Z arc6>")
            for s in self.spots:
                c.sendall(s.encode())
            buf = buf.split(b"\n", 1)[1]
            while True:
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    cmd = line.decode().strip()
                    self.commands.append(cmd)
                    m = re.match(r"set dx filter Band=(\d+)", cmd, re.I)
                    if m and self.ack:
                        c.sendall(f"\r\nDX filter set to: Band = {m.group(1)}\r\nN6YU de NC7J 30-Sep 0007Z arc6>".encode())
                d = c.recv(1024)
                if not d:
                    return
                buf += d
        except OSError:
            pass

    def drop_all(self):
        for c in self.conns:
            try:
                c.shutdown(socket.SHUT_RDWR)
                c.close()
            except OSError:
                pass
        self.conns.clear()

    def close(self):
        self._stop = True
        self.srv.close()
        self.drop_all()
