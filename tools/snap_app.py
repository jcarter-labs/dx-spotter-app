"""Run the app against canned data, capture the window to a PNG (G1/G2). Not part of the app.

    python tools/snap_app.py out.png [width height]
Feeds the saved cluster and POTA captures through the queue (no network).
"""
import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from capture_window import run_and_capture  # noqa: E402
import json  # noqa: E402

from spotter.app import App  # noqa: E402
from spotter.models import RawLine, RawRecords, Status  # noqa: E402
from spotter.settings import Settings  # noqa: E402
from spotter.ui import SpotterUI  # noqa: E402
import queue, time  # noqa: E402


def make(root, now=None):
    q = queue.Queue()
    app = App(q, Settings())
    caps = ROOT / "tests" / "captures"
    for l in (caps / "cluster_session.txt").read_text(errors="replace").splitlines():
        if l.startswith("DX de "):
            q.put(RawLine(l))
    q.put(RawRecords(json.loads((caps / "pota_spots_raw.json").read_text()), time.time() - 57))
    q.put(Status("cluster", "connected", 0))
    return SpotterUI(root, app), app


if __name__ == "__main__":
    out = sys.argv[1]
    w, h = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (492, 1150)
    root = tk.Tk()
    ui, app = make(root)
    root.geometry(f"{w}x{h}+60+60")
    run_and_capture(root, out, delay_ms=2500)
    print("saved", out, "| spots drawn:", len(ui.hits))
