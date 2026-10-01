"""Step 2.7: bare window, two plain lists (call, freq, age) fed through the queue.

No bandmap, layout, styling or client-side filtering; last 50 entries each. Uses a small
temporary drain that `app` replaces in 3.5. Run: python -m spotter.bare_window
"""
import queue
import time
import tkinter as tk
from collections import deque

from .cluster_client import ClusterClient
from .cluster_parse import parse_line
from .models import RawLine, RawRecords, Reject, Spot, Status
from .pota_client import PotaClient
from .pota_parse import parse_record


class Bare:
    def __init__(self, root, band=20, cluster_kw=None, pota_kw=None):
        self.q = queue.Queue()
        self.rbn, self.pota = deque(maxlen=50), deque(maxlen=50)  # (recv_time, Spot)
        self.cluster_state, self.pota_last = "connecting", None
        self.rejected = 0
        self.root = root
        root.title("DX Spotter (bare)")
        self.status = tk.Label(root, anchor="w")
        self.status.pack(fill="x")
        f = tk.Frame(root)
        f.pack(fill="both", expand=True)
        self.lists = []
        for name in ("RBN", "POTA"):
            col = tk.Frame(f)
            col.pack(side="left", fill="both", expand=True)
            tk.Label(col, text=name).pack()
            lb = tk.Listbox(col, width=34, height=30, font=("Menlo", 11))
            lb.pack(fill="both", expand=True)
            self.lists.append(lb)
        self.cluster = ClusterClient(self.q, band=band, **(cluster_kw or {}))
        self.potac = PotaClient(self.q, **(pota_kw or {}))
        self.cluster.start()
        self.potac.start()
        self.tick()

    def drain(self):
        while True:
            try:
                item = self.q.get_nowait()
            except queue.Empty:
                return
            now = time.time()
            if isinstance(item, RawLine):
                s = parse_line(item.text)
                (self.rbn.append((now, s)) if isinstance(s, Spot) else self._rej())
            elif isinstance(item, RawRecords):
                self.pota_last = time.time()
                for r in item.records:
                    s = parse_record(r)
                    (self.pota.append((now, s)) if isinstance(s, Spot) else self._rej())
            elif isinstance(item, Status) and item.source == "cluster":
                self.cluster_state = f"{item.state} (retry {item.retry}) {item.detail}".strip()

    def _rej(self):
        self.rejected += 1

    def tick(self):
        self.drain()
        now = time.time()
        ago = "not polled yet" if self.pota_last is None else f"last poll {int(now - self.pota_last)}s ago"
        self.status.config(text=f"Cluster: {self.cluster_state} | POTA: {ago} | rejected {self.rejected}")
        for lb, data in zip(self.lists, (self.rbn, self.pota)):
            lb.delete(0, "end")
            for t, s in reversed(data):
                lb.insert("end", f"{s.call:<10} {s.freq_mhz * 1000:9.1f} {int(now - t):4d}s")
        self.root.after(1000, self.tick)

    def close(self):
        self.cluster.stop()
        self.potac.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = Bare(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
