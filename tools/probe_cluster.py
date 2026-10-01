"""Step 2.1 probe: connect to NC7J, log in, show raw bytes. Not part of the app."""
import socket, sys, time
cmds = sys.argv[1:]
s = socket.create_connection(("nc7j.com", 7373), timeout=10)
s.settimeout(3)
def rd(t):
    end = time.time() + t; buf = b""
    while time.time() < end:
        try:
            d = s.recv(4096)
            if not d: buf += b"<<EOF>>"; break
            buf += d
        except socket.timeout:
            break
    return buf
print("BANNER:", repr(rd(4)))
s.sendall(b"N6YU\r\n")
print("AFTER LOGIN:", repr(rd(5)))
for c in cmds:
    s.sendall(c.encode() + b"\r\n")
    print(f"CMD {c!r}:", repr(rd(4)))
s.close()
