"""Stage 4 guards G4-G7 (need a display; skipped without one)."""
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

import pytest

from spotter.app import App
from spotter.models import RawLine
from spotter.settings import Settings
from spotter.ui import SpotterUI
from tests.fake_cluster import FakeCluster

ROOT = Path(__file__).resolve().parent.parent
CAP = ROOT / "tests" / "captures" / "cluster_session.txt"


def new_root():
    try:
        return tk.Tk()
    except tk.TclError:
        pytest.skip("no display")


def line(call, khz, skim="WA7LNW-#"):
    return RawLine(f"DX de {skim}:  {khz:.1f}  {call}  CW 13 dB 28 WPM CQ  0007Z")


def pbpaste():
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


@pytest.fixture
def keep_clipboard():
    old = pbpaste()
    yield
    subprocess.run(["pbcopy"], input=old.encode())


def run_loop(root, steps, total_ms):
    """steps: [(ms, fn)] run inside mainloop; the loop ends after total_ms."""
    for ms, fn in steps:
        root.after(ms, fn)
    root.after(total_ms, root.quit)
    root.mainloop()


def click_label(ui, call):
    x0, y0, x1, y1, _ = next(h for h in ui.hits if h[4] == call)
    ui.canvas.event_generate("<Button-1>", x=int((x0 + x1) / 2), y=int((y0 + y1) / 2))


def crowded_ui(root):
    q = queue.Queue()
    app = App(q, Settings())
    ui = SpotterUI(root, app, tick_ms=100)
    root.geometry("492x1150+80+80")
    # 8 calls within 1 kHz: far more crowded than the 16 px label gap
    for i in range(8):
        q.put(line(f"K{i}ABC/P" if i == 3 else f"K{i}ABC", 14040.0 + i * 0.1))
    return q, app, ui


# --- G7 and G6: clicks hit the drawn label, the clipboard holds exactly the call
def test_g7_click_hits_drawn_label_not_true_frequency(keep_clipboard):
    root = new_root()
    q, app, ui = crowded_ui(root)
    out = {}

    def act():
        out["hits"] = list(ui.hits)
        subprocess.run(["pbcopy"], input=b"untouched")
        # a label that was spread away from its true frequency: click its drawn position
        click_label(ui, "K3ABC/P")
        out["after_label"] = pbpaste()
        # click the true-frequency end of its leader (left of the label): no label there -> no copy
        x0, y0, x1, y1, _ = next(h for h in ui.hits if h[4] == "K7ABC")
        subprocess.run(["pbcopy"], input=b"untouched")
        ui.canvas.event_generate("<Button-1>", x=int(x0) - 6, y=int((y0 + y1) / 2) + 30)
        out["after_miss"] = pbpaste()

    run_loop(root, [(600, act)], 900)
    root.destroy()
    assert len(out["hits"]) == 8
    ys = sorted((h[1] + h[3]) / 2 for h in out["hits"])
    assert all(b - a >= 14 for a, b in zip(ys, ys[1:])), "labels were spread apart"
    assert out["after_label"] == "K3ABC/P"          # exactly the call as spotted, suffix kept
    assert out["after_miss"] == "untouched"


def test_g6_clipboard_survives_app_exit(keep_clipboard, tmp_path):
    script = tmp_path / "copy_and_quit.py"
    script.write_text(f"""
import sys, queue, tkinter as tk
sys.path.insert(0, {str(ROOT)!r})
from tests.test_ui_guards import crowded_ui, click_label, run_loop
root = tk.Tk()
q, app, ui = crowded_ui(root)
run_loop(root, [(600, lambda: click_label(ui, "K5ABC"))], 900)
root.destroy()
""")
    subprocess.run(["pbcopy"], input=b"before")
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert pbpaste() == "K5ABC"                      # after the app process has quit


