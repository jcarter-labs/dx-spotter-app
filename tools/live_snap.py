"""5.1: run the real app on live data, capture the window after N seconds. Not part of the app.
    PYTHONPATH=. python tools/live_snap.py out.png [seconds] [width height]"""
import sys, tkinter as tk
sys.path.insert(0, "tools")
from capture_window import run_and_capture
from spotter.main import build

out = sys.argv[1]
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 20
w, h = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (492, 1150)
root = tk.Tk()
ui, app, cluster, pota = build(root)
root.geometry(f"{w}x{h}+60+60")


def report(_):
    v = app.view()
    print(v.cluster_text, "|", v.pota_text, "|", v.shown_text)


run_and_capture(root, out, delay_ms=int(secs * 1000), before=report)
cluster.stop()
pota.stop()