# --- G5: no worker thread touches Tk; close is quick and closes the socket
class TkThreadGuard:
    """Wraps root.tk: records any call made off the main thread."""

    def __init__(self, real):
        object.__setattr__(self, "_real", real)
        object.__setattr__(self, "violations", [])
        object.__setattr__(self, "_main", threading.main_thread())

    def __getattr__(self, name):
        attr = getattr(self._real, name)
        if not callable(attr):
            return attr

        def wrapped(*a, **k):
            if threading.current_thread() is not self._main:
                self.violations.append((threading.current_thread().name, name, a[:1]))
            return attr(*a, **k)
        return wrapped


def test_g5_workers_never_call_tk_and_close_is_quick():
    from spotter.main import build
    root = new_root()
    guard = TkThreadGuard(root.tk)
    root.tk = guard
    fake = FakeCluster()
    from tests.test_pota_client import RAW, Resp
    ui, app, cluster, pota = build(
        root, cluster_kw=dict(host="127.0.0.1", port=fake.port, backoff=(0.1, 0.1), login_timeout=2.0),
        pota_kw=dict(interval=0.3, get=lambda url, timeout: Resp(RAW)), tick_ms=100)
    t = {}

    def close():
        t["start"] = time.monotonic()
        ui.close()
        t["end"] = time.monotonic()

    root.after(1500, close)
    root.mainloop()
    try:
        assert fake.logins >= 1 and app.store.count("pota") > 0       # workers really ran
        assert guard.violations == [], guard.violations
        assert t["end"] - t["start"] < 2.0
        assert not cluster._thread.is_alive() and not pota._thread.is_alive()
        deadline = time.time() + 2
        while fake.disconnects < 1 and time.time() < deadline:
            time.sleep(0.05)
        assert fake.disconnects >= 1                                  # socket closed from our side
    finally:
        fake.close()


def test_g5_worker_modules_do_not_import_tk():
    for name in ("cluster_client", "pota_client", "app", "layout", "settings", "spot_store", "spot_filter"):
        src = (ROOT / "spotter" / f"{name}.py").read_text()
        assert "tkinter" not in src, name


# --- G4: replay at 50 spots/s; the after() tick stays under 300 ms late
def test_g4_tick_stays_responsive_under_50_spots_per_second():
    root = new_root()
    q = queue.Queue()
    app = App(q, Settings())
    ui = SpotterUI(root, app, tick_ms=100)
    root.geometry("492x1150+80+80")
    lines = [l for l in CAP.read_text(errors="replace").splitlines() if l.startswith("DX de ")]
    stop = threading.Event()
    sent = []

    def feeder():
        i = 0
        t0 = time.monotonic()
        while not stop.is_set():
            # one spot per 20 ms = 50/s; capture lines mixed with unique calls inside the span so
            # the canvas really holds hundreds of labels
            q.put(RawLine(lines[i % len(lines)]) if i % 5 == 0 else line(f"T{i % 400}XY", 14020.0 + (i * 7) % 50))
            i += 1
            sent.append(i)
            time.sleep(max(0, t0 + i / 50.0 - time.monotonic()))

    th = threading.Thread(target=feeder, daemon=True)
    th.start()
    # also churn the window size while data flows (a drag is a stream of Configure events)
    sizes = [(492 + (k % 5) * 20, 1000 + (k % 4) * 40) for k in range(40)]
    steps = [(500 + k * 100, (lambda s=s: root.geometry(f"{s[0]}x{s[1]}"))) for k, s in enumerate(sizes)]
    run_loop(root, steps, 5200)
    stop.set(); th.join(2)
    late = ui.max_late_ms
    n = len(ui.hits)
    root.destroy()
    assert len(sent) >= 200                      # about 50 per second for 5 s
    assert n > 50                                # a crowded canvas was being redrawn
    print(f"G4: {len(sent)} spots sent, {n} labels, max tick lateness {late:.0f} ms")
    assert late < 300, f"tick was {late:.0f} ms late"


def test_g5_guard_catches_a_thread_that_calls_tk():
    root = new_root()
    guard = TkThreadGuard(root.tk)

    def bad():
        try:
            guard.call("winfo", "exists", ".")
        except Exception:
            pass

    th = threading.Thread(target=bad, name="rogue")
    th.start(); th.join()
    root.destroy()
    assert guard.violations and guard.violations[0][0] == "rogue"
